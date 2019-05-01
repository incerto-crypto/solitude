# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import pytest
import subprocess
import re
import sys
import yaml
import unittest.mock
from conftest import tmpdir, TmpTestDir, WorkingDir, SOLIDITY_VERSION  # noqa

pytestmark = [pytest.mark.base, pytest.mark.commandline]


def prepend_pragma_solidity(source, version):
    return ("pragma solidity ^%s;\n" % version) + source


def run_solitude(args=[]):
    import solitude._commandline.main
    with unittest.mock.patch("sys.argv", ["solitude"] + args):
        solitude._commandline.main.main()


def run_pytest(args=[]):
    import pytest
    with unittest.mock.patch("sys.argv", ["pytest"] + args):
        pytest.main()


@pytest.mark.require_local_tools
def test_0001_e01_cat_shelter(tooldir, tmpdir):
    tmp = TmpTestDir(tmpdir)
    tmp_testfile = tmp.create("tests/test_example.py", TEST_SCRIPT)
    tmp_contract = tmp.create(
        "src/CatShelter.sol",
        prepend_pragma_solidity(TEST_CONTRACT, SOLIDITY_VERSION))
    tmp.makedirs("obj")
    tmp.create("solitude.yaml", yaml.dump({
        "Tools.Directory": tooldir,
        "Project.SourceDir": "./src",
        "Project.ObjectDir": "./obj"
    }))
    with WorkingDir(tmp.path):
        run_solitude(["compile"])
        run_pytest(["tests"])


TEST_CONTRACT = """\
contract CatShelter
{
    address[16] public adopters;

    constructor() public {}

    function adopt(uint256 catId) public
    {
        require(catId < adopters.length);
        require(
            adopters[catId] == address(0),
            "Cat has already been adopted");
        adopters[catId] = msg.sender;
    }

    function getAdopters() public view returns (address[16] memory)
    {
        return adopters;
    }
}
"""

TEST_SCRIPT = """\
import pytest
from solitude.testing import sol, TransactionError


@pytest.fixture(scope="function")
def shelter(sol):
    # print(sol.client.compiled.contracts)
    # deploy and return contract instance
    with sol.account(0):
        return sol.deploy("CatShelter", args=())


def test_001_adopt_cat(sol, shelter):
    # adopt a cat and check you are its adopter
    CAT_ID = 3
    with sol.account(0):
        shelter.transact_sync("adopt", CAT_ID)

    assert sol.address(0) == shelter.call("adopters", 3)


def test_002_adopt_wrong_id(sol, shelter):
    # adopt a cat which does not exist and expect an error
    CAT_ID = 60
    with sol.account(0):
        with pytest.raises(TransactionError):
            # this transaction should fail
            shelter.transact_sync("adopt", CAT_ID)


def test_003_get_adopters_list(sol, shelter):
    CAT_ID = 3
    with sol.account(0):
        shelter.transact_sync("adopt", CAT_ID)
    adopters = shelter.call("getAdopters")
    assert adopters[CAT_ID] == sol.address(0)
"""
