# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
import pytest
from solitude.tools import Solc
from solitude.common import ContractSourceList
from solitude.compiler import Compiler
from solitude.errors import CompilerError
from conftest import tooldir, SOLIDITY_ALL_VERSIONS  # noqa
from distutils.version import StrictVersion


# test for each solc version
@pytest.fixture(scope="module", params=SOLIDITY_ALL_VERSIONS)
def tool_solc(request, tooldir):
    tool = Solc(tooldir=tooldir, version=request.param)
    if not tool.have():
        tool.add()
    yield tool


@pytest.mark.internet
def test_0001_compile_string(tool_solc):
    sources = ContractSourceList()
    compiler = Compiler(executable=tool_solc.get("solc"))
    CONTRACT_NAME = "TestContractFromString"
    SOURCE_NAME = "test"

    constructor = "constructor"
    if StrictVersion(tool_solc.version) < StrictVersion("0.4.22"):
        constructor = "function " + CONTRACT_NAME

    sources.add_string(
        SOURCE_NAME,
        TEST_CONTRACT.format(
            solidity_version=tool_solc.version,
            contract_name=CONTRACT_NAME,
            constructor=constructor,
            zero_value_constexpr="0",
            zero_value_literal="0",
            string_literal='"a string"'))
    compiled = compiler.compile(sources)
    assert(compiled.select(CONTRACT_NAME)["_solitude"]["contractName"] == CONTRACT_NAME)


TEST_CONTRACT = """\
pragma solidity ^{solidity_version};
contract {contract_name} {{
    uint256 public lastValue;
    string public name;
    {constructor}() public {{
        lastValue = ({zero_value_literal});
        name = {string_literal};
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
