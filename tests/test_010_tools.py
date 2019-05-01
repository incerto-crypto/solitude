# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import pytest
import re
import subprocess
from solitude.tools import Solc, GanacheCli, EthLint
from conftest import (  # noqa
    tooldir, SOLIDITY_VERSION, GANACHE_VERSION, ETHLINT_VERSION)

pytestmark = [pytest.mark.base, pytest.mark.tools]


def assertOutputContainsVersion(output, version, index=0):
    lines = [
        line for line in output.decode().split('\n') if len(line)]
    assert(re.match(
        r"^[^0-9\.]*" + re.escape(version) + r"([^0-9\.].*$|$)",
        lines[index]))


def test_0001_install_compiler(tooldir):
    solc = Solc(tooldir, version=SOLIDITY_VERSION)
    if not solc.have():
        solc.add()
    output = subprocess.check_output(
        [solc.get("solc"), "--version"])
    assertOutputContainsVersion(output, SOLIDITY_VERSION, index=-1)


def test_0002_install_ganache(tooldir):
    ganache = GanacheCli(tooldir, version=GANACHE_VERSION)
    if not ganache.have():
        ganache.add()
    output = subprocess.check_output(
        [ganache.get("ganache-cli"), "--version"])
    assertOutputContainsVersion(output, GANACHE_VERSION, index=-1)


def test_0003_install_ethlint(tooldir):
    ethlint = EthLint(tooldir, version=ETHLINT_VERSION)
    if not ethlint.have():
        ethlint.add()
    output = subprocess.check_output(
        [ethlint.get("solium"), "--version"])
    assertOutputContainsVersion(output, ETHLINT_VERSION, index=-1)
