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

from solitude.common import (update_global_config, read_yaml_or_json, read_config_file)
from solitude.common.errors import CLIError


def _update_global_config_from_file(path):
    cfg_from_file = read_yaml_or_json(path)
    update_global_config(cfg_from_file)


def txhash_type(txhash):
    try:
        if not txhash.startswith("0x"):
            raise ValueError()
        return binascii.unhexlify(txhash[2:])
    except ValueError:
        raise CLIError("TXHASH format must be a hex string prefixed with 0x")


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-g", "--global-config", dest="global_config", type=str,
        default="resource://global_config.json",
        help="Global configuration file")
    parser.add_argument(
        "-c", "--config", type=str,
        default="./solitude.yaml",
        help="Project configuration file")
    sub = parser.add_subparsers()

    # create subparsers
    p_init = sub.add_parser("init")
    p_install = sub.add_parser("install")
    p_compile = sub.add_parser("compile")
    p_debug = sub.add_parser("debug")
    p_trace = sub.add_parser("trace")
    p_lint = sub.add_parser("lint")
    p_server = sub.add_parser("server")

    def module_init():
        from solitude._commandline import cmd_init
        return cmd_init
    p_init.set_defaults(module=module_init)

    def module_install():
        from solitude._commandline import cmd_install
        return cmd_install
    p_install.set_defaults(module=module_install)

    def module_compile():
        from solitude._commandline import cmd_compile
        return cmd_compile
    p_compile.set_defaults(module=module_compile)

    def module_debug():
        from solitude._commandline import cmd_debug
        return cmd_debug
    p_debug.set_defaults(module=module_debug)
    p_debug.add_argument(
        "txhash", type=txhash_type,
        help="Transaction hash, a hex string prefixed with 0x")
    p_debug.add_argument(
        "--eval-command", "-ex", action="append", help="Execute command at start", dest="ex")

    def module_trace():
        from solitude._commandline import cmd_trace
        return cmd_trace
    p_trace.set_defaults(module=module_trace)
    p_trace.add_argument("txhash", type=txhash_type)
    p_trace.add_argument("--variables", action="store_true")
    p_trace.add_argument("--frames", action="store_true")
    p_trace.add_argument("--stack", action="store_true")
    p_trace.add_argument("--memory", action="store_true")
    p_trace.add_argument("--storage", action="store_true")

    def module_lint():
        from solitude._commandline import cmd_lint
        return cmd_lint
    p_lint.set_defaults(module=module_lint)
    p_lint.add_argument(
        "--report",
        help="Path to report (enable report output mode)")
    p_lint.add_argument(
        "--report-template", dest="report_template",
        help="Path to report template",
        default="resource://report.filemessage.default.html")

    def module_server():
        from solitude._commandline import cmd_server
        return cmd_server
    p_server.set_defaults(module=module_server)
    p_server.add_argument(
        "--port", type=int, default=0, help="Override server port")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    if not hasattr(args, "module"):
        parser.print_help()
        return 1

    try:
        _update_global_config_from_file(args.global_config)
        module = args.module()
        module.main(args)
    except CLIError as e:
        print("Error: %s" % str(e), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
