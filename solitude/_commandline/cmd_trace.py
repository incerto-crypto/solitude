# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
from solitude import Factory, read_config_file
from solitude._internal.oi_common_objects import ColorText
from solitude._commandline.color_util import Color
from solitude._commandline.text_util import TablePrinter
from solitude.debugger import EvmDebugCore, EvmTrace, TraceStep, InteractiveDebuggerOI


def main(args):
    Color.enable()

    factory = Factory(read_config_file(args.config))
    client = factory.create_client()
    client.update_contracts(factory.get_objectlist())
    debugger = EvmDebugCore(client, args.txhash)
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

        line = Color.wrap(InteractiveDebuggerOI.get_source_lines(s.step, color="green"))
        printer.write([
            s.step.index,
            s.step.pc,
            s.step.jumptype,
            s.step.op,
            s.step.gas,
            "%s:%d" % (str(s.step.code.unitname).split(os.path.sep)[-1], s.step.code.line_index),
            line])

        if args.variables:
            for var in debugger.get_values().values():
                print(var)
        if args.frames:
            PRE = (printer.width * " ")
            for f in frames:
                if f.prev is not None and f.cur is not None:
                    prev_line = Color.wrap(InteractiveDebuggerOI.get_source_lines(f.prev, strip=True, color="blue"))
                    cur_line = Color.wrap(InteractiveDebuggerOI.get_source_lines(f.cur, strip=True, color="blue"))
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
