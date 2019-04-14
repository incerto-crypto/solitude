# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree


class SolitudeError(Exception):
    pass


class InternalError(SolitudeError):
    def __init__(self, message: str, data):
        super().__init__(message)
        self._data = data
