# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude.testing import SOL_new
from solitude.server import kill_all_servers
import pytest


@pytest.fixture(scope="module")
def sol():
    """pytest fixture for a testing context configured with the default
    configuration file, solitude.yaml.
    """
    try:
        ctx = SOL_new()
        yield ctx
        ctx.teardown()
    finally:
        kill_all_servers()
