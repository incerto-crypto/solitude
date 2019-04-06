# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Optional, Dict
import subprocess
import re
import json
import datetime
import os
import sys
from solitude.errors import CompilerError
from solitude.common import FileMessage
from solitude._internal import (
    EnumType, RaiseForParam, isfile_assert, value_assert, type_assert)


UNDEFINED = "undefined"


class EvmVersion(EnumType):
    HOMESTEAD = "homestead"
    TANGERINE_WHISTLE = "tangerineWhistle"
    SPURIOUS_DRAGON = "spuriousDragon"
    BYZANTIUM = "byzantium"
    CONSTANTINOPLE = "constantinople"


class OutputSelection(EnumType):
    AST = "ast"
    ABI = "abi"
    DEVDOC = "devdoc"
    USERDOC = "userdoc"
    METADATA = "metadata"
    IR = "ir"
    ASSEMBLY = "evm.assembly"
    DEPLOY_OBJECT = "evm.bytecode.object"
    DEPLOY_OPCODES = "evm.bytecode.opcodes"
    DEPLOY_SOURCEMAP = "evm.bytecode.sourceMap"
    DEPLOY_LINKREFS = "evm.bytecode.linkReferences"
    RUNTIME_OBJECT = "evm.deployedBytecode.object"
    RUNTIME_OPCODES = "evm.deployedBytecode.opcodes"
    RUNTIME_SOURCEMAP = "evm.deployedBytecode.sourceMap"
    RUNTIME_LINKREFS = "evm.deployedBytecode.linkReferences"
    METHOD_IDENTIFIERS = "evm.methodIdentifiers"
    GAS_ESTIMATES = "evm.gasEstimates"

    _GLOBAL_OUTPUTS = set([
        "ast"])

    @staticmethod
    def is_global(value):
        return (value in OutputSelection._GLOBAL_OUTPUTS)


class SolcWrapper:
    Evm = EvmVersion
    Out = OutputSelection

    def __init__(
            self,
            executable="solc",
            outputs: List[str]=None,
            optimize: Optional[int]=None,
            evm_version: Optional[str]=None,
            warnings_as_errors: bool=False):

        with RaiseForParam("executable"):
            isfile_assert(executable)
            self._executable = executable

        with RaiseForParam("outputs"):
            if outputs is not None:
                for choice in outputs:
                    OutputSelection.value_assert(choice)
                self._outputs = outputs[:]
            else:
                self._outputs = _make_default_output_selection()

        with RaiseForParam("optimize"):
            type_assert(optimize, (int, type(None)))
            self._optimize = optimize

        with RaiseForParam("evm_version"):
            if evm_version is not None:
                EvmVersion.value_assert(evm_version)
            self._evm_version = evm_version

        self._warnings_as_errors = bool(warnings_as_errors)

    def compile(
            self,
            source_files: Optional[List[str]]=None,
            source_strings: Optional[Dict[str, str]]=None):

        cmd = [self._executable, "--standard-json"]
        data = _SolcStandardJsonInput()

        data.set_output_selection(self._outputs)
        if self._optimize is not None:
            data.set_optimizer(self._optimize)
        if self._evm_version is not None:
            data.set_evm_version(self._evm_version)

        # read source files and include them in the JSON
        unitname_to_path = {}
        with RaiseForParam("source_files"):
            if source_files is not None:
                type_assert(source_files, list)
                for path in source_files:
                    isfile_assert(path)
                    absolute_path = os.path.abspath(path)
                    unitname = data.add_source_from_file(absolute_path)
                    unitname_to_path[unitname] = absolute_path

        # include source strings in the JSON
        with RaiseForParam("source_strings"):
            if source_strings is not None:
                type_assert(source_strings, dict, ", (name: str -> code: str)")
                for unitname, contents in source_strings.items():
                    value_assert(
                        isinstance(unitname, str),
                        "Key must be a string containing a name")
                    value_assert(
                        not unitname.startswith("/"),
                        "Key cannot start with '/'")
                    value_assert(
                        isinstance(contents, str),
                        "Value must be a string containing the source code")
                    data.add_source(unitname, contents)

        # invoke solc
        solc_out = self.call_standard_json(data.value())
        timestamp = datetime.datetime.utcnow().isoformat()

        # collect errors and warnings
        errors = []
        warnings = []
        for error in solc_out.get("errors", []):
            severity = error.get("severity")
            if severity == "error" or self._warnings_as_errors:
                errors.append(error)
            else:
                warnings.append(error)

        # raise exception on error
        if errors:
            raise CompilerError([
                _convert_error(error) for error in errors])

        contracts = solc_out.get("contracts", {})
        sources = solc_out.get("sources", {})
        sourceid_to_unitname = [None] * len(sources)

        output = {}

        # gather AST and source id for each source
        unitname_to_ast = {}
        for unitname, unit in sources.items():
            unitname_to_ast[unitname] = unit.get("ast")
            sourceid_to_unitname[unit["id"]] = unitname

        # create output dictionary, (unitname, contractname) -> contract
        # including the full source content and AST
        for unitname, contracts_in_unit in contracts.items():
            for contractname, contract in contracts_in_unit.items():
                try:
                    source_path = unitname_to_path[unitname]
                except KeyError:
                    source_path = unitname
                out_contract_data = {}
                out_contract_data["abi"] = contract.get("abi")
                out_contract_data["bin"] = (
                    contract.get("evm", {}).get("bytecode", {}).get("object"))
                out_contract_data["srcmap"] = (
                    contract.get("evm", {}).get("bytecode", {}).get("sourceMap"))
                out_contract_data["bin-runtime"] = (
                    contract.get("evm", {}).get("deployedBytecode", {}).get("object"))
                out_contract_data["srcmap-runtime"] = (
                    contract.get("evm", {}).get("deployedBytecode", {}).get("sourceMap"))
                out_contract_data["_solitude"] = {
                    "ast": unitname_to_ast[unitname],
                    "contractName": contractname,
                    "sourceList": sourceid_to_unitname,
                    "sourcePath": source_path,
                    "source": data.get_source(unitname),
                    "timestamp": timestamp
                }
                output[(unitname, contractname)] = out_contract_data
        return output

    def call_standard_json(self, data: dict):
        cmd = [self._executable, "--standard-json"]

        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        stdin_data = json.dumps(data, indent=2).encode("utf-8")
        out, err = p.communicate(stdin_data)
        out_dict = json.loads(out.decode("utf-8"))
        return out_dict


def _convert_error(error: dict) -> FileMessage:
    line, column = 1, 1
    message = error.get("message", UNDEFINED)
    m = re.match(
        r"^(.+):([0-9]+):([0-9]+):\s*([^:\s]+)\s*:",
        error.get("formattedMessage", UNDEFINED))
    if m is not None:
        line = int(m.group(2))
        column = int(m.group(3))
    return FileMessage(
        type=error.get("severity", ""),
        unitname=error.get("sourceLocation", {}).get("file", ""),
        line=line,
        column=column,
        message=message)


def _make_default_output_selection() -> List[str]:
    return [
        OutputSelection.ABI,
        OutputSelection.DEPLOY_OBJECT]


def _make_output_selection_dict(outputs: List[str]) -> dict:
    return {
        "*": {
            "*": [val for val in outputs if not OutputSelection.is_global(val)],
            "": [val for val in outputs if OutputSelection.is_global(val)]
        }
    }


def _make_unitname(path: str):
    # solc does not accept r"\" in source unit names
    # C:\path\to\file.sol -> /C/path/to/file.sol
    if sys.platform == "win32":
        path = path.replace("\\", "/")
        if path[1] == ":":
            path = "/" + path[0] + path[2:]
        return path
    return path


class _SolcStandardJsonInput:
    def __init__(self):
        self._language = "Solidity"
        self._settings = {
            "metadata": {
                "useLiteralContent": True,
            },
            "outputSelection": {
            }
        }
        self._sources = {}

    def set_output_selection(self, outputs: List[str]):
        self._settings["outputSelection"] = _make_output_selection_dict(outputs)

    def set_optimizer(self, optimize: Optional[int]):
        try:
            del self._settings["optimizer"]
        except KeyError:
            pass
        self._settings["optimizer"] = {
            "enabled": True,
            "runs": optimize
        }

    def set_evm_version(self, evm_version):
        try:
            del self._settings["evmVersion"]
        except KeyError:
            pass
        self._settings["evmVersion"] = evm_version

    def add_source_from_file(self, path) -> str:
        unitname = _make_unitname(path)
        with open(path, "r") as fp:
            contents = fp.read()
        self.add_source(unitname, contents)
        return unitname

    def add_source(self, unitname: str, contents: str):
        self._sources[unitname] = contents

    def get_source(self, unitname: str):
        return self._sources[unitname]

    def value(self):
        return {
            "language": self._language,
            "settings": self._settings,
            "sources": {
                k: {"content": v} for k, v in self._sources.items()
            }
        }
