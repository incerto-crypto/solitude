# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
import hashlib
import json
from typing import List, Tuple, Dict, Optional  # noqa
from solitude._internal import (
    type_assert, value_assert, RaiseForParam, EnumType)
from solitude.common.contract_util import (
    convert_contract_truffle_to_solitude)


class BuildDirectoryType(EnumType):
    SOLITUDE = "solitude"
    TRUFFLE = "truffle"


def make_unique_built_contract_filename(unitname: str, contractname: str):
    """Create a unique filename to store the contract identified by (unitname, contractname)

    This function shrinks the 'unitname', which may contain a path, keeping the
    uniqueness of the (unitname, contractname) tuple.

    :param unitname: source unit containing the contract
    :param contractname: name of the contract
    :return: unique filename
    """
    h = hashlib.md5()
    h.update(unitname.encode("utf-8"))
    h.update(b"\0")
    h.update(contractname.encode("utf-8"))
    return "build_" + contractname + "_" + h.hexdigest() + ".json"


def file_is_built_contract(filename: str):
    """Verify from the filename whether a file may contain compiled contract
    information.

    :param filename: name of the file (excluding directory)
    :return: True if the filename is valid for a solitude compiled contract
        output filename.
    """
    return filename.startswith("build_") and filename.endswith(".json")


class ContractObjectList:
    """A collection of compiled contracts
    """

    _EXCLUDE_TRUFFLE_CONTRACTS = ["Migrations"]

    def __init__(self):
        """Create an empty collection of compiled contracts
        """
        self._contracts = {}  # type: Dict[Tuple[str, str], dict]
        self._name_to_units = {}

    def add_contract(self, unitname: str, contractname: str, contract: dict):
        """Add a contract, uniquely identified by (unitname, contractname).

        :param unitname: source unit containing the contract
        :param contractname: name of the contract
        :param contract: contract data dictionary, as produced by the compiler module
        """
        key = (unitname, contractname)
        if key in self._contracts:
            raise CompilerError([FileMessage(
                type="duplicate",
                unitname=unitname + ":" + contractname,
                line=None,
                column=None,
                message="Duplicate contract identifier found")])
        self._contracts[key] = contract
        try:
            self._name_to_units[contractname].append(unitname)
        except KeyError:
            self._name_to_units[contractname] = [unitname]

    def add_directory(self, path: str, buildtype=BuildDirectoryType.SOLITUDE) -> None:
        """Add all contracts from a directory.

        :param path: path of the directory containing the contracts data.
        :param buildtype: format of the build directory, one of the values of BuildDirectoryType.
            defaults to SOLITUDE.
        """
        with RaiseForParam("buildtype"):
            BuildDirectoryType.value_assert(buildtype)

        if buildtype == BuildDirectoryType.SOLITUDE:
            self._add_solitude_directory(path)
        elif buildtype == BuildDirectoryType.TRUFFLE:
            self._add_truffle_directory(path)
        else:
            assert False

    def _add_solitude_directory(self, path: str):
        for filename in os.listdir(path):
            if file_is_built_contract(filename):
                with open(os.path.join(path, filename)) as fp:
                    contract = json.load(fp)
                self.add_contract(
                    contract["_solitude"]["unitName"],
                    contract["_solitude"]["contractName"],
                    contract)

    def _add_truffle_directory(self, path: str):
        source_unit_index_map = {}
        # Since truffle does not store a mapping of the source index (as it appears in the source map)
        #   to the source file, we build this index at the end, from the source index found in the AST
        #   of each file.
        for filename in os.listdir(path):
            if filename.endswith(".json"):

                # Ignore the Migrations contract
                if filename[:-len(".json")] in ContractObjectList._EXCLUDE_TRUFFLE_CONTRACTS:
                    continue

                with open(os.path.join(path, filename)) as fp:
                    truffle_contract = json.load(fp)

                contract = convert_contract_truffle_to_solitude(
                    truffle_contract)
                source_unit_index = int(contract["_solitude"]["ast"]["src"].split(":")[2])
                source_unit_index_map[source_unit_index] = contract["_solitude"]["unitName"]
                self.add_contract(
                    contract["_solitude"]["unitName"],
                    contract["_solitude"]["contractName"],
                    contract)
        source_list = [None] * (1 + max(source_unit_index_map.keys()))
        for index, unitname in source_unit_index_map.items():
            source_list[index] = unitname
        for key, contract in self._contracts.items():
            contract["_solitude"]["sourceList"] = source_list

    def save_directory(self, path: str, buildtype=BuildDirectoryType.SOLITUDE) -> None:
        """Save all contracts to a directory.

        :param path: path of destination directory; the directory must exist.
        """
        with RaiseForParam("buildtype"):
            BuildDirectoryType.value_assert(buildtype)

        if buildtype == BuildDirectoryType.SOLITUDE:
            os.makedirs(path, exist_ok=True)
            for (unitname, contractname), contract in self._contracts.items():
                filename = make_unique_built_contract_filename(unitname, contractname)
                with open(os.path.join(path, filename), "w") as fp:
                    json.dump(contract, fp, indent=2)
        elif buildtype == BuildDirectoryType.TRUFFLE:
            raise NotImplementedError("Saving to truffle format is not implemented yet")
        else:
            assert False

    def update(self, other: "ContractObjectList") -> None:
        """Add all contracts from other ContractObjectList.

        :param other: other ContractObjectList with contracts to add
        """
        with RaiseForParam("other"):
            type_assert(other, ContractObjectList)
        for (unitname, contractname), contract in other._contracts.items():
            self.add_contract(unitname, contractname, contract)

    def find(self, suffix: Optional[str], contractname: str) -> List[Tuple[str, str]]:
        """Find contracts by unitname suffix and full contractname.

        Example: ("erc20/ERC20.sol", "ERC20") matches ("/home/user/contracts/erc20/ERC20.sol", "ERC20").

        :param suffix: suffix to match the contract source unit name, or None; if it is None, any
            unit name is matched.
        :param contractname: full name of the contract
        """
        with RaiseForParam("suffix"):
            type_assert(suffix, (str, type(None)))
        with RaiseForParam("contractname"):
            type_assert(contractname, str)
        out = []
        units = self._name_to_units.get(contractname, [])
        for unit in units:
            if suffix is None or unit.endswith(suffix):
                out.append((unit, contractname))
        return out

    def select(self, selector: str) -> dict:
        """Find a single contract matching the contract selector string.

        The selector string is a string in either of the following forms:

        - "{suffix}:{contractname}": source unit name suffix and contract name,
            separated by ':'. Example: "erc20/ERC20.sol:ERC20" matches contract
            named "ERC20" in source unit "/home/user/contracts/erc20/ERC20.sol".

        - "{contractname}": only the contract name. Example: "ERC20" matches
            contract named "ERC20".

        If the selector matches multiple contract, this function will raise an
        exception of type ValueError.

        :param selector: contract selector
        """
        with RaiseForParam("selector"):
            type_assert(selector, str)
            if selector.count(":") == 1:
                suffix, contractname = selector.split(":")
            else:
                suffix, contractname = None, selector
            value_assert(
                "/" not in contractname,
                "Invalid contract selector syntax. Either 'path/suffix:ContractName' or 'ContractName'")
            contracts = self.find(suffix, contractname)
            value_assert(
                len(contracts) != 0,
                "Contract not found")
            value_assert(
                len(contracts) == 1,
                "Contract selector matched multiple contracts")
            return self._contracts[contracts[0]]

    @property
    def contracts(self) -> Dict[Tuple[str, str], dict]:
        """All contracts, as a dictionary of (unitname, contractname) -> data
        """
        return self._contracts.copy()
