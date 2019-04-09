#!/usr/bin/env python

# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Tuple  # noqa
import sys
import os
import argparse
import datetime
import binascii
import json
from solitude.errors import CompilerError, CLIError
from solitude import (
    Factory, make_default_config, write_config_file, read_config_file)
from solitude.common import file_message_format
from solitude.tools import Solc, GanacheCli, Solium

from solitude._internal.config_util import read_yaml_or_json_file
from solitude._internal.resource_util import update_global_config

from solitude.cli.debug import main_debug, main_trace


def main_init(args):
    if os.path.exists(args.config):
        raise CLIError("%s already exists" % args.config)
    write_config_file(make_default_config(), args.config)


def _update_global_config_from_file(path):
    cfg_from_file = read_yaml_or_json_file(path)
    update_global_config(cfg_from_file)


def _iter_required_tools(cfg):
    required = cfg["Tools.Required"]  # type: List[str]
    tooldir = os.path.expanduser(cfg["Tools.Directory"])
    if "Solc" in required:
        yield Solc(tooldir, cfg["Tools.Solc.Version"])
    if "GanacheCli" in required:
        yield GanacheCli(tooldir, cfg["Tools.GanacheCli.Version"])
    if "Solium" in required:
        yield Solium(tooldir, cfg["Tools.Solium.Version"])


def _install_if_not_have(tool):
    if tool.have():
        print("Found %s %s" % (tool.name, tool.version))
    else:
        print("Installing %s %s" % (tool.name, tool.version))
        tool.add()
        print("Installed %s" % tool.name)


def _check_have(tool):
    if not tool.have():
        raise CLIError(
            "Tool not installed: %s %s. To install all required tools, run:\n    solitude install" % (
                tool.name, tool.version))


def _require_tool(cfg, name):
    for tool in _iter_required_tools(cfg):
        if tool.name == name:
            if not tool.have():
                break
            return tool
    raise CLIError("This function requires a tool which is not installed: %s" % name)


def main_install(args):
    cfg = read_config_file(args.config)
    for tool in _iter_required_tools(cfg):
        _install_if_not_have(tool)


def main_compile(args):
    cfg = read_config_file(args.config)
    factory = Factory(cfg)
    compiler = factory.create_compiler(add_contract_dir=True)
    try:
        compiled = compiler.compile()
    except CompilerError as e:
        for message in e.messages:
            print(file_message_format(message), file=sys.stderr)
        sys.exit(1)
    compiled.save_directory(cfg["Compiler.BuildDir"])


def main_lint(args):
    from solitude.common.report import FileMessageReport
    cfg = read_config_file(args.config)
    factory = Factory(cfg)
    linter = factory.create_linter(add_contract_dir=True)
    errors = False

    if args.report:
        report = FileMessageReport(
            args.report_template,
            project=cfg["Project.Name"],
            component="Linter")
        report.add_info("Timestamp", datetime.datetime.utcnow().isoformat())
        files_without_errors = []
        for filename, output in linter.lint_iter():
            if len(output):
                errors = True
                report.add_file(filename, output)
            else:
                files_without_errors.append(filename)
        for filename in files_without_errors:
            report.add_file(filename, [])
        with open(args.report, "w") as fp:
            report.dump(fp)
    else:
        for filename, output in linter.lint_iter():
            for message in output:
                errors = True
                print(file_message_format(message), file=sys.stderr)
    if errors:
        sys.exit(1)


def main_server(args):
    import time
    from solitude.server import kill_all_servers
    cfg = read_config_file(args.config)
    if args.port > 0:
        cfg["Server.Port"] = args.port
    factory = Factory(cfg)
    server = factory.create_server()
    try:
        server.start()
        print("Server started at: %s" % server.endpoint)
        print("Ctrl-C to quit")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        print("Shutdown...")
        server.stop()
    finally:
        kill_all_servers()


def txhash_type(txhash):
    assert(txhash.startswith("0x"))
    return binascii.unhexlify(txhash[2:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--global-config", dest="global_config", type=str, help="Global configuration file")
    parser.add_argument("-c", "--config", type=str, default="./solitude.yaml", help="Project configuration file")
    sub = parser.add_subparsers()

    # write default config
    p_init = sub.add_parser("init")
    p_init.set_defaults(func=main_init)

    # install tools
    p_install = sub.add_parser("install")
    p_install.set_defaults(func=main_install)

    # compile
    p_compile = sub.add_parser("compile")
    p_compile.set_defaults(func=main_compile)

    # debug
    p_debug = sub.add_parser("debug")
    p_debug.set_defaults(func=main_debug)
    p_debug.add_argument(
        "--eval-command", "-ex", action="append", help="Execute command at start", dest="ex")
    p_debug.add_argument("txhash", type=txhash_type)

    # trace
    p_trace = sub.add_parser("trace")
    p_trace.set_defaults(func=main_trace)
    p_trace.add_argument("txhash", type=txhash_type)
    p_trace.add_argument("--variables", action="store_true")
    p_trace.add_argument("--frames", action="store_true")
    p_trace.add_argument("--stack", action="store_true")
    p_trace.add_argument("--memory", action="store_true")
    p_trace.add_argument("--storage", action="store_true")

    # lint
    p_lint = sub.add_parser("lint")
    p_lint.set_defaults(func=main_lint)
    p_lint.add_argument(
        "--report",
        help="Path to report (enable report output mode)")
    p_lint.add_argument(
        "--report-template", dest="report_template",
        help="Path to report template",
        default="resource://report.filemessage.default.html")

    p_server = sub.add_parser("server")
    p_server.set_defaults(func=main_server)
    p_server.add_argument(
        "--port", type=int, default=0, help="Override server port")

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        exit(1)
    try:
        if args.global_config is not None:
            _update_global_config_from_file(args.global_config)
        args.func(args)
    except CLIError as e:
        print("Error: %s" % str(e))
        exit(1)
    exit(0)


if __name__ == "__main__":
    main()
