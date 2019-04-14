# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
from solitude._internal.errors import InternalError


def internal_assert(cond: bool, message: str, data=None):
    if not cond:
        raise InternalError(message, data)


def value_assert(cond: bool, message: str):
    if not cond:
        raise ValueError(message)


def type_assert(instance, class_or_tuple, message=""):
    if not isinstance(instance, class_or_tuple):
        if isinstance(class_or_tuple, tuple):
            raise TypeError(
                "Expected one of %s" % repr(tuple(x.__name__ for x in class_or_tuple)) + message)
        else:
            raise TypeError("Expected %s" % repr(class_or_tuple.__name__) + message)


def isfile_assert(path):
    if not isinstance(path, str) or not os.path.isfile(path):
        raise ValueError("File does not exist: %s" % repr(path))


class RaiseForParam:
    def __init__(self, name: str):
        self._name = name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if (exc_type in (ValueError, TypeError)) and len(exc_val.args) == 1:
            exc_val.args = (("In parameter %s: " % repr(self._name)) + exc_val.args[0], )
