# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List
import subprocess
import re
import json
import datetime
import os
import sys
from solitude.errors import SetupError, CompilerError
from solitude.common import FileMessage


COMBINED_JSON_ALLOWED = set([
    "ast",
    "abi",
    "devdoc",
    "userdoc",
    "metadata",
    "ir",
    "evm.assembly",
    "evm.bytecode.object",
    "evm.bytecode.opcodes",
    "evm.bytecode.sourceMap",
    "evm.bytecode.linkReferences",
    "evm.deployedBytecode.object",
    "evm.deployedBytecode.opcodes",
    "evm.deployedBytecode.sourceMap",
    "evm.deployedBytecode.linkReferences",
    "evm.methodIdentifiers",
    "evm.gasEstimates"
])

COMBINED_JSON_GLOBAL = set(["ast"])

COMBINED_JSON_DEFAULT = [
    "abi",
    "evm.bytecode.object"
]


def make_unit_name(path):
    if sys.platform == "win32":
        path = path.replace("\\", "/")
        if path[1] == ":":
            path = "/" + path[0] + path[2:]
        return path
    return path


class SolcWrapper:
    def __init__(
            self,
            executable="solc",
            combined_json: List[str]=COMBINED_JSON_DEFAULT,
            optimize: int=None,
            evm_version: str=None):
        for value in combined_json:
            if value not in COMBINED_JSON_ALLOWED:
                raise SetupError("solc: Unknown output type: '%s'" % value)
        self._executable = executable
        self._combined_json = combined_json[:]
        self._optimize = optimize
        self._evm_version = evm_version

    def compile_source(self, source: str, name: str="<stdin>"):
        return self._compile(stdin=source, stdin_alias=name)

    def compile_files(self, files: List[str]):
        return self._compile(source_files=[
            os.path.abspath(filename) for filename in files])

    def _compile(self, stdin=None, source_files=None, stdin_alias="<stdin>"):
        cmd = [self._executable, "--standard-json"]

        outputSelection = {
            "*": {
                "*": [val for val in self._combined_json if val not in COMBINED_JSON_GLOBAL],
                "": [val for val in self._combined_json if val in COMBINED_JSON_GLOBAL]
            }
        }
        data = {
            "language": "Solidity",
            "settings": {
                "metadata": {
                    "useLiteralContent": True
                },
                "outputSelection": outputSelection
            },
            "sources": {}
        }

        if self._optimize is not None:
            if "settings" not in data:
                data["settings"] = {}
            data["settings"]["optimizer"] = {
                "enabled": True,
                "runs": self._optimize
            }

        if self._evm_version is not None:
            if "settings" not in data:
                data["settings"] = {}
            data["settings"]["evmVersion"] = self._evm_version

        unit_to_source = {}
        if source_files is not None:
            # directories = set()
            # for path in source_files:
            #     dname = os.path.dirname(os.path.abspath(path))
            #     directories.add(dname)
            #     data["sources"][path] = {
            #         "urls": [
            #             os.path.abspath(path)
            #         ]
            #     }
            # cmd.extend(["--allow-paths", ",".join(directories)])]
            for path in source_files:
                with open(path, "r") as fp:
                    content = fp.read()
                path_unit_name = make_unit_name(path)
                data["sources"][path_unit_name] = {
                    "content": content
                }
                unit_to_source[path_unit_name] = content

        if stdin is not None:
            content = stdin
            data["sources"][stdin_alias] = {
                "content": content
            }
            unit_to_source[stdin_alias] = content

        stdin_data = json.dumps(data, indent=2).encode("utf-8")
        # print(cmd)
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        out, err = p.communicate(stdin_data)

        # TODO remove
        # DUMP_CMDLINE = "/tmp/solcjs-debug/cmdline.json"
        # DUMP_IN = "/tmp/solcjs-debug/input.json"
        # DUMP_OUT = "/tmp/solcjs-debug/output.json"
        # print(json.dumps(cmd, indent=2), file=open(DUMP_CMDLINE, "w"))
        # print(json.dumps(json.loads(stdin_data.decode('utf-8')), indent=2), file=open(DUMP_IN, "w"))
        # try:
        #   print(json.dumps(json.loads(out.decode('utf-8')), indent=2), file=open(DUMP_OUT, "w"))
        # except:
        #   print('STDOUT\n' + out.decode('utf-8') + "\nSTDERR\n" + err.decode('utf-8'), file=open(DUMP_OUT, "w"))

        out_dict = json.loads(out.decode('utf-8'))
        if "errors" in out_dict and len(out_dict["errors"]):
            if any(error.get("severity") == "error" for error in out_dict["errors"]):
                errors = []
                pos_regex = re.compile(r"^(.+):([0-9]+):([0-9]+):\s*([^:\s]+)\s*:")
                for error in out_dict["errors"]:
                    if error.get("severity") != "error":
                        pass
                    m = pos_regex.search(error["formattedMessage"])
                    line, column = 1, 1
                    if m is not None:
                        line = int(m.group(2))
                        column = int(m.group(3))
                    errors.append(FileMessage(
                        type=error.get("severity", ""),
                        filename=error.get("sourceLocation", {}).get("file", ""),
                        line=line,
                        column=column,
                        message=error["message"]))
                raise CompilerError(errors)

        out_dict = json.loads(out.decode('utf-8'))
        if "contracts" not in out_dict:
            return {}
        contracts = out_dict["contracts"]
        sources = out_dict["sources"]
        output = {}
        sourceList = [None] * len(sources)

        unit_to_ast = {}
        for unit_name, unit_data in sources.items():
            unit_to_ast[unit_name] = unit_data["ast"]
            sourceList[unit_data["id"]] = unit_name

        for unit_name, contracts_in_unit in contracts.items():
            for contract_name, contract_data in contracts_in_unit.items():
                out_data = {}
                out_data["abi"] = contract_data["abi"]
                out_data["bin"] = contract_data["evm"]["bytecode"]["object"]
                out_data["srcmap"] = contract_data["evm"]["bytecode"]["sourceMap"]
                out_data["bin-runtime"] = contract_data["evm"]["deployedBytecode"]["object"]
                out_data["srcmap-runtime"] = contract_data["evm"]["deployedBytecode"]["sourceMap"]
                out_data["_solitude"] = {
                    "ast": unit_to_ast[unit_name],
                    "contractName": contract_name,
                    "sourceList": sourceList,
                    "sourcePath": unit_name,
                    "source": unit_to_source[unit_name],
                    "timestamp": datetime.datetime.now().isoformat()
                }
                output[(unit_name, contract_name)] = out_data
        return output
