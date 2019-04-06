# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude._internal.enum_type import EnumType
from solitude._internal.error_util import (
    internal_assert, isfile_assert, value_assert, type_assert, RaiseForParam)
from solitude._internal.resource_util import (
    get_resource_path, get_global_config, copy_from_url)
from solitude._internal import config_schema


class Config:
    SCHEMA = config_schema.SCHEMA
    SCHEMA_SCHEMA = config_schema.SCHEMA_SCHEMA


__all__ = [
    "EnumType",
    "internal_assert",
    "isfile_assert",
    "value_assert",
    "type_assert",
    "RaiseForParam",

    "Config",

    "get_resource_path",
    "get_global_config",
    "copy_from_url"
]
