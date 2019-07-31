# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
from solitude._internal.oi_common_objects import ColorText
from solitude._internal.oi_interface import ObjectInterface, ObjectInterfaceException
from solitude.debugger.evm_trace import TraceStep
from solitude.debugger.evm_debug_core import EvmDebugCore


class InteractiveDebuggerOI(ObjectInterface):
    def __init__(self, txhash, client, code_lines=(3, 6)):
        super().__init__()
        self.client = client
        self.dbg = EvmDebugCore(client, txhash, windowsize=50)
        self._breakpoints = set()
        self._current_frame = 0
        self._running = False

        assert len(code_lines) == 2 and all(isinstance(x, int) for x in code_lines)
        self._code_lines = code_lines

        self.command(self.cmd_print, ["print"])
        self.command(self.cmd_info_locals, ["info_locals"])
        self.command(self.cmd_info_args, ["info_args"])
        self.command(self.cmd_info_breakpoints, ["info_breakpoints"])
        self.command(self.cmd_break, ["break"])
        self.command(self.cmd_delete, ["delete"])
        self.command(self.cmd_frame, ["frame"])
        self.command(self.cmd_continue, ["continue"])
        self.command(self.cmd_step, ["step"])
        self.command(self.cmd_stepi, ["stepi"])
        self.command(self.cmd_next, ["next"])
        self.command(self.cmd_finish, ["finish"])
        self.command(self.cmd_backtrace, ["backtrace"])
        self.command(self.cmd_list, ["list"])
        self.command(self.cmd_quit, ["quit"])

        self.error(self.on_breakpoint, ["breakpoint"])
        self.error(self.on_revert, ["revert"])
        self.error(self.on_terminate, ["terminate"])
        self.error(self.on_step, ["step", "stepi", "finish"])

    def on_step(self, args):
        s = self.dbg.get_step(0)
        obj = {
            "type": "step",
            "code": self.format_code(s.step),
            "assigned_values": [],
            "is_return": False,
            "return_values": []
        }

        for name in sorted(s.values):
            obj["assigned_values"].append(s.values[name].to_obj())
        if "return" in args:
            obj["is_return"] = True
            frames = self.dbg.get_frames()
            if len(frames):
                f = frames[0]
                for var in f.return_values:
                    obj["return_values"].append(var.to_obj())
        return obj

    def on_breakpoint(self, args):
        s = self.dbg.get_step(0)
        return {
            "type": "breakpoint",
            "code": self.format_code(s.step)
        }

    def on_revert(self, args):
        s = self.dbg.get_step(0)
        return {
            "type": "revert",
            "code": self.format_code(s.step)
        }

    def on_terminate(self, args):
        self.quit()
        return {
            "type": "end"
        }

    def _get_function_name(self, s: "Step"):
        if "FunctionDefinition" in s.ast:
            return s.ast["FunctionDefinition"]["name"]
        return None

    def _function_def_look_ahead(self, name):
        push_found = False
        for i in range(1, 50):
            s = self.dbg.get_step(i)
            if s.event.event == "push":
                push_found = True
            if not s.valid:
                return False
            next_name = self._get_function_name(s)
            if next_name != name:
                return False
            if s.step.op == "JUMPDEST" and not push_found:
                return True
        return False

    def format_code(self, step, before=None, after=None):
        colortext = InteractiveDebuggerOI.get_source_lines(
            step, strip=False,
            before=before if before is not None else self._code_lines[0],
            after=after if after is not None else self._code_lines[1])
        absolute_path = step.code.unitname
        if (absolute_path is not None) and not absolute_path.startswith("source#"):
            absolute_path = os.path.abspath(absolute_path)
        return {
            "path": step.code.unitname,
            "absolute_path": absolute_path,
            "line_index": step.code.line_index,
            "line_pos": step.code.line_pos,
            "line_lenght": step.length,
            "line_start": step.code.line_start,
            "text": str(colortext),
            "colortext": colortext.to_obj()
        }

    def _check_break(self, depth):
        s = self.dbg.get_step(0)
        prev = self.dbg.get_step(-1)
        if s.step.op == "REVERT":
            raise ObjectInterfaceException("revert")
        if s.step.op == "JUMPDEST" and prev.valid and prev.step.jumptype != "o" and depth > 0:
            if "FunctionDefinition" in s.ast:
                ast = s.ast["FunctionDefinition"]
                function_name = ast["name"]
                if self._function_def_look_ahead(function_name):
                    return
                names = [
                    function_name,
                    s.step.contractname + "." + function_name]
                for name in names:
                    if name in self._breakpoints:
                        raise ObjectInterfaceException("breakpoint")

        if s.step.code.unitname is not None:
            if (
                    (not prev.valid) or (
                        (s.step.code.unitname, s.step.code.line_index) !=
                        (prev.step.code.unitname, prev.step.code.line_index))):
                file_bp_name = "%s:%d" % (os.path.split(s.step.code.unitname)[-1], 1 + s.step.code.line_index)
                if file_bp_name in self._breakpoints:
                    raise ObjectInterfaceException("breakpoint")

    @staticmethod
    def _same_source(s1, s2):
        if s1.fileno == -1 and s2.fileno == -1:
            return True
        return (s1.start, s1.length, s1.fileno) == (s2.start, s2.length, s2.fileno)

    def _continue(self, function=None):
        prev_depth = self.dbg.get_callstack_depth()
        prev = self.dbg.get_step()
        depth = 0
        while True:
            self.dbg.step()
            s = self.dbg.get_step()
            if s.event.event == "push":
                depth += 1
            elif s.event.event == "pop":
                depth -= 1
            if not s.valid:
                raise ObjectInterfaceException("terminate")
            self._check_break(depth)
            if function == "stepi":
                raise ObjectInterfaceException("step")
            elif function == "step":
                if not prev.valid and s.valid:
                    raise ObjectInterfaceException("step")
                if not InteractiveDebuggerOI._same_source(s.step, prev.step):
                    raise ObjectInterfaceException("step")
                if len(s.values):
                    raise ObjectInterfaceException("step")
            elif function == "next":
                depth = self.dbg.get_callstack_depth()
                if depth <= prev_depth:
                    if not prev.valid and s.valid:
                        raise ObjectInterfaceException("step")
                    if not InteractiveDebuggerOI._same_source(s.step, prev.step):
                        raise ObjectInterfaceException("step")
                    if len(s.values):
                        raise ObjectInterfaceException("step")
            elif function == "finish":
                depth = self.dbg.get_callstack_depth()
                next_s = self.dbg.get_step(1)
                if not next_s.valid:
                    raise ObjectInterfaceException("step", args=["warning", "program_terminated"])
                if depth < prev_depth:
                    raise ObjectInterfaceException("step", args=["warning", "unexpected_return"])
                if depth == prev_depth and next_s.event.event == "pop":
                    raise ObjectInterfaceException("step", args=["return"])

    def _get_values(self, iframe, istep):
        frames = self.dbg.get_frames()
        f = frames[iframe]
        s = self.dbg.get_step(istep)
        values = {}
        values.update(f.locals)
        values.update(s.values)
        return values

    def cmd_print(self, args):
        varname = args[0]
        obj = {
            "type": "print",
            "frame_index": self._current_frame,
            "variable_name": varname,
            "frame_found": False,
            "variable_found": False,
            "variable": None
        }
        try:
            variables = self._get_values(self._current_frame, 0)
            obj["frame_found"] = True
            try:
                variable = variables[varname]
                obj["variable_found"] = True
                obj["variable"] = variable.to_obj()
            except KeyError:
                pass
        except IndexError:
            pass
        return obj

    def cmd_info_locals(self, args):
        obj = {
            "type": "info_locals",
            "frame_index": self._current_frame,
            "frame_found": False,
            "variables": []
        }
        try:
            variables = self._get_values(self._current_frame, 0)
            obj["frame_found"] = True
            for variable in variables.values():
                obj["variables"].append(variable.to_obj())
        except IndexError:
            pass
        return obj

    def cmd_info_args(self, args):
        obj = {
            "type": "info_args",
            "frame_index": self._current_frame,
            "frame_found": False,
            "function_found": False,
            "function": None
        }
        try:
            frames = self.dbg.get_frames()
            f = frames[self._current_frame]
            obj["frame_found"] = True
            if f.function is not None:
                obj["function_found"] = True
                obj["function"] = f.function.to_obj()
        except IndexError:
            pass
        return obj

    def cmd_info_breakpoints(self, args):
        return {
            "type": "info_breakpoints",
            "breakpoints": [x for x in self._breakpoints]
        }

    def cmd_delete(self, args):
        name = args[0]
        obj = {
            "type": "delete",
            "breakpoint_found": False,
            "breakpoint_name": name
        }
        try:
            self._breakpoints.remove(name)
            obj["breakpoint_found"] = True
        except KeyError:
            pass
        return obj

    def cmd_frame(self, args):
        obj = {
            "type": "frame",
            "frame_index": 0,
            "frame_found": False,
            "code": False
        }
        try:
            frame_index = int(args[0])
            self._current_frame = frame_index
            obj["frame_index"] = frame_index
        except ValueError:
            raise ObjectInterfaceException("_syntax")
        frames = self.dbg.get_frames()
        try:
            step = frames[self._current_frame].cur
            obj["frame_found"] = True
            obj["code"] = self.format_code(step)
        except IndexError:
            pass
        return obj

    def cmd_continue(self, args):
        return self._continue("continue")

    def cmd_stepi(self, args):
        return self._continue(function="stepi")

    def cmd_step(self, args):
        return self._continue(function="step")

    def cmd_next(self, args):
        return self._continue(function="next")

    def cmd_finish(self, args):
        self.dbg.step()
        return self._continue(function="finish")

    def cmd_break(self, args):
        name = args[0]
        self._breakpoints.add(name)
        return {
            "type": "break",
            "breakpoint_name": name
        }

    def cmd_backtrace(self, args):
        obj = {
            "type": "backtrace",
            "frames": []
        }
        frames = self.dbg.get_frames()
        for i, f in enumerate(frames):
            if f.function is not None:
                obj["frames"].append({
                    "index": i,
                    "function_found": True,
                    "function": f.function.to_obj(),
                    "description": str(f.function)
                })
            elif f.prev is not None and f.cur is not None:
                prev_line = InteractiveDebuggerOI.get_source_lines(
                    f.prev, strip=True, color=None)
                cur_line = InteractiveDebuggerOI.get_source_lines(
                    f.cur, strip=True, color=None)
                obj["frames"].append({
                    "index": i,
                    "function_found": False,
                    "function": None,
                    "description": ("[ %s => %s ]" % (prev_line, cur_line))
                })
            else:
                obj["frames"].append({
                    "index": i,
                    "function_found": False,
                    "function": None,
                    "description": "?"
                })
        return obj

    def cmd_list(self, args):
        s = self.dbg.get_step()
        return {
            "type": "list",
            "code": self.format_code(s.step)
        }

    def cmd_quit(self, args):
        self.quit()
        return {
            "type": "quit"
        }

    @staticmethod
    def get_source_lines(step: TraceStep, strip=False, color="green", before=0, after=0) -> ColorText:
        out = ColorText()
        if step is None or step.fileno == -1:
            out.append("<unknown>")
            return out
        lines_before = ""
        for i in range(step.code.line_index - before, step.code.line_index):
            if i >= 0:
                lines_before += step.code.lines[i] + "\n"
        out.append(lines_before)

        source = step.code.source[step.code.line_start:]

        left = source[:step.code.line_pos]
        middle = source[step.code.line_pos:(step.code.line_pos + step.length)]
        right = source[(step.code.line_pos + step.length):]

        if strip:
            left = left.lstrip()
            right = right.rstrip()

        lines_remaining = after

        lines_count = left.count("\n")
        if lines_count > lines_remaining:
            out.append("\n".join(left.split("\n")[:1 + lines_remaining]))
            return out
        else:
            out.append(left)
            lines_remaining -= lines_count

        lines_count = middle.count("\n")
        if lines_count > lines_remaining:
            out.append("\n".join(middle.split("\n")[:1 + lines_remaining]), color=color)
            return out
        else:
            out.append(middle, color=color)
            lines_remaining -= lines_count

        if right:
            lines_count = right.count("\n")
            if lines_count > lines_remaining:
                out.append("\n".join(right.split("\n")[:1 + lines_remaining]))
            else:
                out.append(right)

        return out
