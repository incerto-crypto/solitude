# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree


class EnumType:
    @classmethod
    def get_values(cls) -> list:
        return list(cls._iter_values())

    @classmethod
    def _iter_values(cls) -> list:
        return (
            v for k, v in cls.__dict__.items() if not (k.startswith("_") or callable(v)))

    @classmethod
    def has_value(cls, value) -> bool:
        return any(value == v for v in cls._iter_values())

    @classmethod
    def value_assert(cls, value):
        if not cls.has_value(value):
            raise TypeError(
                "Expected value of enum {name}, one of {values}".format(
                    name=cls.__name__,
                    values=repr(cls.get_values())))
