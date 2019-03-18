# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Tuple, Dict, Optional  # noqa
import functools
import sys
import os
import cmd
import json
from solitude import Factory, read_config_file
from solitude.cli.colors import ColorText, Color
from solitude.cli.ui_base import ObjectUI, CmdException, parse_args
from solitude.client.debug_interactive import Debugger, Step, Function, Frame, Variable  # noqa
from solitude.client.debug_trace import DebugTracer, TraceStep  # noqa


def main_debug(args):
    Color.enable()
    factory = Factory(read_config_file(args.config))
    client = factory.create_client()
    idbg = InteractiveDebuggerCLI(InteractiveDebuggerOUI(args.txhash, client))
    if args.ex:
        for command in args.ex:
            for c in command.split(";"):
                print(idbg.prompt + c)
                result = idbg.onecmd(c.strip())
                if result:
                    return
    idbg.cmdloop()


class InteractiveDebuggerCLI(cmd.Cmd):
    def __init__(self, oui: "InteractiveDebuggerOUI", stdout=sys.stdout):
        super().__init__()
        self._stdout = stdout
        self.oui = oui
        self.prompt = Color.wrap('(sold) ', color="reset")
        self._color_info = "yellow"
        self._color_error = "red"
        self._logfile = None  # "cmdlog.txt"

        self._command_executors = {
            "step": functools.partial(self.oui_arglist, name="step"),
            "continue": functools.partial(self.oui_arglist, name="continue"),
            "c": functools.partial(self.oui_arglist, name="continue"),
            "s": functools.partial(self.oui_arglist, name="step"),
            "stepi": functools.partial(self.oui_arglist, name="stepi"),
            "si": functools.partial(self.oui_arglist, name="stepi"),
            "next": functools.partial(self.oui_arglist, name="next"),
            "n": functools.partial(self.oui_arglist, name="next"),
            "finish": functools.partial(self.oui_arglist, name="finish"),
            "backtrace": functools.partial(self.oui_arglist, name="backtrace"),
            "bt": functools.partial(self.oui_arglist, name="backtrace"),
            "list": functools.partial(self.oui_arglist, name="list"),
            "break": functools.partial(self.oui_arglist, name="break"),
            "b": functools.partial(self.oui_arglist, name="break"),
            "frame": functools.partial(self.oui_arglist, name="frame"),
            "f": functools.partial(self.oui_arglist, name="frame"),
            "delete": functools.partial(self.oui_arglist, name="delete"),
            "print": functools.partial(self.oui_arglist, name="print"),
            "p": functools.partial(self.oui_arglist, name="print"),
            "info": self.oui_info,
            "quit": self.cmd_quit,
            "q": self.cmd_quit
        }

        self._oui_presenters = {
            "step": self.present_step,
            "breakpoint": self.present_breakpoint,
            "revert": self.present_revert,
            "terminate": self.present_terminate,
            "print": self.present_print,
            "info_locals": self.present_info_locals,
            "info_args": self.present_info_args,
            "info_breakpoints": self.present_info_breakpoints,
            "backtrace": self.present_backtrace,
            "frame": self.present_frame,
            "list": self.present_list,
            "break": self.present_break,
            "delete": self.present_delete,
            "end": self.present_end
        }

    def cmd_quit(self, args):
        return True

    def present_status_end(self, obj):
        self.print_error("Program terminated")

    def present_status_error(self, obj):
        errname = obj.get("what", {}).get("name")
        errdesc = obj.get("what", {}).get("message")

        self.print_error("Error: %s, %s" % (
            errname if errname else "<unknown>",
            errdesc if errdesc else "<unknown>"))

    def oui_arglist(self, name, args):
        obj = self.call(name, *args)
        status = obj["status"]
        if status == "ok":
            response = obj["response"]
            return self._oui_presenters[response["type"]](response)
        elif status == "end":
            return self.present_status_end(obj)
        else:
            return self.present_status_error(obj)

    def oui_info(self, args):
        try:
            name = "info_" + args[0]
        except IndexError:
            self.print_error("Unknown Command")
            return
        return self.oui_arglist(name=name, args=args[1:])

    def default(self, line):
        try:
            args = parse_args(line)
        except ValueError:
            self.print_error("Invalid Syntax")
            return
        if args[0] not in self._command_executors:
            self.print_error("Unknown Command")
            return
        return self._command_executors[args[0]](args=args[1:])

    def present_step(self, obj):
        assert obj["type"] == "step"
        self.print_code(obj["code"])
        assigned_values = obj["assigned_values"]
        for value in sorted(assigned_values, key=lambda x: x["name"]):
            self.print_info("Assign: %s" % str(value["string"]))
        if obj["is_return"]:
            for var in obj["return_values"]:
                self.print_info("Return: %s" % var["string"])

    def present_breakpoint(self, obj):
        assert obj["type"] == "breakpoint"
        code = obj["code"]
        self.print_info("Breakpoint: %s" % InteractiveDebuggerCLI.format_code_location(code))
        self.print_code(code)

    def present_revert(self, obj):
        assert obj["type"] == "revert"
        code = obj["code"]
        self.print_info("Revert: %s" % InteractiveDebuggerCLI.format_code_location(code))
        self.print_code(code)

    def present_terminate(self, obj):
        assert obj["type"] == "terminate"
        self.print_info("Execution terminated")

    def present_print(self, obj):
        assert obj["type"] == "print"
        if not obj["frame_found"]:
            self.print_error("Frame not found: %d" % obj["frame_index"])
        elif not obj["variable_found"]:
            self.print_error("Symbol not found: '%s'" % obj["variable_name"])
        else:
            self.print_info("Variable: %s" % obj["variable"]["string"])

    def present_info_locals(self, obj):
        assert obj["type"] == "info_locals"
        if not obj["frame_found"]:
            self.print_error("frame not found: %d" % obj["frame_index"])
        else:
            for var in obj["variables"]:
                self.print_info("Variable: %s" % var["string"])

    def present_info_args(self, obj):
        assert obj["type"] == "info_args"
        if not obj["frame_found"]:
            self.print_error("frame not found: %d" % obj["frame_index"])
        elif not obj["function_found"]:
            self.print_error("No information available")
        else:
            self.print_info("Call: %s" % obj["function"]["string"])

    def present_info_breakpoints(self, obj):
        assert obj["type"] == "info_breakpoints"
        for breakpoint in obj["breakpoints"]:
            self.print_info("Breakpoint: %s" % breakpoint)

    def present_backtrace(self, obj):
        assert obj["type"] == "backtrace"
        for f in obj["frames"]:
            self.print_info("#%d %s" % (f["index"], f["description"]))

    def present_frame(self, obj):
        assert obj["type"] == "frame"
        if not obj["frame_found"]:
            self.print_error("Frame not found: #%d" % obj["frame_index"])
            return
        self.print_info("Selected frame: #%d" % obj["frame_index"])
        self.print_code(obj["code"])

    def present_list(self, obj):
        assert obj["type"] == "list"
        self.print_code(obj["code"])

    def present_break(self, obj):
        assert obj["type"] == "break"
        self.print_info("Breakpoint Added: '%s'" % obj["breakpoint_name"])

    def present_delete(self, obj):
        assert obj["type"] == "delete"
        if obj["breakpoint_found"]:
            self.print_info("Breakpoint Deleted: '%s'" % obj["breakpoint_name"])
        else:
            self.print_info("Breakpoint not found: '%s'" % obj["breakpoint_name"])

    def present_end(self, obj):
        assert obj["type"] == "end"
        self.print_info("Program Terminated")

    def print_info(self, text):
        print(Color.wrap("[I] " + text, color=self._color_info), file=self._stdout)

    def print_error(self, text):
        print(Color.wrap("[E] " + text, color=self._color_error), file=self._stdout)

    def print_code(self, code):
        colortext = ColorText.from_obj(code["colortext"])
        print(Color.wrap(colortext), file=self._stdout)

    @staticmethod
    def format_code_location(code):
        return "{path}:{line}:{col}".format(
            path=code["path"],
            line=1 + code["line_index"],
            col=code["line_pos"])

    def call(self, command, *args):
        inp = dict(command=command, args=args)
        out = self.oui.call(inp)
        if self._logfile is not None:
            with open(self._logfile, "a+") as fp:
                fp.write("SEND " + json.dumps(inp) + "\n")
                fp.write("RECV " + json.dumps(out) + "\n")
        return out

    def do_dev(self, line):
        args = parse_args(line)
        what = args[0]
        if what == "stack":
            s = self.oui.dbg.get_step(0)
            self.print_info("Stack: %s" % str(s.step.stack))
        elif what == "memory":
            s = self.oui.dbg.get_step(0)
            self.print_info("Memory: %s" % str(s.step.memory))
        elif what == "storage":
            s = self.oui.dbg.get_step(0)
            self.print_info("Storage: %s" % str(s.step.storage))
        elif what == "code":
            import code
            code.interact(local=locals())


class InteractiveDebuggerOUI(ObjectUI):
    def __init__(self, txhash, client, code_lines=(3, 6)):
        super().__init__()
        self.client = client
        self.dbg = Debugger(client, txhash, windowsize=50)
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
                for var in f.returnValues:
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
        colortext = get_source_lines(
            step, strip=False,
            before=before if before is not None else self._code_lines[0],
            after=after if after is not None else self._code_lines[1])
        absolute_path = step.code.path
        if (absolute_path is not None) and not absolute_path.startswith("source#"):
            absolute_path = os.path.abspath(absolute_path)
        return {
            "path": step.code.path,
            "absolute_path": absolute_path,
            "line_index": step.code.line_index,
            "line_pos": step.code.line_pos,
            "line_start": step.code.line_start,
            "text": colortext.to_string(colored=False),
            "colortext": colortext.to_obj()
        }

    def _check_break(self, depth):
        s = self.dbg.get_step(0)
        prev = self.dbg.get_step(-1)
        if s.step.op == "REVERT":
            raise CmdException("revert")
        if s.step.op == "JUMPDEST" and prev.valid and prev.step.jumptype != "o" and depth > 0:
            if "FunctionDefinition" in s.ast:
                ast = s.ast["FunctionDefinition"]
                function_name = ast["name"]
                if self._function_def_look_ahead(function_name):
                    return
                names = [
                    function_name,
                    s.step.contract_name + "." + function_name]
                for name in names:
                    if name in self._breakpoints:
                        raise CmdException("breakpoint")

        if s.step.code.path is not None:
            if (
                    (not prev.valid) or (
                        (s.step.code.path, s.step.code.line_index) !=
                        (prev.step.code.path, prev.step.code.line_index))):
                file_bp_name = "%s:%d" % (os.path.split(s.step.code.path)[-1], 1 + s.step.code.line_index)
                if file_bp_name in self._breakpoints:
                    raise CmdException("breakpoint")

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
                raise CmdException("terminate")
            self._check_break(depth)
            if function == "stepi":
                raise CmdException("step")
            elif function == "step":
                if not prev.valid and s.valid:
                    raise CmdException("step")
                if not InteractiveDebuggerOUI._same_source(s.step, prev.step):
                    raise CmdException("step")
                if len(s.values):
                    raise CmdException("step")
            elif function == "next":
                depth = self.dbg.get_callstack_depth()
                if depth <= prev_depth:
                    if not prev.valid and s.valid:
                        raise CmdException("step")
                    if not InteractiveDebuggerOUI._same_source(s.step, prev.step):
                        raise CmdException("step")
                    if len(s.values):
                        raise CmdException("step")
            elif function == "finish":
                depth = self.dbg.get_callstack_depth()
                next_s = self.dbg.get_step(1)
                if not next_s.valid:
                    raise CmdException("step", args=["warning", "program_terminated"])
                if depth < prev_depth:
                    raise CmdException("step", args=["warning", "unexpected_return"])
                if depth == prev_depth and next_s.event.event == "pop":
                    raise CmdException("step", args=["return"])

    def _get_variables(self, iframe, istep):
        frames = self.dbg.get_frames()
        f = frames[iframe]
        s = self.dbg.get_step(istep)
        variables = {}
        variables.update(f.locals)
        variables.update(s.values)
        return variables

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
            variables = self._get_variables(self._current_frame, 0)
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
            variables = self._get_variables(self._current_frame, 0)
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
            raise CmdException("_syntax")
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
                prev_line = get_source_lines(f.prev, strip=True, color=None)
                cur_line = get_source_lines(f.cur, strip=True, color=None)
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


def main_trace(args):
    Color.enable()

    factory = Factory(read_config_file(args.config))
    client = factory.create_client()
    debugger = Debugger(client, args.txhash)
    printer = TablePrinter([
        ("INDEX", 6),
        ("PC", 6),
        ("JU", 2),
        ("OP", 8),
        ("GAS", 8),
        ("FILE", -30),
        ("SOURCE", 0)
    ])
    printer.write_header()

    while True:
        debugger.step()
        s = debugger.get_step()
        if not s.valid:
            break
        frames = debugger.get_frames()

        line = Color.wrap(get_source_lines(s.step, color="green"))
        printer.write([
            s.step.index,
            s.step.pc,
            s.step.jumptype,
            s.step.op,
            s.step.gas,
            "%s:%d" % (str(s.step.code.path).split(os.path.sep)[-1], s.step.code.line_index),
            line])

        if args.variables:
            for var in debugger.get_variables().values():
                print(var)
        if args.frames:
            PRE = (printer.width * " ")
            for f in frames:
                if f.prev is not None and f.cur is not None:
                    prev_line = Color.wrap(get_source_lines(f.prev, strip=True, color="blue"))
                    cur_line = Color.wrap(get_source_lines(f.cur, strip=True, color="blue"))
                    if f.function is not None:
                        print(PRE + str(f.function))
                    else:
                        print((printer.width * " ") + prev_line + " => " + cur_line)
        if args.stack:
            print(s.step.stack)
        if args.memory:
            print(s.step.memory)
        if args.storage:
            print(s.step.storage)


class TablePrinter:
    def __init__(self, cols: List[Tuple[str, int]], file=sys.stdout):
        self._fp = file
        self._sizes = [x[1] for x in cols]
        self._header = [x[0] for x in cols]
        self.width = sum(abs(x[1]) for x in cols)

    def write_header(self):
        self.write(self._header)

    def write(self, row: list):
        assert(len(row) == len(self._sizes))
        text = []
        for i, element in enumerate(row):
            x = str(element)
            c = self._sizes[i]
            if len(x) < abs(c):
                text.append(x + (" " * (abs(c) - len(x))))
            elif c > 0:
                text.append(x[:c])
            elif c < 0:
                text.append(x[c:])
            else:
                text.append(x)
        print("".join(text), file=self._fp)


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
