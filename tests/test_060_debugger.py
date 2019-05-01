# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import pytest
import re
from collections import namedtuple
from solitude.common import ContractSourceList
from solitude.server import RPCTestServer, kill_all_servers  # noqa
from solitude.client import ETHClient, ContractBase  # noqa
from solitude.testing import SOL

from solitude.debugger import EvmTrace, InteractiveDebuggerOI
from solitude._commandline.cmd_debug import InteractiveDebuggerCLI
from conftest import sol, SOLIDITY_VERSION, GANACHE_VERSION, ATTILA, GEORGE  # noqa
from io import StringIO

pytestmark = [pytest.mark.base, pytest.mark.debugger]


def onecmd(debugger, buf, line):
    pos = buf.tell()
    debugger.onecmd(line)
    buf.seek(pos)
    out = buf.read()
    return out


@pytest.fixture(scope="module", autouse=True)
def contracts(sol: SOL):
    sources = ContractSourceList()
    sources.add_string(
        "TestContract",
        TEST_CONTRACT.format(
            solidity_version=SOLIDITY_VERSION))
    sol.client.update_contracts(sol.compiler.compile(sources))


FibResult = namedtuple("FibResult", ["value", "max_depth"])


def reference_fib(n, depth=1):
    if n < 2:
        return FibResult(value=n, max_depth=depth)
    a = reference_fib(n - 1, depth + 1)
    b = reference_fib(n - 2, depth + 1)
    return FibResult(value=a.value + b.value, max_depth=max(a.max_depth, b.max_depth))


def test_0001_fib(sol: SOL):

    with sol.account(ATTILA):
        Fibonacci = sol.deploy(
            "Fibonacci", args=(), wrapper=IFibonacci)

    debugger = EvmTrace(sol.client.rpc, sol.client.compiled)

    for value in (7, 10):
        with sol.account(ATTILA):
            tx = Fibonacci.fib(value)
        reference = reference_fib(value)
        result = Fibonacci.result
        assert(result == reference.value)
        stack_depth = 0
        max_stack_depth = 0
        for step, callstack_event in debugger.trace_iter(tx.txhash):
            if callstack_event.event == "push":
                stack_depth += 1
            elif callstack_event.event == "pop":
                stack_depth -= 1
            max_stack_depth = max(max_stack_depth, stack_depth)
        assert(max_stack_depth == 1 + reference.max_depth)


def test_0002_interactive(sol: SOL):
    with sol.account(ATTILA):
        Fibonacci = sol.deploy(
            "Fibonacci", args=(), wrapper=IFibonacci)

    with sol.account(ATTILA):
        tx = Fibonacci.fib(7)

    LINE10_BP = "TestContract:10"
    LINE10_CODE = "if (n < 2)"
    var_template = r"uint256\s+{name}\s*=\s*{val}(\s|;|$|\r|\n)"
    fn_template = r"{name}\(\s*uint256\s+{argname}\s*=\s*{argval}\s*\)"

    buf = StringIO()
    debugger = InteractiveDebuggerCLI(InteractiveDebuggerOI(tx.txhash, sol.client), stdout=buf)

    # debugger.oui.dbg._dbg._contracts

    out = onecmd(debugger, buf, "break %s" % LINE10_BP)
    # [I] Breakpoint Added: 'TestContract:10'
    assert LINE10_BP in out

    out = onecmd(debugger, buf, "continue")
    # [I] Breakpoint: TestContract:10:16
    # (code...)
    assert LINE10_BP in out
    assert LINE10_CODE in out

    out = onecmd(debugger, buf, "info locals")
    # [I] Variable: uint256 n = 7
    assert re.search(var_template.format(name="n", val="7"), out) is not None

    out = onecmd(debugger, buf, "print n")
    # [I] Variable: uint256 n = 7
    assert re.search(var_template.format(name="n", val="7"), out) is not None

    out = onecmd(debugger, buf, "backtrace")
    # [I] #0 function fib_r(uint256 n = 7)
    # [I] #1 function fib(uint256 n = 7)
    assert re.search(fn_template.format(name="fib_r", argname="n", argval="7"), out) is not None
    assert re.search(fn_template.format(name="fib", argname="n", argval="7"), out) is not None

    out = onecmd(debugger, buf, "continue")
    # [I] Breakpoint: TestContract:10:16
    # (code...)
    assert LINE10_BP in out
    assert LINE10_CODE in out

    out = onecmd(debugger, buf, "backtrace")
    # [I] #0 function fib_r(uint256 n = 5)
    # [I] #1 function fib_r(uint256 n = 7)
    # [I] #2 function fib(uint256 n = 7)
    assert re.search(fn_template.format(name="fib_r", argname="n", argval="5"), out) is not None
    assert re.search(fn_template.format(name="fib_r", argname="n", argval="7"), out) is not None
    assert re.search(fn_template.format(name="fib", argname="n", argval="7"), out) is not None

    out = onecmd(debugger, buf, "print n")
    # [I] Variable: uint256 n = 5
    assert re.search(var_template.format(name="n", val="5"), out) is not None

    out = onecmd(debugger, buf, "frame 1")
    # [I] Selected frame: #1
    # (code...)
    assert LINE10_CODE in out

    out = onecmd(debugger, buf, "print n")
    # [I] Variable: uint256 n = 7
    assert re.search(var_template.format(name="n", val="7"), out) is not None

    out = onecmd(debugger, buf, "info breakpoints")
    # [I] Breakpoint: TestContract:10
    assert LINE10_BP in out

    out = onecmd(debugger, buf, "delete %s" % LINE10_BP)
    # [I] Breakpoint Deleted: 'TestContract:10'

    out = onecmd(debugger, buf, "list")
    # (code...)
    assert LINE10_CODE in out

    out = onecmd(debugger, buf, "stepi")
    # (code...)
    assert LINE10_CODE in out

    out = onecmd(debugger, buf, "step")
    # (code...)
    assert LINE10_CODE in out

    out = onecmd(debugger, buf, "next")
    # (code...)
    assert LINE10_CODE in out

    out = onecmd(debugger, buf, "frame 0")
    # [I] Selected frame: #0
    # (code...)
    assert LINE10_CODE in out

    out = onecmd(debugger, buf, "finish")
    # (code...)
    # [I] Return: uint256 ? = 5
    fib5 = reference_fib(5)
    assert re.search(var_template.format(name=r"[^\s]+", val=fib5.value), out) is not None

    out = onecmd(debugger, buf, "info args")
    # [I] Call: function fib_r(uint256 n = 5)
    assert re.search(fn_template.format(name="fib_r", argname="n", argval="5"), out) is not None

    out = onecmd(debugger, buf, "finish")
    # (code...)
    # [I] Return: uint256 ? = 13
    fib7 = reference_fib(7)
    assert re.search(var_template.format(name=r"[^\s]+", val=fib7.value), out) is not None

    out = onecmd(debugger, buf, "info args")
    # [I] Call: function fib_r(uint256 n = 7)
    assert re.search(fn_template.format(name="fib_r", argname="n", argval="7"), out) is not None

    out = onecmd(debugger, buf, "quit")
    # (no output to check)
    del out


class IFibonacci(ContractBase):
    def fib(self, n: int):
        return self.transact_sync("fib", n)

    @property
    def result(self):
        return self.functions.result().call()


TEST_CONTRACT = """\
pragma solidity ^{solidity_version};
contract Fibonacci {{
    uint public result;

    constructor() public {{
        result = 0;
    }}

    function fib_r(uint n) internal pure returns (uint) {{
        if (n < 2) {{  // this is line 10. do not move or change this line
            return n;
        }}
        return fib_r(n - 1) + fib_r(n - 2);
    }}

    function fib(uint n) public {{
        result = fib_r(n);
    }}
}}
"""
