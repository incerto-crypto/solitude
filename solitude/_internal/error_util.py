# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude.errors import InternalError


def internal_assert(cond, message, data=None):
    if not cond:
        raise InternalError(message, data)
