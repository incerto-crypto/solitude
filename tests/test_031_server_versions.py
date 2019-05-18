import datetime
import pytest
from solitude.common import ContractSourceList
from solitude.compiler import Compiler
from solitude.server import ETHTestServer, kill_all_servers
from solitude.client import ETHClient, ContractBase
from solitude.tools import GanacheCli
from conftest import (  # noqa
    tooldir, tool_solc, SOLIDITY_VERSION, GANACHE_ALL_VERSIONS)

pytestmark = [pytest.mark.versions, pytest.mark.server]


# test for each ganache version
@pytest.fixture(scope="module", params=GANACHE_ALL_VERSIONS)
def tool_ganache(request, tooldir):
    tool = GanacheCli(tooldir=tooldir, version=request.param)
    if not tool.have():
        tool.add()
    yield tool


@pytest.fixture(scope="function")
def server(tool_ganache):
    server = ETHTestServer(
        port=8545, executable=tool_ganache.get("ganache-cli"))
    server.start()
    yield server
    server.stop()
    kill_all_servers()


@pytest.mark.require_local_tools
def test_0001_pay(server: ETHTestServer, tool_solc):
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
