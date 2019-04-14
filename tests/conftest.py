# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import pytest
import tempfile
import shutil
import os
from types import SimpleNamespace
from solitude.common import update_global_config
from solitude import make_default_config
from solitude.testing import SOL_new
from solitude.tools import Solc, GanacheCli, Solium
from solitude.server import kill_all_servers


ARGS = SimpleNamespace()


def pytest_addoption(parser):
    parser.addoption(
        "--internet",
        action="store_true",
        help="enable tests marked with 'internet' (lots of downloads)")
    parser.addoption(
        "--local-tools",
        action="store_true",
        help="Expect all tools to be found at ~/.solitude-dev/testing/")


def pytest_runtest_setup(item):
    global ARGS
    if "internet" in item.keywords and not item.config.getoption("--internet"):
        pytest.skip("'internet' tests disabled (enable with --internet)")
    ARGS.USE_LOCAL_TOOLDIR = item.config.getoption("--local-tools")


DEFAULT_CONFIG = make_default_config()
SOLIDITY_VERSION = DEFAULT_CONFIG["Tools.Solc.Version"]
SOLIDITY_ALL_VERSIONS = [
    "0.4.16", "0.4.17", "0.4.18", "0.4.19", "0.4.20", "0.4.21", "0.4.22",
    "0.4.23", "0.4.24", "0.4.25",

    "0.5.0", "0.5.1", "0.5.2", "0.5.3", "0.5.4", "0.5.5", "0.5.6", "0.5.7"
]
GANACHE_VERSION = DEFAULT_CONFIG["Tools.GanacheCli.Version"]
GANACHE_ALL_VERSIONS = [
    "6.1.5", "6.1.6", "6.1.7", "6.1.8",
    "6.2.0", "6.2.1", "6.2.2", "6.2.3", "6.2.4", "6.2.5",
    "6.3.0",
    "6.4.0", "6.4.1", "6.4.2"
]
SOLIUM_VERSION = DEFAULT_CONFIG["Tools.Solium.Version"]
SOLIUM_ALL_VERSIONS = [
    SOLIUM_VERSION
]

LOCAL_TOOLDIR = os.path.expanduser("~/.solitude-dev/testing")


ATTILA = 0
GEORGE = 1


@pytest.fixture(scope="module")
def tooldir():
    if ARGS.USE_LOCAL_TOOLDIR:
        yield LOCAL_TOOLDIR
    else:
        with tempfile.TemporaryDirectory() as tmp:
            yield tmp


@pytest.fixture(scope="function")
def tmpdir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture(scope="module")
def sol(request, tooldir):
    solc = Solc(tooldir=tooldir, version=SOLIDITY_VERSION)
    if not solc.have():
        solc.add()
    ganache = GanacheCli(tooldir=tooldir, version=GANACHE_VERSION)
    if not ganache.have():
        ganache.add()
    cfg = make_default_config()
    cfg["Tools.Directory"] = tooldir
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
        ctx = SOL_new(cfg)
        yield ctx
        ctx.teardown()
    finally:
        kill_all_servers()


@pytest.fixture(scope="module")
def tool_solc(tooldir):
    tool = Solc(tooldir=tooldir, version=SOLIDITY_VERSION)
    if not tool.have():
        tool.add()
    yield tool


@pytest.fixture(scope="module")
def tool_ganache(tooldir):
    tool = GanacheCli(tooldir=tooldir, version=GANACHE_VERSION)
    if not tool.have():
        tool.add()
    yield tool


@pytest.fixture(scope="module")
def tool_solium(tooldir):
    tool = Solium(tooldir=tooldir, version=SOLIUM_VERSION)
    if not tool.have():
        tool.add()
    yield tool
