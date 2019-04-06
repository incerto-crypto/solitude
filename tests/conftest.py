# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import pytest
import tempfile
import shutil
from solitude.testing import SOL_new
from solitude.tools import Solc, GanacheCli
from solitude import make_default_config
from solitude.server import kill_all_servers


def pytest_addoption(parser):
    parser.addoption(
        "--internet",
        action="store_true",
        help="enable tests marked with 'internet' (lots of downloads)")


def pytest_runtest_setup(item):
    if 'internet' in item.keywords and not item.config.getoption("--internet"):
        pytest.skip("'internet' tests disabled (enable with --internet)")


DEFAULT_CONFIG = make_default_config()
SOLIDITY_VERSION = DEFAULT_CONFIG["Tools.Solc.Version"]
GANACHE_VERSION = DEFAULT_CONFIG["Tools.GanacheCli.Version"]
SOLIUM_VERSION = DEFAULT_CONFIG["Tools.Solium.Version"]


@pytest.fixture(scope="module")
def sol(request):
    tmpdir = tempfile.mkdtemp()
    solc = Solc(tooldir=tmpdir, version=SOLIDITY_VERSION)
    solc.add()
    ganache = GanacheCli(tooldir=tmpdir, version=GANACHE_VERSION)
    ganache.add()
    cfg = make_default_config()
    cfg["Tools.Directory"] = tmpdir
    cfg["Tools.Solc.Version"] = SOLIDITY_VERSION
    cfg["Tools.GanacheCli.Version"] = GANACHE_VERSION
    cfg["Client.ContractBuildDir"] = None
    cfg["Client.ContractSources"] = []
    cfg["Client.AccountAliases"] = {
        "attila": 0
    }
    cfg["Server.Port"] = 8700
    cfg["Testing.StartServer"] = True
    try:
        ctx = SOL_new(cfg, tmpdir=tmpdir)
        yield ctx
        ctx.teardown()
    finally:
        kill_all_servers()


@pytest.fixture(scope="module")
def tooldir():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp)


@pytest.fixture(scope="module")
def tool_solc(tooldir):
    tool = Solc(tooldir=tooldir, version=SOLIDITY_VERSION)
    tool.add()
    yield tool


@pytest.fixture(scope="module")
def tool_ganache(tooldir):
    tool = GanacheCli(tooldir=tooldir, version=GANACHE_VERSION)
    tool.add()
    yield tool
