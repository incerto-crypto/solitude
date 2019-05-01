# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Dict  # noqa
import threading
import time
import re
import textwrap
import pytest
from solitude.common import ContractSourceList
from solitude.compiler import Compiler
from solitude.server import RPCTestServer, kill_all_servers
from solitude.client import ETHClient, BatchCaller, ContractBase
from conftest import (  # noqa
    tooldir, tool_solc, tool_ganache, SOLIDITY_VERSION, GANACHE_VERSION)

pytestmark = [pytest.mark.base, pytest.mark.client]


PRAGMA = "pragma solidity ^{solidity_version};\n".format(
    solidity_version=SOLIDITY_VERSION)


@pytest.fixture(scope="function")
def server(tool_ganache):
    server = RPCTestServer(
        port=8545, executable=tool_ganache.get("ganache-cli"))
    server.start()
    yield server
    server.stop()
    kill_all_servers()


@pytest.fixture(scope="function")
def client(tool_solc, server):
    sources = ContractSourceList()
    compiler = Compiler(executable=tool_solc.get("solc"))
    sources.add_string(
        "TestContract",
        PRAGMA + textwrap.dedent("""
        contract TestContract {
            uint256 public a;
            uint256 public b;
            event Change(uint256 previous, uint256 current);
            event Create();
            constructor() public {
                a = 42;
                b = 1;
                emit Create();
            }
            function a_plus_b() public view returns (uint256) {
                return a + b;
            }
            function a_plus(uint256 value) public view returns (uint256) {
                return a + value;
            }
            function set_b(uint256 value) public {
                emit Change(b, value);
                b = value;
            }
        }
        """))
    compiled = compiler.compile(sources)
    client = ETHClient(endpoint=server.endpoint)
    client.update_contracts(compiled)
    return client


@pytest.fixture(scope="function")
def contracts(client):
    c = {}
    with client.account(0):
        c["TestContract"] = client.deploy(
            "TestContract", args=(), wrapper=ContractBase)
    return c


def test_0001_calls(client: ETHClient, contracts: Dict[str, ContractBase]):
    TestContract = contracts["TestContract"]

    assert TestContract.functions.a_plus_b().call() == 42 + 1

    assert TestContract.functions.a_plus(8).call() == 42 + 8

    batch = BatchCaller(client)
    batch.add_call(TestContract, "a_plus_b", ())
    batch.add_call(TestContract, "a_plus", (10,))
    results = batch.execute()
    assert results[0] == 42 + 1
    assert results[1] == 42 + 10


def test_0002_transactions(client: ETHClient, contracts: Dict[str, ContractBase]):
    TestContract = contracts["TestContract"]

    with client.account(0):
        TestContract.transact_sync("set_b", 30)
    assert TestContract.functions.a_plus_b().call() == 42 + 30


def event_is(event, contract_name, name, args):
    if event.contractname != contract_name:
        return False
    if event.name != name:
        return False
    return tuple(event.args) == tuple(args)


def test_0003_events(client: ETHClient, contracts: Dict[str, ContractBase]):
    TestContract = contracts["TestContract"]

    with client.account(0), client.capture("*:TestContract.Change"):
        TestContract.transact_sync("set_b", 50)
    events = client.get_events()
    assert len(events) == 1
    assert event_is(events[0], "TestContract", "Change", (1, 50))

    with client.account(0), client.capture(re.compile(r".*:TestContract\..*")):
        TestContract.transact_sync("set_b", 40)
    events = client.get_events()
    assert len(events) == 1
    assert event_is(events[0], "TestContract", "Change", (50, 40))

    flt = client.add_filter([TestContract], ["Change"])

    with client.account(0), client.capture("*:TestContract.*"):
        TestContract.transact_sync("set_b", 30)
    events = client.get_events()
    assert len(events) == 1
    assert event_is(events[0], "TestContract", "Change", (40, 30))

    def remove_filter():
        for i in range(50):
            if not flt.valid:
                return
            time.sleep(0.1)
        client.remove_filter(flt)

    threading.Thread(target=remove_filter, args=()).start()

    event = next(client.iter_filters([flt], interval=0.25))
    client.remove_filter(flt)
    assert event_is(event, "TestContract", "Change", (40, 30))
