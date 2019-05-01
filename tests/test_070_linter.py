# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import pytest
import re
from solitude.linter import Linter
from solitude.common import ContractSourceList
from conftest import tool_ethlint, SOLIDITY_VERSION  # noqa

pytestmark = [pytest.mark.base, pytest.mark.linter]


def test_0001_lint(tool_ethlint):
    COUNT = 20
    linter = Linter(
        tool_ethlint.get("solium"),
        plugins=["security"],
        rules={
            "quotes": ["error", "double"],
            "indentation": ["error", 4]
        },
        parallelism=4)
    sources = ContractSourceList()
    for i in range(COUNT):
        sources.add_string(
            "TestContract%03d" % i,
            TEST_CONTRACT.format(
                solidity_version=SOLIDITY_VERSION))
    err_count = 0
    for err in linter.lint(sources):
        assert err.type == "error"
        assert err.unitname.startswith("TestContract")
        assert err.line == 5
        assert err.column == 2
        assert "[indentation]" in err.message
        err_count += 1
    assert err_count == COUNT


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
