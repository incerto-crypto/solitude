# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude.common.factory import Factory
from solitude._internal.config_util import (
    read_config_file, write_config_file, config_schema_to_defaults)
from solitude._internal.config_schema import SCHEMA


def make_default_config():
    return config_schema_to_defaults(SCHEMA)


__all__ = [
    "Factory",
    "read_config_file",
    "write_config_file",
    "make_default_config"
]
