# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Dict  # noqa
import threading
import time
import re
import os
import io
import textwrap
import yaml
import pytest
from solitude.common import ContractObjectList, BuildDirectoryType, hex_repr
from solitude.compiler import Compiler
from solitude.server import ETHTestServer, kill_all_servers
from solitude.client import ETHClient, BatchCaller, ContractBase
from solitude.debugger import EvmTrace, InteractiveDebuggerOI
from solitude._commandline.cmd_debug import InteractiveDebuggerCLI

from conftest import (
    tooldir, tmpdir, TmpTestDir, WorkingDir, unpack_test_data, tool_solc, tool_ganache,
    SOLIDITY_VERSION, GANACHE_VERSION, run_solitude)

pytestmark = [pytest.mark.base, pytest.mark.client]


FNARG_TEMPLATE_UINT256 = r"{name}\(\s*uint256\s+{argname}\s*=\s*{argval}\s*\)"


def onecmd(debugger, buf, line):
    pos = buf.tell()
    debugger.onecmd(line)
    buf.seek(pos)
    out = buf.read()
    return out


@pytest.fixture(scope="function")
def test_data(tmpdir):
    return unpack_test_data(tmpdir, "truffle_fib")


@pytest.fixture(scope="function")
def server(tool_ganache):
    server = ETHTestServer(
        port=8545, executable=tool_ganache.get("ganache-cli"))
    server.start()
    yield server
    server.stop()
    kill_all_servers()


@pytest.fixture(scope="function")
def client(tool_solc, test_data, server):
    objects = ContractObjectList()
    objects.add_directory(
        os.path.join(test_data, "build", "contracts"),
        BuildDirectoryType.TRUFFLE)
    client = ETHClient(endpoint=server.endpoint)
    client.update_contracts(objects)
    return client


@pytest.fixture(scope="function")
def CallFibonacci(client):
    with client.account(client.address(0)):
        c = client.deploy("CallFibonacci", args=())
    return c


def test_0001_command(tooldir, tmpdir, server, client, test_data, CallFibonacci):
    with client.account(client.address(0)):
        tx = CallFibonacci.transact_sync("fib", 7)

    tmp = TmpTestDir(tmpdir)
    tmp.create("solitude.yaml", yaml.dump({
        "Tools.Directory": tooldir,
        "Project.ObjectDir": os.path.abspath(os.path.join(test_data, "build", "contracts")),
        "Project.ObjectDirType": BuildDirectoryType.TRUFFLE
    }))

    with WorkingDir(tmp.path):
        out = run_solitude(["trace", hex_repr(tx.txhash)])

    assert "function fib_r(uint n) internal pure returns (uint)" in out


def test_0002_debug(server, client, CallFibonacci):
    with client.account(client.address(0)):
        tx = CallFibonacci.transact_sync("fib", 7)

    buf = io.StringIO()
    debugger = InteractiveDebuggerCLI(InteractiveDebuggerOI(tx.txhash, client), stdout=buf)

    onecmd(debugger, buf, "break fib")
    onecmd(debugger, buf, "continue")
    out = onecmd(debugger, buf, "info args")
    assert re.search(FNARG_TEMPLATE_UINT256.format(name="fib", argname="n", argval="7"), out) is not None
