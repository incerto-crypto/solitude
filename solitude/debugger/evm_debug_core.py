# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Optional, Dict, List

from web3 import Web3

from solitude.client.eth_client import ETHClient
from solitude.debugger.evm_trace import EvmTrace, TraceStep, CallStackEvent  # noqa


class Variable:
    def __init__(self, vtype: str, name: str, value: int, scope: str, origin=None):
        self.type, self.name, self.value, self.scope, self.origin = (
            vtype, name, value, scope, origin)

    def __str__(self):
        return "{type} {name} = {value}".format(
            type=self.type,
            name=self.name if self.name else "?",
            value=repr(self.value_native()))

    def value_native(self):
        if self.type == "address":
            value = "0x{:040x}".format(self.value)
            if len(value) == 42:
                value = Web3.toChecksumAddress(value)
            return value
        else:
            return self.value

    def to_obj(self):
        value = self.value_native()
        return {
            "type": self.type,
            "name": self.name,
            "value": self.value,
            "scope": self.scope,
            "origin": self.origin,
            "value_string": str(value),
            "value_repr": repr(value),
            "string": str(self)
        }


class Function:
    def __init__(self, name: str, parameters: List[Variable]):
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


class Frame:
    def __init__(self, prev: TraceStep, cur: TraceStep):
        self.prev = prev
        self.cur = cur
        self.locals = {}  # type: Dict[str, Variable]
        self.returnValues = []  # type: List[Variable]
        self.function = None  # type: Optional[Function]

    def to_obj(self):
        return {
            "locals": {k: v.to_obj() for k, v in self.locals.items()},
            "return_values": [v.to_obj() for v in self.returnValues],
            "function": (self.function.to_obj() if self.function is not None else None)
        }


class Step:
    def __init__(self, step: TraceStep, event: CallStackEvent):
        self.step = step
        self.event = event
        self.ast = {}  # type: Dict[str, dict]
        self.values = {}  # type: Dict[str, Variable]

    @property
    def valid(self):
        return self.step is not None


class EvmDebugCore:
    INVALID_STEP = Step(None, CallStackEvent(None, None))

    def __init__(self, client: ETHClient, txhash, windowsize=50):
        self._client = client
        self._dbg = EvmTrace(client.rpc, client.compiled)
        self._txhash = txhash

        self._astmaps = self._create_ast_maps(client.compiled)

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

    def _extract_variable(self, step: TraceStep, astnode: dict, stackpos: int, origin=None) -> List[Variable]:
        vartype = astnode.get("typeDescriptions", {}).get("typeString", "T?")
        varname = astnode.get("name", None)
        varscope = "function"
        if varname is None:
            st, le, fi = [int(x) for x in astnode["src"].split(":")]
            source = self._dbg.srcmapper.get_source(step.contractname, st, le, fi)
            varname = source.source[st:st + le]
            varscope = "line"
        try:
            varvalue = int(step.stack[-1 - stackpos], 16)
        except IndexError:
            return []
        return [Variable(vtype=vartype, name=varname, value=varvalue, scope=varscope, origin=origin)]

    def _get_ast_nodes(self, step: TraceStep):
        ast_src = "%d:%d:%d" % (step.start, step.length, step.fileno)
        out = {}
        try:
            for node in self._astmaps[step.code.unitname][ast_src]:
                out[node["nodeType"]] = node
        except KeyError:
            pass
        return out

    def _search_ExpressionStatement(self, s: Step, stmt: dict) -> List[Variable]:
        variables = []
        try:
            if stmt["expression"]["nodeType"] == "Assignment":
                node = stmt["expression"]["leftHandSide"]
                variables.extend(
                    self._extract_variable(s.step, node, 0, origin="ExpressionStatement"))
        except KeyError:
            pass
        return variables

    def _search_VariableDeclarationStatement(self, s: Step, stmt: dict) -> List[Variable]:
        variables = []
        try:
            if stmt["declarations"][0]["nodeType"] == "VariableDeclaration":
                node = stmt["declarations"][0]
                variables.extend(
                    self._extract_variable(s.step, node, 0, origin="VariableDeclarationStatement"))
        except KeyError:
            pass
        return variables

    def _search_FunctionDefinition(self, s: Step, stmt: dict) -> Optional[Function]:
        variables = []
        try:
            name = stmt["name"]
            params = stmt["parameters"]["parameters"]
            num_params = len(params)
            if len(s.step.stack) < num_params + 1:
                return None
            for param_index, param_node in enumerate(params):
                variables.extend(
                    self._extract_variable(
                        s.step, param_node, num_params - param_index - 1,
                        origin="FunctionDefinition"))
        except KeyError:
            return None
        return Function(name=name, parameters=variables)

    def _search_FunctionReturn(self, s: Step, stmt: dict) -> Optional[Function]:
        variables = []
        try:
            name = stmt["name"]
            params = stmt["returnParameters"]["parameters"]
            num_params = len(params)
            if len(s.step.stack) < num_params + 2:
                return None
            for param_index, param_node in enumerate(params):
                variables.extend(
                    self._extract_variable(
                        s.step, param_node, num_params - param_index,
                        origin="FunctionReturn"))
                for var in variables:
                    var.scope = "return"
        except KeyError:
            return None
        return Function(name=name, parameters=variables)

    def step(self):
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

        variables = []
        if not variables and "ExpressionStatement" in ast and s.step.op == "SWAP1":
            variables.extend(
                self._search_ExpressionStatement(s, ast["ExpressionStatement"]))
        if not variables and "VariableDeclarationStatement" in ast and s.step.op in ("SWAP1", "SWAP2", "SWAP3"):
            variables.extend(
                self._search_VariableDeclarationStatement(s, ast["VariableDeclarationStatement"]))
        if not variables and "FunctionDefinition" in ast and s.step.op == "JUMP":
            function = self._search_FunctionReturn(s, ast["FunctionDefinition"])
            if function is not None and f.function is not None and f.function.name == function.name:
                variables.extend(function.parameters)
        if not variables and "FunctionDefinition" in ast and s.step.op == "JUMPDEST":
            function = self._search_FunctionDefinition(s, ast["FunctionDefinition"])
            if function is not None and f.function is None:
                variables.extend(function.parameters)
                f.function = function
        if not variables and s.step.op == "CALLVALUE":
            snext = self._get_window_rel(1)
            if snext.valid:
                varvalue = int(snext.step.stack[-1], 16)
                variables.extend([
                    Variable(vtype="uint256", name="msg.value", value=varvalue, scope="function")])
        for var in variables:
            if var.scope == "line":
                s.values[var.name] = var
            elif var.scope == "function":
                f.locals[var.name] = var
            elif var.scope == "return":
                f.returnValues.append(var)

    def get_frames(self) -> List[Frame]:
        return self._frames[::-1]

    def get_callstack_depth(self) -> int:
        return len(self._frames)

    def get_variables(self) -> Dict[str, Variable]:
        s = self._get_window_rel(0)
        f = self._get_frame(0)
        out = {}  # type: Dict[str, Variable]
        out.update(f.locals)
        out.update(s.values)
        return out

    def get_step(self, i=0) -> Step:
        return self._get_window_rel(i)
