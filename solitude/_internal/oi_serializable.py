# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from abc import ABC, abstractmethod


class ISerializable(ABC):
    @abstractmethod
    def to_obj(self):
        return {}

    @staticmethod
    @abstractmethod
    def from_obj(obj):
        return None
