# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
import hashlib
from typing import List, Tuple, Dict, Optional  # noqa
from solitude._internal import type_assert, value_assert, RaiseForParam


def make_unique_built_contract_filename(unitname: str, contractname: str):
    h = hashlib.sha256()
    h.update(unitname.encode("utf-8"))
    h.update(b"\0")
    h.update(contractname.encode("utf-8"))
    return "build_" + contractname + "_" + h.hexdigest() + ".json"


def file_is_built_contract(filename):
    return filename.startswith("build_") and filename.endswith(".json")


class ContractObjectList:
    def __init__(self):
        self._contracts = {}  # type: Dict[Tuple[str, str], dict]
        self._name_to_units = {}

    def add_contract(self, unitname: str, contractname: str, contract: dict):
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

    def add_directory(self, path: str):
        for filename in os.listdir(path):
            if file_is_built_contract(filename):
                with open(os.path.join(path, filename)) as fp:
                    contract = json.load(fp)
                self.add_contract(
                    contract["_solitude"]["unitName"],
                    contract["_solitude"]["contractName"],
                    contract)

    def save_directory(self, path: str):
        os.makedirs(path, exist_ok=True)
        for (unitname, contractname), contract in self._contracts.items():
            filename = make_unique_built_contract_filename(unitname, contractname)
            with open(os.path.join(path, filename), "w") as fp:
                json.dump(contract, fp, indent=2)

    def update(self, other: "ContractObjectList"):
        with RaiseForParam("other"):
            type_assert(other, ContractObjectList)
        for (unitname, contractname), contract in other._contracts.items():
            self.add_contract(unitname, contractname, contract)

    def find(self, suffix: Optional[str], contractname: str) -> List[Tuple[str, str]]:
        with RaiseForParam("suffix"):
            type_assert(suffix, (str, type(None)))
        with RaiseForParam("contractname"):
            type_assert(contractname, str)
        out = []
        units = self._name_to_units.get(contractname)
        for unit in units:
            if suffix is None or unit.endswith(suffix):
                out.append((unit, contractname))
        return out

    def select(self, selector: str) -> dict:
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
    def contracts(self):
        return self._contracts.copy()
