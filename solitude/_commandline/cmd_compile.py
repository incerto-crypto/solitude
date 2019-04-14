# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import sys
from solitude import Factory
from solitude.errors import CLIError
from solitude.common import ContractSourceList


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

    objects.save_directory(cfg["Project.ObjectDir"])
