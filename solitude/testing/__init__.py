# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude.testing.context import TestingContext, SOL_new
from solitude.testing.fixtures import sol

SOL = TestingContext

__all__ = [
    "SOL_new",
    "SOL",
    "TestingContext",
    "sol"
]
