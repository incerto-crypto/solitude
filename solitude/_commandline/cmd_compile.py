# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import sys
from solitude import Factory
from solitude.common.errors import CLIError, CompilerError
from solitude.common import ContractSourceList, read_config_file, file_message_format


def main(args):
    cfg = read_config_file(args.config)
    factory = Factory(cfg)
    compiler = factory.create_compiler()
    sources = factory.get_sourcelist()

    try:
        objects = compiler.compile(sources)
    except CompilerError as e:
        for message in e.messages:
            print(file_message_format(message), file=sys.stderr)
        raise CLIError("Compiler error")

    objects.save_directory(cfg["Project.ObjectDir"], cfg["Project.ObjectDirType"])
