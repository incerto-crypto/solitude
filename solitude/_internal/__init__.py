# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude._internal.enum_type import EnumType
from solitude._internal.error_util import (
    internal_assert, isfile_assert, value_assert, type_assert, RaiseForParam)
from solitude._internal import config_schema

from solitude._internal.oi_serializable import ISerializable
from solitude._internal.oi_interface import ObjectInterface, ObjectInterfaceException
from solitude._internal.oi_common_objects import ColorText


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

    "ISerializable",
    "ObjectInterface",
    "ObjectInterfaceError",
    "ColorText"
]
