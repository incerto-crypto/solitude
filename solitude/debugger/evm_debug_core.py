# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Optional, Dict, List

from web3 import Web3

from solitude._internal.oi_serializable import ISerializable
from solitude._internal import EnumType
from solitude.client.eth_client import ETHClient
from solitude.debugger.evm_trace import EvmTrace, TraceStep, CallStackEvent  # noqa


class ValueKind(EnumType):
    VARIABLE = "variable"
    TEMPORARY = "temporary"
    RETURN = "return"


class Value(ISerializable):
    """Value debug information

    It represents a value associated to a named entity in the source code.
    Only supports numeric values.
    """
    def __init__(self, vtype: str, name: str, value, kind: str, origin=None):
        """Create a Value object

        :param vtype: value type name
        :param name: value name
        :param value: integer content of value
        :param kind: one of ValueKind enum values
        :param origin: type of AST node from which the variable information was extracted
        """
        self.type, self.name, self.value, self.kind, self.origin = (
            vtype, name, value, kind, origin)

    def __str__(self):
        return "{type} {name} = {value}".format(
            type=self.type,
            name=self.name if self.name else "?",
            value=repr(self.value_repr()))

    def value_repr(self) -> str:
        """Get string representation of the value

        :return: string representation
        """
        if self.type == "address":
            value = "0x{:040x}".format(self.value)
            if len(value) == 42:
                value = Web3.toChecksumAddress(value)
            return value
        else:
            return self.value

    def to_obj(self):
        value = self.value_repr()
        return {
            "type": self.type,
            "name": self.name,
            "value": self.value,
            "kind": self.kind,
            "origin": self.origin,
            "value_string": str(value),
            "value_repr": repr(value),
            "string": str(self)
        }

    @staticmethod
    def from_obj(obj):
        raise NotImplementedError()


class Function(ISerializable):
    """Object containing a function call information
    """
    def __init__(self, name: str, parameters: List[Value]):
        """Create a Function object

        :param name: function name
        :param parameters: list of function parameters, as :py:class:`Value` objects
        """
        self.name = name
        self.parameters = parameters

    def __str__(self):
        return "function " + self.name + "(" + ", ".join([str(x) for x in self.parameters]) + ")"

    def to_obj(self):
        return {
            "name": self.name,
            "parameters": [param.to_obj() for param in self.parameters],
            "string": str(self)
        }

    @staticmethod
    def from_obj(obj):
        raise NotImplementedError()


class Frame(ISerializable):
    """Call stack frame information

    :ivar ~.locals: dictionary of local variable values
    :ivar ~.return_values: list of values produced by return statements
    :ivar ~.function: function call information

    Step information is lost during serialization, and the three attributes above are kept
    """
    def __init__(self, prev: TraceStep, cur: TraceStep):
        """Create a Frame object

        :param prev: step before entering the function
        :param cur: step after entering the function
        """
        self.prev = prev
        self.cur = cur
        self.locals = {}  # type: Dict[str, Value]
        self.return_values = []  # type: List[Value]
        self.function = None  # type: Optional[Function]

    def to_obj(self):
        return {
            "locals": {k: v.to_obj() for k, v in self.locals.items()},
            "return_values": [v.to_obj() for v in self.return_values],
            "function": (self.function.to_obj() if self.function is not None else None)
        }

    @staticmethod
    def from_obj(obj):
        raise NotImplementedError()


class Step:
    """
    Single instruction step information

    :ivar ~.ast: AST nodes mapped to the instruction, as dictionary of
        (node type name -> node dict)
    :ivar ~.values: values associated to this instruction (variable assignment,
        value produced by evaluation of statement, ...)
    """
    def __init__(self, step: Optional[TraceStep], event: Optional[CallStackEvent]):
        """Create a Step object

        :param step: step information
        :param event: call stack event associated with the step

        This object may be create empty, with null step and event data.
        """
        self.step = step
        self.event = event
        self.ast = {}  # type: Dict[str, dict]
        self.values = {}  # type: Dict[str, Value]

    @property
    def valid(self):
        """Wether this object contains step information or is empty

        :return: True if not empty, otherwise False
        """
        return self.step is not None


class EvmDebugCore:
    """Provides common debugger-like access to the EVM's debug information
    """
    INVALID_STEP = Step(None, CallStackEvent(None, None))

    def __init__(self, client: ETHClient, txhash: bytes, windowsize=50):
        """Create an EvmDebugCore.

        :param client: an `ETHClient` connected to the ETH node
        :param txhash: transaction hash, as bytes
        :param windowsize: amount of previous and next steps buffered, for a total
            of previous (windowsize) + current (1) + next (windowsize).
        """
        self._client = client
        self._dbg = EvmTrace(client.rpc, client.contracts)
        self._txhash = txhash

        self._astmaps = self._create_ast_maps(client.contracts)

        self._windowsize = windowsize
        self._window_offset = 0
        self._window = [EvmDebugCore.INVALID_STEP] * (1 + 2 * self._windowsize)

        self._frames = []  # type: List[Frame]

        self._iter = self._dbg.trace_iter(txhash)
        self._move_window(self._windowsize + 1)
        first_step = self._get_window_rel(0).step
        self._push_frame(Frame(prev=first_step, cur=first_step))

    def _create_ast_maps(self, compiled):
        out = {}
        for cname, contract in compiled.contracts.items():
            castmap = {}
            source_path = contract["_solitude"]["sourcePath"]
            if source_path in out:
                continue
            cast = contract["_solitude"]["ast"]
            nodes = [cast]
            while nodes:
                node = nodes[0]
                del nodes[0]
                if isinstance(node, dict):
                    if "src" in node:
                        src = node["src"]
                        try:
                            castmap[src].append(node)
                        except KeyError:
                            castmap[src] = [node]
                    for key, value in node.items():
                        if isinstance(value, dict):
                            nodes.extend(list(value.values()))
                        elif isinstance(value, list):
                            nodes.extend(value)
                elif isinstance(node, list):
                    nodes.extend(node)
            out[source_path] = castmap
        return out

    def _get_window_rel(self, i):
        if self._windowsize + i < len(self._window):
            return self._window[self._windowsize + i]
        return EvmDebugCore.INVALID_STEP

    def _get_window_abs(self, i):
        return self._get_window_rel(i - self._window_offset)

    def _push_frame(self, f):
        self._frames.append(f)

    def _pop_frame(self):
        del self._frames[-1]

    def _get_frame(self, i):
        return self._frames[-1 - i]

    def _move_window(self, n):
        for _ in range(n):
            del self._window[0]
            try:
                step, event = next(self._iter)
                s = Step(step, event)
                s.ast = self._get_ast_nodes(s.step)
                self._window.append(s)
            except StopIteration:
                self._window.append(EvmDebugCore.INVALID_STEP)
            self._window_offset += 1

    def _extract_variable(self, step: TraceStep, astnode: dict, stackpos: int, origin=None) -> List[Value]:
        vartype = astnode.get("typeDescriptions", {}).get("typeString", "T?")
        varname = astnode.get("name", None)
        varkind = ValueKind.VARIABLE
        if varname is None:
            st, le, fi = [int(x) for x in astnode["src"].split(":")]
            source = self._dbg.srcmapper.get_source(step.contractname, st, le, fi)
            varname = source.source[st:st + le]
            varkind = ValueKind.TEMPORARY
        try:
            varvalue = int(step.stack[-1 - stackpos], 16)
        except IndexError:
            return []
        return [Value(vtype=vartype, name=varname, value=varvalue, kind=varkind, origin=origin)]

    def _get_ast_nodes(self, step: TraceStep):
        ast_src = "%d:%d:%d" % (step.start, step.length, step.fileno)
        out = {}
        try:
            for node in self._astmaps[step.code.unitname][ast_src]:
                out[node["nodeType"]] = node
        except KeyError:
            pass
        return out

    def _search_ExpressionStatement(self, s: Step, stmt: dict) -> List[Value]:
        values = []
        try:
            if stmt["expression"]["nodeType"] == "Assignment":
                node = stmt["expression"]["leftHandSide"]
                values.extend(
                    self._extract_variable(s.step, node, 0, origin="ExpressionStatement"))
        except KeyError:
            pass
        return values

    def _search_VariableDeclarationStatement(self, s: Step, stmt: dict) -> List[Value]:
        values = []
        try:
            if stmt["declarations"][0]["nodeType"] == "VariableDeclaration":
                node = stmt["declarations"][0]
                values.extend(
                    self._extract_variable(s.step, node, 0, origin="VariableDeclarationStatement"))
        except KeyError:
            pass
        return values

    def _search_FunctionDefinition(self, s: Step, stmt: dict) -> Optional[Function]:
        values = []
        try:
            name = stmt["name"]
            params = stmt["parameters"]["parameters"]
            num_params = len(params)
            if len(s.step.stack) < num_params + 1:
                return None
            for param_index, param_node in enumerate(params):
                values.extend(
                    self._extract_variable(
                        s.step, param_node, num_params - param_index - 1,
                        origin="FunctionDefinition"))
        except KeyError:
            return None
        return Function(name=name, parameters=values)

    def _search_FunctionReturn(self, s: Step, stmt: dict) -> Optional[Function]:
        values = []
        try:
            name = stmt["name"]
            params = stmt["returnParameters"]["parameters"]
            num_params = len(params)
            if len(s.step.stack) < num_params + 2:
                return None
            for param_index, param_node in enumerate(params):
                values.extend(
                    self._extract_variable(
                        s.step, param_node, num_params - param_index,
                        origin="FunctionReturn"))
                for var in values:
                    var.kind = ValueKind.RETURN
        except KeyError:
            return None
        return Function(name=name, parameters=values)

    def step(self):
        """Step one instruction forward
        """
        self._move_window(1)
        s = self._get_window_rel(0)
        if not s.valid:
            return
        if s.event.event == "push":
            self._push_frame(
                Frame(prev=s.event.data.prev, cur=s.event.data.step))
        elif s.event.event == "pop":
            self._pop_frame()

        try:
            f = self._get_frame(0)
        except IndexError:
            # TODO inline assembly delegatecall not detected and no frame being
            #   pushed on the stack. When using proxy contracts, causes the first
            #   frame to be missing, and the last return to be unmatched
            return

        # analyze locals
        ast = s.ast

        # print(list(ast))
        # print(s.step.op)
        # print(s.step.stack)
        # print("pc=%d ast=%s op=%s" % (s.step.pc, repr(list(ast)), repr(s.step.op)))

        values = []
        if not values and "ExpressionStatement" in ast and s.step.op == "SWAP1":
            values.extend(
                self._search_ExpressionStatement(s, ast["ExpressionStatement"]))
        if not values and "VariableDeclarationStatement" in ast and s.step.op in ("SWAP1", "SWAP2", "SWAP3"):
            values.extend(
                self._search_VariableDeclarationStatement(s, ast["VariableDeclarationStatement"]))
        if not values and "FunctionDefinition" in ast and s.step.op == "JUMP":
            function = self._search_FunctionReturn(s, ast["FunctionDefinition"])
            if function is not None and f.function is not None and f.function.name == function.name:
                values.extend(function.parameters)
        if not values and "FunctionDefinition" in ast and s.step.op == "JUMPDEST":
            function = self._search_FunctionDefinition(s, ast["FunctionDefinition"])
            if function is not None and f.function is None:
                values.extend(function.parameters)
                f.function = function
        if not values and s.step.op == "CALLVALUE":
            snext = self._get_window_rel(1)
            if snext.valid:
                varvalue = int(snext.step.stack[-1], 16)
                values.extend([
                    Value(vtype="uint256", name="msg.value", value=varvalue, kind=ValueKind.VARIABLE)])
        for var in values:
            if var.kind == ValueKind.TEMPORARY:
                s.values[var.name] = var
            elif var.kind == ValueKind.VARIABLE:
                f.locals[var.name] = var
            elif var.kind == ValueKind.RETURN:
                f.return_values.append(var)

    def get_frames(self) -> List[Frame]:
        """Get call stack frames
        :return: a list of :py:class:`Frame`
        """
        return self._frames[::-1]

    def get_callstack_depth(self) -> int:
        """Get the call stack depth
        :return: number of frames in the call stack
        """
        return len(self._frames)

    def get_values(self) -> Dict[str, Value]:
        """Get named values in the current step, from function parameters and
        local variables.

        :return: list of :py:class:`Value`
        """
        s = self._get_window_rel(0)
        f = self._get_frame(0)
        out = {}  # type: Dict[str, Value]
        out.update(f.locals)
        out.update(s.values)
        return out

    def get_step(self, offset=0) -> Step:
        """Get step, relative to current step.

        :param offset: step offset, relative to the current one. Can be in range
            (-windowsize, windowsize), according to the windowsize value provided in the
            constructor.
        :return: a :py:class:`Step`
        """
        return self._get_window_rel(offset)
