# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Tuple, Dict, Optional  # noqa
import functools
import sys
import os
import cmd
import binascii
import json

from solitude.common.errors import CLIError
from solitude import Factory, read_config_file
from solitude._internal.oi_common_objects import ColorText
from solitude._internal.oi_interface import ObjectInterface, ObjectInterfaceException, parse_args
from solitude.debugger.evm_debug_core import EvmDebugCore, Step, Function, Frame, Value  # noqa
from solitude.debugger.evm_trace import TraceStep  # noqa
from solitude.debugger.oi_debugger import InteractiveDebuggerOI
from solitude._commandline.color_util import Color


def main(args):
    if args.json:
        run_json_debug(args)
    else:
        run_console_debug(args)

def run_json_debug(args):
    factory = Factory(read_config_file(args.config))
    client = factory.create_client()
    client.update_contracts(factory.get_objectlist())

    idbg = InteractiveDebuggerOI(args.txhash, client)
    while True:
        command = json.loads(input())
        res = idbg.call(command)
        print(json.dumps(res))
        if "quit" in res:
            return

def run_console_debug(args):
    Color.enable()
    factory = Factory(read_config_file(args.config))
    client = factory.create_client()
    client.update_contracts(factory.get_objectlist())

    idbg = InteractiveDebuggerCLI(InteractiveDebuggerOI(args.txhash, client))
    if args.ex:
        for command in args.ex:
            for c in command.split(";"):
                print(idbg.prompt + c)
                result = idbg.onecmd(c.strip())
                if result:
                    return
    idbg.cmdloop()


class InteractiveDebuggerCLI(cmd.Cmd):
    def __init__(self, oi: InteractiveDebuggerOI, stdout=sys.stdout):
        super().__init__()
        self._stdout = stdout
        self.oi = oi
        self.prompt = Color.wrap('(sold) ', color="reset")
        self._color_info = "yellow"
        self._color_error = "red"
        self._logfile = None  # "cmdlog.txt"

        self._command_executors = {
            "step": functools.partial(self.oi_arglist, name="step"),
            "continue": functools.partial(self.oi_arglist, name="continue"),
            "c": functools.partial(self.oi_arglist, name="continue"),
            "s": functools.partial(self.oi_arglist, name="step"),
            "stepi": functools.partial(self.oi_arglist, name="stepi"),
            "si": functools.partial(self.oi_arglist, name="stepi"),
            "next": functools.partial(self.oi_arglist, name="next"),
            "n": functools.partial(self.oi_arglist, name="next"),
            "finish": functools.partial(self.oi_arglist, name="finish"),
            "backtrace": functools.partial(self.oi_arglist, name="backtrace"),
            "bt": functools.partial(self.oi_arglist, name="backtrace"),
            "list": functools.partial(self.oi_arglist, name="list"),
            "break": functools.partial(self.oi_arglist, name="break"),
            "b": functools.partial(self.oi_arglist, name="break"),
            "frame": functools.partial(self.oi_arglist, name="frame"),
            "f": functools.partial(self.oi_arglist, name="frame"),
            "delete": functools.partial(self.oi_arglist, name="delete"),
            "print": functools.partial(self.oi_arglist, name="print"),
            "p": functools.partial(self.oi_arglist, name="print"),
            "info": self.oi_info,
            "quit": self.cmd_quit,
            "q": self.cmd_quit
        }

        self._oi_presenters = {
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

    def oi_arglist(self, name, args):
        obj = self.call(name, *args)
        status = obj["status"]
        if status == "ok":
            response = obj["response"]
            return self._oi_presenters[response["type"]](response)
        elif status == "end":
            return self.present_status_end(obj)
        else:
            return self.present_status_error(obj)

    def oi_info(self, args):
        try:
            name = "info_" + args[0]
        except IndexError:
            self.print_error("Unknown Command")
            return
        return self.oi_arglist(name=name, args=args[1:])

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
        out = self.oi.call(inp)
        if self._logfile is not None:
            with open(self._logfile, "a+") as fp:
                fp.write("SEND " + json.dumps(inp) + "\n")
                fp.write("RECV " + json.dumps(out) + "\n")
        return out

    def do_dev(self, line):
        args = parse_args(line)
        what = args[0]
        if what == "stack":
            s = self.oi.dbg.get_step(0)
            self.print_info("Stack: %s" % str(s.step.stack))
        elif what == "memory":
            s = self.oi.dbg.get_step(0)
            self.print_info("Memory: %s" % str(s.step.memory))
        elif what == "storage":
            s = self.oi.dbg.get_step(0)
            self.print_info("Storage: %s" % str(s.step.storage))
        elif what == "code":
            import code
            code.interact(local=locals())
