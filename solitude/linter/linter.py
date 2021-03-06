# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Union, Iterator, Tuple  # noqa
from collections import OrderedDict

from solitude.common import (
    ContractSourceList, FileMessage, path_to_unitname)

from multiprocessing.pool import ThreadPool
from solitude.linter.solium_wrapper import SoliumWrapper


class Linter:
    """The linter object allows linting groups of contracts.
    """

    def __init__(
            self,
            executable: str,
            plugins: List[str],
            rules: dict,
            parallelism: int=4):
        """Create a Linter

        :param executable: path to the solium executable file
        :param plugins: list of solium plugins
        :param rules: dictionary containing solium rules
        :param parallelism: maximum number of parallel instances to be run
        """
        self._solium = SoliumWrapper(executable, plugins, rules)
        self._parallelism = parallelism

    def lint(self, sourcelist: ContractSourceList) -> Iterator[Tuple[str, FileMessage]]:
        """Lint a group of contracts

        :param sourcelist: source files to lint, as ContractSourceList
        :return: an iterator of FileMessage objects containing the linter output information
        """
        pool = ThreadPool(processes=self._parallelism)
        futures = []

        for path in sourcelist.file_sources:
            futures.append(
                pool.apply_async(self._solium.lint_file, args=(path, )))
        for unitname, source in sourcelist.text_sources.items():
            futures.append(
                pool.apply_async(self._solium.lint_source, args=(source, unitname)))

        for future in futures:
            errors = future.get()
            for error in errors:
                yield error
