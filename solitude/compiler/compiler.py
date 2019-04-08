# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Union, Dict, Optional, Tuple  # noqa
import os
import copy
import json
from io import StringIO

from solitude.common import (
    ContractSourceList, ContractObjectList, FileMessage)
from solitude.errors import CompilerError

from solitude.compiler.solc_wrapper import SolcWrapper as SolcWrapper


class Compiler:
    Out = SolcWrapper.Out

    OUTPUT_VALUES = [
        SolcWrapper.Out.AST,
        SolcWrapper.Out.ABI,
        SolcWrapper.Out.DEPLOY_OBJECT,
        # SolcWrapper.Out.DEPLOY_OPCODES,
        SolcWrapper.Out.DEPLOY_SOURCEMAP,
        # SolcWrapper.Out.DEPLOY_LINKREFS,
        SolcWrapper.Out.RUNTIME_OBJECT,
        # SolcWrapper.Out.RUNTIME_OPCODES,
        SolcWrapper.Out.RUNTIME_SOURCEMAP,
        # SolcWrapper.Out.RUNTIME_LINKREFS,
    ]

    def __init__(self, executable: str, optimize: Optional[int]=None):
        super().__init__()
        self._executable = executable
        self._solc = SolcWrapper(
            executable=executable,
            outputs=Compiler.OUTPUT_VALUES,
            optimize=optimize,
            warnings_as_errors=False)  # TODO expose this option

    def compile(self, sourcelist: ContractSourceList) -> ContractObjectList:
        """Compile all contracts
        """
        output_dict = self._solc.compile(
            source_files=sourcelist.file_sources,
            source_strings=sourcelist.text_sources)

        compiled = ContractObjectList()
        for (unitname, contractname), data in output_dict.items():
            compiled.add_contract(unitname, contractname, data)
        return compiled
