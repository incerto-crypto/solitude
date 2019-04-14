# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Dict, Tuple, Optional, Iterator, Sequence
from collections import namedtuple
import hashlib
import binascii
import bisect

from solitude.client import RPCClient
from solitude.common import ContractObjectList, hex_repr


TraceStackItem = namedtuple("TraceStackItem", ["unitname", "contractname", "decoder"])

SourceMapping = namedtuple("SourceMapping", [
    "unitname", "source", "lines", "line_index", "line_start", "line_pos"])

TraceStep = namedtuple("TraceStep", [
    "index", "depth", "contractname",
    "pc", "op", "stack", "memory", "storage", "gas", "error",
    "start", "length", "fileno", "jumptype",
    "code"])

CallStackElement = namedtuple("CallStackElement", ["prev", "step"])
CallStackEvent = namedtuple("CallStackEvent", ["event", "data"])


class EvmTrace:
    def __init__(self, rpc: RPCClient, compiled: ContractObjectList):
        self._rpc = rpc
        self._compiled = compiled
        self._address_to_contract = AddressToContract()
        self._address_to_contract.initialize(rpc, self._compiled)
        self.srcmapper = SourceMapper(self._compiled)

    def trace_iter(self, txhash: bytes) -> Iterator[Tuple[TraceStep, List[TraceStep]]]:
        txhash_hex = hex_repr(txhash)
        transaction = self._rpc.eth_getTransactionByHash(txhash_hex)
        debug_trace = self._rpc.debug_traceTransaction(txhash_hex, {})
        logs = debug_trace["structLogs"]
        callstack = CallStack()

        tracestack = []  # type: List[TraceStackItem]
        prev_depth = -1
        for i, log in enumerate(logs):
            depth, pc, op, error, gas, memory, stack, storage = (
                log["depth"], log["pc"], log["op"], log["error"], log["gas"], log["memory"], 
                log["stack"], log["storage"])

            # when entering call, create a new decoder for the relevant contract
            if depth == prev_depth + 1:  # enter CALL
                if i == 0:
                    address = transaction["to"]
                else:
                    # contract address is in element -2 of stack
                    address = "0x" + logs[i - 1]["stack"][-2][24:]
                try:
                    call_unitname, call_contractname = self._address_to_contract.get_contract_id(address)
                    contract = self._compiled.contracts[(call_unitname, call_contractname)]
                    tracestack.append(TraceStackItem(
                        unitname=call_unitname,
                        contractname=call_contractname,
                        decoder=FrameDecoder(contract=contract)))
                except KeyError:
                    tracestack.append(TraceStackItem(
                        unitname=call_unitname,
                        contractname=call_contractname,
                        decoder=FrameDecoderDummy()))
            elif depth == prev_depth - 1:
                del tracestack[-1]
            prev_depth = depth

            # use the relevant decoder to map source
            frame = tracestack[-1]
            mapping = frame.decoder.get_mapping(address=pc)
            st, le, fi, ju = mapping
            source = self.srcmapper.get_source(frame.unitname, st, le, fi)

            step = TraceStep(
                index=i, depth=depth, contractname=frame.contractname,
                pc=pc, op=op, stack=stack, memory=memory, storage=storage, gas=gas, error=error,
                start=st, length=le, fileno=fi, jumptype=ju,
                code=source)
            callstack_event = callstack.add(step)
            yield step, callstack_event


class CallStack:
    def __init__(self):
        self._stack = [[]]
        self._prev_step = None

    def add(self, step: TraceStep) -> CallStackEvent:
        event = None
        event_data = None
        prev_op = self._prev_step.op.lower() if (self._prev_step is not None) else None
        op = step.op.lower()
        # print("op %s prev %s" % (op, prev_op))
        if op == 'jumpdest':
            if prev_op == 'jump':
                if (len(self._stack[-1]) > 0) and (step.pc == self._stack[-1][-1].prev.pc + 1):
                    del self._stack[-1][-1]
                    event = "pop"
                elif self._prev_step.jumptype == 'i':
                    event_data = CallStackElement(self._prev_step, step)
                    event = "push"
                    self._stack[-1].append(event_data)
        elif step.pc == 0 and prev_op == 'call':
            event_data = CallStackElement(self._prev_step, step)
            event = "push"
            self._stack.append([event_data])
        elif prev_op == 'stop':
            event = "pop"
            del self._stack[-1]
        self._prev_step = step
        return CallStackEvent(event=event, data=event_data)

    @property
    def stack(self):
        return [x for y in self._stack for x in y]


class IFrameDecoder:
    def __init__(self, contract: Optional[dict]=None):
        self._contract = contract

    def get_mapping(self, address: int):
        raise NotImplementedError()


class FrameDecoderDummy(IFrameDecoder):
    def __init__(self, contract: Optional[dict]=None):
        super().__init__(contract)

    def get_mapping(self, address: int) -> Tuple[int, int, int, str]:
        return (0, 0, 0, '-')


class FrameDecoder(IFrameDecoder):
    def __init__(self, contract: dict):
        super().__init__(contract)
        assert(self._contract is not None)

        self._bytecode = binascii.unhexlify(self._contract["bin-runtime"])

        # instruction address (bytes offset) to instruction number
        #   which can be related to program counter
        self._address_to_instruction_number = (
            FrameDecoder._map_address_to_instruction_number(self._bytecode))

        # instruction address to start, length, fileid, jumptype
        #   to find source code parts relevant to instruction address
        # The source map in the compiler output is compressed, we need to
        #   expand it
        self._instruction_number_to_source = (
            FrameDecoder._decode_source_map(self._contract["srcmap-runtime"]))

    def get_mapping(self, address: int) -> Tuple[int, int, int, str]:
        instruction_number = self._address_to_instruction_number[address]
        mapping = self._instruction_number_to_source[instruction_number]
        return mapping

    @staticmethod
    def _decode_source_map(srcmap: str) -> List[Tuple[int, int, int, str]]:
        out = []
        # the source map is a list of tuples (st, le, fi, ju)
        #   st: start character in source code
        #   le: lenght of code portion
        #   fi: file number for this mapping
        #   ju: jump type

        # In the string, mappings are separated by ";" and elements of a mapping
        #   are separated by ":"

        # from https://github.com/ethereum/solidity/blob/develop/docs/miscellaneous.rst#source-mappings
        # In order to compress these source mappings especially for bytecode, the following rules are used:
        #   - If a field is empty, the value of the preceding element is used.
        #   - If a : is missing, all following fields are considered empty.

        last = (0, 0, 0, '-')
        for m in srcmap.split(";"):
            mv = m.split(':')
            st = int(mv[0]) if (len(mv) > 0 and len(mv[0])) else last[0]
            le = int(mv[1]) if (len(mv) > 1 and len(mv[1])) else last[1]
            fi = int(mv[2]) if (len(mv) > 2 and len(mv[2])) else last[2]
            ju = mv[3] if (len(mv) > 3 and len(mv[3])) else last[3]
            last = (st, le, fi, ju)
            out.append(last)
        return out

    @staticmethod
    def _map_address_to_instruction_number(bytecode) -> List[int]:
        out = []
        # all instructions have length 1, except PUSH1[0x60]..PUSH32[0x7f]
        # which have length 2..33
        instr_address = 0
        k = 0
        while instr_address < len(bytecode):
            instr = bytecode[instr_address]
            instr_length = 1
            if instr >= 0x60 and instr <= 0x7f:
                instr_length += instr - 0x5f
            out.extend([k] * instr_length)
            k += 1
            instr_address += instr_length
        return out


class SourcePosToLine:
    def __init__(self, source: Optional[str]):
        self._splits = []  # type: List[int]
        if source is None:
            self._source = ""
            self._lines = [""]
        else:
            self._source = source
            self._lines = source.split('\n')
            for i, c in enumerate(source):
                if c == '\n':
                    self._splits.append(i)

    def line_of(self, index: int):
        line_index = bisect.bisect_right(self._splits, index)
        try:
            line_start = self._splits[line_index - 1] + 1
        except IndexError:
            line_start = 0
        return line_index, line_start

    @property
    def source(self):
        return self._source

    @property
    def lines(self):
        return self._lines


class SourceMapper:
    def __init__(self, compiled: ContractObjectList):
        self._compiled = compiled
        # collect sources
        self._unitname_to_posmapper = {}  # type: Dict[str, SourcePosToLine]
        self._unitname_fi_to_unitname = {}  # type: Dict[Tuple[str, int], str]
        # self._contractname_fi_to_unitname = {}  # type: Dict[Tuple[str, int], str]
        for (unitname, contractname), contract in self._compiled.contracts.items():
            self._unitname_to_posmapper[unitname] = (
                SourcePosToLine(contract["_solitude"]["source"]))
            for fi, fi_unitname in enumerate(contract["_solitude"]["sourceList"]):
                self._unitname_fi_to_unitname[(unitname, fi)] = fi_unitname
        self._nullposmapper = SourcePosToLine(None)

    def get_unitname(self, unitname: str, fi: int) -> str:
        return self._unitname_fi_to_unitname[(unitname, fi)]

    def get_source(self, unitname: str, st: int, le: int, fi: int) -> SourceMapping:
        unitname_fi = None  # type: Optional[str]
        try:
            unitname_fi = self.get_unitname(unitname, fi)
            posmapper = self._unitname_to_posmapper[unitname_fi]
        except KeyError:
            unitname_fi = None
            posmapper = self._nullposmapper
        line_index, line_start = posmapper.line_of(st)
        line_pos = st - line_start
        if line_pos < 0:
            line_pos = len(posmapper.lines[line_index])
        return SourceMapping(
            unitname=unitname_fi,
            source=posmapper.source,
            lines=posmapper.lines,
            line_index=line_index,
            line_start=line_start,
            line_pos=line_pos)


class AddressToContract:
    def __init__(self):
        self._address_to_contract_id = {}  # type: Dict[str, Tuple[str, str]]

    def initialize(self, client: RPCClient, compiled: ContractObjectList):
        earliest_block = client.eth_getBlockByNumber("earliest", False)
        start_block = int(earliest_block["number"][2:], 16)
        latest_block = client.eth_getBlockByNumber("latest", False)
        end_block = int(latest_block["number"][2:], 16)

        contracts_bin = [
            (
                unitname,
                contractname,
                binascii.unhexlify(contract["bin"])
            ) for (
                (unitname, contractname), contract) in compiled.contracts.items()
        ]

        for block_number in range(start_block, end_block + 1):
            block = client.eth_getBlockByNumber(hex(block_number), True)
            for transaction in block["transactions"]:
                if len(transaction["input"]) > 4:
                    receipt = client.eth_getTransactionReceipt(transaction["hash"])
                    contract_address = receipt["contractAddress"]
                    if contract_address is not None:
                        contract_bytecode = binascii.unhexlify(transaction["input"][2:])

                        contract_id = self._search_contract(contracts_bin, contract_bytecode)
                        # print("ContractAddress: %s" % contract_address)
                        # print("ContractID: %s" % repr(contract_id))
                        self._address_to_contract_id[contract_address] = contract_id

    def _search_contract(self, contract_bin: Tuple[str, str, bytes], contract_bytecode: bytes) -> Tuple[str, str]:
        match_length = 0
        match_id = None
        for unitname, contractname, bytecode in contract_bin:
            if len(bytecode) > match_length and contract_bytecode.startswith(bytecode):
                match_length = len(bytecode)
                match_id = (unitname, contractname)
        return match_id

    def get_contract_id(self, address: str) -> Tuple[str, str]:
        return self._address_to_contract_id[address]
