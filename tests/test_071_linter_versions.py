# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import pytest
import re
from solitude.tools import EthLint
from solitude.linter import Linter
from solitude.common import ContractSourceList
from conftest import SOLIDITY_VERSION, ETHLINT_ALL_VERSIONS


pytestmark = [pytest.mark.versions, pytest.mark.linter]


# test for each ethlint version
@pytest.fixture(scope="module", params=ETHLINT_ALL_VERSIONS)
def tool_ethlint(request, tooldir):
    tool = EthLint(tooldir=tooldir, version=request.param)
    if not tool.have():
        tool.add()
    yield tool


@pytest.mark.require_local_tools
def test_0001_lint(tool_ethlint):
    linter = Linter(
        tool_ethlint.get("solium"),
        plugins=["security"],
        rules={
            "quotes": ["error", "double"],
            "indentation": ["error", 4]
        },
        parallelism=1)
    sources = ContractSourceList()
    sources.add_string(
        "TestContract",
        TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION))
    errors = list(linter.lint(sources))
    assert len(errors) == 1
    err = errors[0]
    assert err.type == "error"
    assert err.unitname.startswith("TestContract")
    assert err.line == 5
    assert err.column == 2
    assert "[indentation]" in err.message


TEST_CONTRACT = """\
pragma solidity ^{solidity_version};
contract Fibonacci {{
    uint public result;

  constructor() public {{  // this is line 5. do not move or change this line
        result = 0;
    }}

    function fib_r(uint n) internal pure returns (uint) {{
        if (n < 2) {{
            return n;
        }}
        return fib_r(n - 1) + fib_r(n - 2);
    }}

    function fib(uint n) public {{
        result = fib_r(n);
    }}
}}
"""
