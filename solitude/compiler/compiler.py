# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Union, Dict, Optional, Tuple  # noqa
import os
import copy
import json
from io import StringIO
from solitude.compiler.sourcelist import SourceList
from solitude.compiler.solc_wrapper import SolcWrapper
from solitude.errors import CompilerError, FileMessage


class CompiledSources:
    def __init__(self):
        self._contracts = {}

    def add_contract(self, contract_name: str, compiled_contract: dict):
        if contract_name in self._contracts:
            raise CompilerError([FileMessage(
                type="duplicate",
                filename=contract_name,
                line=None,
                column=None,
                message="Duplicate contract name found")])
        self._contracts[contract_name] = compiled_contract

    def add_directory(self, path: str):
        for filename in os.listdir(path):
            if os.path.splitext(filename)[1].lower() in (".json"):
                with open(os.path.join(path, filename)) as fp:
                    contract = json.load(fp)
                    self.add_contract(
                        contract["_solitude"]["contractName"],
                        contract)

    def save_directory(self, path: str):
        os.makedirs(path, exist_ok=True)
        for contract_name, contract in self._contracts.items():
            with open(os.path.join(path, contract_name + ".json"), "w") as fp:
                json.dump(contract, fp, indent=2)

    def update(self, other: "CompiledSources"):
        for contract_name, contract in other._contracts.items():
            self.add_contract(contract_name, contract)

    @property
    def contracts(self):
        return copy.copy(self._contracts)


class Compiler(SourceList):
    OUTPUT_VALUES = [
        "ast",
        "abi",
        "evm.bytecode.object",
        "evm.bytecode.opcodes",
        "evm.bytecode.sourceMap",
        "evm.bytecode.linkReferences",
        "evm.deployedBytecode.object",
        "evm.deployedBytecode.opcodes",
        "evm.deployedBytecode.sourceMap",
        "evm.deployedBytecode.linkReferences"
    ]

    def __init__(self, executable: str, optimize: Optional[int]=None):
        super().__init__()
        self._executable = executable
        self._solc = SolcWrapper(
            executable=executable,
            combined_json=Compiler.OUTPUT_VALUES,
            optimize=optimize)

    def compile(self) -> CompiledSources:
        """Compile all contracts
        """
        try:
            compiled = CompiledSources()
            compiler_outputs = []  # type: List[Dict[str, dict]]
            if self._file_sources:
                compiler_outputs.append(
                    self._solc.compile_files(self._file_sources))
            for source_name, source in self._text_sources:
                compiler_outputs.append(
                    self._solc.compile_source(source, "source#" + source_name))
            for output_dict in compiler_outputs:
                for (source_path, contract_name), contract in output_dict.items():
                    compiled.add_contract(contract_name, contract)
            return compiled
        finally:
            self._clear_sources()
