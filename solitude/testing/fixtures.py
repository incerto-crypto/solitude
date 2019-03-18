# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude.testing import SOL_new
from solitude.server import kill_all_servers
import pytest


@pytest.fixture(scope="module")
def sol():
    ctx = SOL_new()
    yield ctx
    ctx.teardown()
    kill_all_servers()
