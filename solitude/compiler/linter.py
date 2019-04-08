# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Union, Iterator, Tuple  # noqa
from collections import OrderedDict

from solitude.common import (
    ContractSourceList, FileMessage)

from solitude.compiler.solium_wrapper import SoliumWrapper


class Linter:
    def __init__(self, executable: str, plugins: List[str], rules: Union[dict, OrderedDict]):
        super().__init__()
        self._executable = executable
        self._solium = SoliumWrapper(executable, plugins, rules)

    def lint_iter(self, sourcelist: ContractSourceList) -> Iterator[Tuple[str, FileMessage]]:
        try:
            for path in self._file_sources:
                yield path, self._solium.lint_file(path)
            for source_name, source in self._text_sources:
                filename = "source#" + source_name
                yield filename, self._solium.lint_source(source, filename)
        finally:
            self._clear_sources()

    def lint(self, sourcelist: ContractSourceList) -> List[Tuple[str, FileMessage]]:
        return list(self.lint_iter(sourcelist))
