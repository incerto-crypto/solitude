# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
import pytest
from solitude.common import ContractSourceList
from solitude.compiler import Compiler
from solitude.errors import CompilerError
from conftest import tooldir, tmpdir, tool_solc, SOLIDITY_VERSION  # noqa

pytestmark = [pytest.mark.base, pytest.mark.compiler]


def find_line(text, needle):
    for i, line in enumerate(text.split("\n")):
        if needle in line:
            return i
    return -1


def test_0001_compile_string(tool_solc):
    sources = ContractSourceList()
    compiler = Compiler(executable=tool_solc.get("solc"))
    CONTRACT_NAME = "TestContractFromString"
    UNIT_NAME = "test"
    sources.add_string(
        UNIT_NAME,
        TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME,
            zero_value_constexpr="0",
            zero_value_literal="0",
            string_literal='"a string"'))
    compiled = compiler.compile(sources)
    assert(compiled.select(CONTRACT_NAME)["_solitude"]["contractName"] == CONTRACT_NAME)


def test_0002_compile_file(tooldir, tmpdir, tool_solc):
    sources = ContractSourceList()
    compiler = Compiler(executable=tool_solc.get("solc"))
    CONTRACT_NAME = "TestContractFromFile0002"
    contract_file = os.path.join(tmpdir, CONTRACT_NAME + ".sol")
    with open(contract_file, 'w') as fp:
        fp.write(TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME,
            zero_value_constexpr="0",
            zero_value_literal="0",
            string_literal='"a string"'))
    sources.add_file(contract_file)
    compiled = compiler.compile(sources)
    assert(compiled.select(CONTRACT_NAME)["_solitude"]["contractName"] == CONTRACT_NAME)


def test_0003_compile_file_and_string(tooldir, tmpdir, tool_solc):
    sources = ContractSourceList()
    compiler = Compiler(executable=tool_solc.get("solc"))
    CONTRACT_NAME_STRING = "TestContractFromString"
    CONTRACT_NAME_FILE = "TestContractFromFile0003"
    SOURCE_NAME = "test"
    contract_file = os.path.join(tmpdir, CONTRACT_NAME_FILE + ".sol")
    with open(contract_file, 'w') as fp:
        fp.write(TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME_FILE,
            zero_value_constexpr="0",
            zero_value_literal="0",
            string_literal='"a string"'))
    sources.add_string(
        SOURCE_NAME,
        TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME_STRING,
            zero_value_constexpr="0",
            zero_value_literal="0",
            string_literal='"a string"'))
    sources.add_file(contract_file)
    compiled = compiler.compile(sources)
    assert (
        compiled.select(CONTRACT_NAME_STRING)["_solitude"]["contractName"] ==
        CONTRACT_NAME_STRING)
    assert(
        compiled.select(CONTRACT_NAME_FILE)["_solitude"]["contractName"] ==
        CONTRACT_NAME_FILE)


def test_0004_compile_duplicate_name(tooldir, tmpdir, tool_solc):
    sources = ContractSourceList()
    compiler = Compiler(executable=tool_solc.get("solc"))
    CONTRACT_NAME = "TestContract"
    UNIT_NAME = "test"
    contract_file = os.path.join(tmpdir, CONTRACT_NAME + ".sol")
    with open(contract_file, 'w') as fp:
        fp.write(TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME,
            zero_value_constexpr="0",
            zero_value_literal="0",
            string_literal='"a string"'))
    sources.add_string(
        UNIT_NAME,
        TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME,
            zero_value_constexpr="0",
            zero_value_literal="0",
            string_literal='"a string"'))
    sources.add_file(contract_file)
    compiled = compiler.compile(sources)
    assert (
        compiled.select(UNIT_NAME + ":" + CONTRACT_NAME)["_solitude"]["contractName"] ==
        CONTRACT_NAME)
    suffix = contract_file.split("/")[-1]
    assert (
        compiled.select(suffix + ":" + CONTRACT_NAME)["_solitude"]["contractName"] ==
        CONTRACT_NAME)


def test_0005_compile_syntax_error(tool_solc):
    sources = ContractSourceList()
    compiler = Compiler(executable=tool_solc.get("solc"))
    CONTRACT_NAME = "TestContract"
    SOURCE_NAME = "test"
    sources.add_string(
        SOURCE_NAME,
        TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION,
            contract_name=CONTRACT_NAME,
            zero_value_constexpr="0",
            zero_value_literal="0",
            string_literal="it's not a string"))
    try:
        compiler.compile(sources)
    except CompilerError as err:
        assert len(err.messages) >= 1
        m = err.messages[0]
        assert m.type == "error"
        assert m.unitname == SOURCE_NAME
        assert m.line == 1 + find_line(TEST_CONTRACT, "{string_literal}")
    else:
        pytest.fail("Syntax error not caught by compiler")


TEST_CONTRACT = """\
pragma solidity ^{solidity_version};
contract {contract_name} {{
    uint256 public lastValue;
    string public name;
    constructor() public {{
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
