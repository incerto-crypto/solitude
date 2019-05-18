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
from solitude.tools import Solc, GanacheCli, EthLint
from solitude.server import kill_all_servers


ARGS = SimpleNamespace()


def pytest_addoption(parser):
    parser.addoption(
        "--local-tools",
        action="store_true",
        help="Expect all tools to be found at ~/.solitude-dev/testing/")


def pytest_runtest_setup(item):
    global ARGS
    ARGS.USE_LOCAL_TOOLDIR = item.config.getoption("--local-tools")
    if "require_local_tools" in item.keywords and not ARGS.USE_LOCAL_TOOLDIR:
        pytest.skip("test requires tools to be installed locally")


DEFAULT_CONFIG = make_default_config()
SOLIDITY_VERSION = DEFAULT_CONFIG["Tools.Solc.Version"]
SOLIDITY_ALL_VERSIONS = [
    "0.4.16", "0.4.17", "0.4.18", "0.4.19", "0.4.20", "0.4.21", "0.4.22",
    "0.4.23", "0.4.24", "0.4.25",

    "0.5.0", "0.5.1", "0.5.2", "0.5.3", "0.5.4", "0.5.5", "0.5.6", "0.5.7",
    "0.5.8"
]
GANACHE_VERSION = DEFAULT_CONFIG["Tools.GanacheCli.Version"]
GANACHE_ALL_VERSIONS = [
    "6.1.5", "6.1.6", "6.1.7", "6.1.8",
    "6.2.0", "6.2.1", "6.2.2", "6.2.3", "6.2.4", "6.2.5",
    "6.3.0",
    "6.4.0", "6.4.1", "6.4.2"
]
ETHLINT_VERSION = DEFAULT_CONFIG["Tools.EthLint.Version"]
ETHLINT_ALL_VERSIONS = [
    "1.2.0", "1.2.1", "1.2.2", "1.2.3", "1.2.4"
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


class TmpTestDir:
    def __init__(self, path):
        self._base = path

    @property
    def path(self):
        return self._base

    def makedirs(self, dirname):
        path = os.path.join(self._base, *dirname.split("/"))
        os.makedirs(path, exist_ok=True)

    def create(self, filename, contents):
        path = os.path.join(self._base, *filename.split("/"))
        dirname = os.path.dirname(path)
        os.makedirs(dirname, exist_ok=True)
        with open(path, "w" + ("b" if isinstance(contents, bytes) else "")) as fp:
            fp.write(contents)
        return path


class WorkingDir:
    def __init__(self, path):
        self._prev = os.getcwd()
        self._cur = path

    def __enter__(self):
        os.chdir(self._cur)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self._prev)


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
    cfg["Project.SourceDir"] = None
    cfg["Project.ObjectDir"] = None
    cfg["Server.Port"] = 8700
    cfg["Testing.RunServer"] = True
    try:
        ctx = SOL_new(cfg)
        yield ctx
        ctx.teardown()
    finally:
        kill_all_servers()


@pytest.fixture(scope="module")
def attila(sol):
    return sol.address(ATTILA)


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
def tool_ethlint(tooldir):
    tool = EthLint(tooldir=tooldir, version=ETHLINT_VERSION)
    if not tool.have():
        tool.add()
    yield tool
