# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import re
import subprocess
from solitude.tools import Solc, GanacheCli, Solium
from conftest import (  # noqa
    tooldir, SOLIDITY_VERSION, GANACHE_VERSION, SOLIUM_VERSION)


def assertOutputContainsVersion(output, version, index=0):
    lines = [
        line for line in output.decode().split('\n') if len(line)]
    assert(re.match(
        r"^[^0-9\.]*" + re.escape(version) + r"([^0-9\.].*$|$)",
        lines[index]))


def test_0001_install_compiler(tooldir):
    solc = Solc(tooldir, version=SOLIDITY_VERSION)
    solc.add()
    output = subprocess.check_output(
        [solc.get("solc"), "--version"])
    assertOutputContainsVersion(output, SOLIDITY_VERSION, index=-1)


def test_0002_install_ganache(tooldir):
    ganache = GanacheCli(tooldir, version=GANACHE_VERSION)
    ganache.add()
    output = subprocess.check_output(
        [ganache.get("ganache-cli"), "--version"])
    assertOutputContainsVersion(output, GANACHE_VERSION, index=-1)


def test_0003_install_solium(tooldir):
    solium = Solium(tooldir, version=SOLIUM_VERSION)
    solium.add()
    output = subprocess.check_output(
        [solium.get("solium"), "--version"])
    assertOutputContainsVersion(output, SOLIUM_VERSION, index=-1)
