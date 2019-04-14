# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
from solitude.common.config_util import make_default_config, write_config_file
from solitude.common.errors import CLIError


def main(args):
    if os.path.exists(args.config):
        raise CLIError("Configuration file already exists: '%s'" % args.config)
    write_config_file(make_default_config(), args.config)
