# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import datetime
import pytest
from solitude.common import ContractSourceList, ContractObjectList
from solitude.compiler import Compiler
from solitude.server import ETHTestServer, kill_all_servers
from solitude.client import ETHClient, ContractBase
from conftest import (  # noqa
    tooldir, tool_solc, tool_ganache, SOLIDITY_VERSION, GANACHE_VERSION)

pytestmark = [pytest.mark.base, pytest.mark.server]


@pytest.fixture(scope="function")
def server(tool_ganache):
    server = ETHTestServer(
        port=8545, executable=tool_ganache.get("ganache-cli"))
    server.start()
    yield server
    server.stop()
    kill_all_servers()


def test_0001_run(server: ETHTestServer):
    client = ETHClient(endpoint=server.endpoint)
    client.mine_block()
    blocktime = client.get_last_blocktime()
    now = datetime.datetime.now()
    time_bound_low = int((now - datetime.timedelta(days=1)).timestamp())
    time_bound_high = int((now + datetime.timedelta(days=1)).timestamp())
    assert(time_bound_low <= blocktime <= time_bound_high)


def test_0002_increase_time(server: ETHTestServer, tool_solc):
    TIME_OFFSET = 10000  # seconds
    TOLERANCE = 60  # seconds
    CONTRACT_NAME = "TestContract"

    sources = ContractSourceList()
    compiler = Compiler(executable=tool_solc.get("solc"))
    sources.add_string(
        "test",
        TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME))
    compiled = compiler.compile(sources)

    client = ETHClient(endpoint=server.endpoint)
    client.update_contracts(compiled)

    with client.account(client.address(0)):
        TestContract = client.deploy(
            CONTRACT_NAME, args=(), wrapper=MyTestContractWrapper)

    client.increase_blocktime_offset(10)
    client.mine_block()
    t = client.get_last_blocktime()
    client.increase_blocktime_offset(TIME_OFFSET)
    client.mine_block()
    blocktime = client.get_last_blocktime()
    time_diff = blocktime - t
    assert abs(time_diff - TIME_OFFSET) < TOLERANCE, (
        "time of new block is different from expected increase")
    soltime = TestContract.getTime()
    assert abs(soltime - blocktime) < TOLERANCE, (
        "Time from contract function is different from last block time")


def test_0003_pay(server: ETHTestServer, tool_solc):
    CONTRACT_NAME = "TestContract"

    sources = ContractSourceList()
    compiler = Compiler(executable=tool_solc.get("solc"))
    sources.add_string(
        "test",
        TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME))
    compiled = compiler.compile(sources)

    client = ETHClient(endpoint=server.endpoint)
    client.update_contracts(compiled)
    with client.account(client.address(0)):
        TestContract = client.deploy(
            CONTRACT_NAME, args=(), wrapper=MyTestContractWrapper)
        value = TestContract.pay(100, 110)
    assert value == 110


class MyTestContractWrapper(ContractBase):
    def getTime(self) -> int:
        return self.functions.getTime().call()

    def pay(self, value: int, valueSent: int):
        self.transact_sync("pay", value, value=valueSent)
        return self.functions.lastValue().call()


TEST_CONTRACT = """\
pragma solidity ^{solidity_version};
contract {contract_name} {{
    uint256 public lastValue;
    constructor() public {{
        lastValue = 0;
    }}
    function getTime() public view returns (uint256) {{
        return block.timestamp;
    }}
    function pay(uint256 _value) public payable {{
        require(msg.value >= _value);
        lastValue = msg.value;
    }}
}}
"""
