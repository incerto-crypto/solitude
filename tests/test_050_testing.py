# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import pytest
from solitude.common import ContractSourceList
from solitude.server import ETHTestServer, kill_all_servers  # noqa
from solitude.client import ETHClient, ContractBase  # noqa
from solitude.testing import SOL
from conftest import sol, SOLIDITY_VERSION, GANACHE_VERSION, ATTILA, GEORGE  # noqa

pytestmark = [pytest.mark.base, pytest.mark.testing]


@pytest.fixture(scope="module", autouse=True)
def contracts(sol: SOL):
    sources = ContractSourceList()
    sources.add_string(
        "test",
        TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME))
    sol.client.update_contracts(sol.compiler.compile(sources))


def test_0001_pay(sol: SOL):
    with sol.account(ATTILA):
        TestContract = sol.deploy(
            CONTRACT_NAME, args=(), wrapper=ITestContract)
        value = TestContract.pay(100, 110)
        assert(value == 110)

        t = TestContract.pay_reset_gettime(100, 110)
        assert(t > 0)


class ITestContract(ContractBase):
    def add(self, a, b):
        return self.functions.add(a, b).call()

    def getTime(self) -> int:
        t = self.functions.getTime().call()
        return self.add(t, 0)

    def pay(self, value: int, valueSent: int):
        self.transact_sync("pay", value, value=valueSent)
        return self.functions.lastValue().call()

    def reset(self):
        self.transact_sync("reset")

    def pay_reset_gettime(self, value: int, valueSent: int):
        self.pay(value, valueSent)
        self.reset()
        return self.getTime()


CONTRACT_NAME = "TestContract"
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
    function reset() public {{
        lastValue = 0;
    }}
    function add(uint256 a, uint256 b) public pure returns (uint256) {{
        return a + b;
    }}
}}
"""
