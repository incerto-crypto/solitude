import datetime
import pytest
from solitude.compiler import CompiledSources, Compiler
from solitude.server import RPCTestServer, kill_all_servers
from solitude.client import ETHClient, ContractWrapper, view, payable
from solitude.tools import GanacheCli
from conftest import (  # noqa
    tooldir, tool_solc, SOLIDITY_VERSION)


VERSIONS = [
    "6.1.5", "6.1.6", "6.1.7", "6.1.8",
    "6.2.0", "6.2.1", "6.2.2", "6.2.3", "6.2.4", "6.2.5",
    "6.3.0",
    "6.4.0", "6.4.1", "6.4.2"
]


# test for each ganache version
@pytest.fixture(scope="module", params=VERSIONS)
def tool_ganache(request, tooldir):
    tool = GanacheCli(tooldir=tooldir, version=request.param)
    tool.add()
    yield tool


@pytest.fixture(scope="function")
def server(tool_ganache):
    server = RPCTestServer(
        port=8545, executable=tool_ganache.get("ganache-cli"))
    server.start()
    yield server
    server.stop()
    kill_all_servers()


@pytest.mark.internet
def test_0001_pay(server: RPCTestServer, tool_solc):
    CONTRACT_NAME = "TestContract"

    compiler = Compiler(executable=tool_solc.get("solc"))
    compiler.add_string(
        "test",
        TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME))
    compiled = compiler.compile()

    client = ETHClient(
        endpoint=server.endpoint,
        compiled=compiled)
    with client.account(0):
        TestContract = client.deploy(
            CONTRACT_NAME, args=(), wrapper=MyTestContractWrapper)
        value = TestContract.pay(100, 110)
    assert value == 110


class MyTestContractWrapper(ContractWrapper):
    @view
    def getTime(self) -> int:
        return self.functions.getTime().call()

    @payable
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
