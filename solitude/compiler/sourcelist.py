# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

"""Contract Source Lists

This module provides a class to list Solidity contracts (.SOL) of interest.
Contracts can be referenced using the filesystem paths or a can be stored
as a text string (inline contracts).

"""

import os
from typing import List, Tuple, Union  # noqa


class SourceList:
    """Store contracts references

    Store asbolute path for contracts (.sol) and save the list of inline
    contracts. Inline contracts are tuples made by tow strings: the inline
    contract name and the contract code.

    Attributes:
        _file_sources (list(str)): list of the contracts' asbolute paths.
        _text_sources (list[tuple[str, str]]): list of inline contracts tuples.

    """
    SOURCE_FILE_EXT_FILTER = [".sol"]

    def __init__(self):
        self._file_sources = []  # type: List[str]
        self._text_sources = []  # type: List[Tuple[str, str]]

    def add_directory(self, path: str):
        """Scan a directory and add the contracts path to the file source list."""
        for root, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                if os.path.splitext(filename)[1].lower() in SourceList.SOURCE_FILE_EXT_FILTER:
                    self._file_sources.append(os.path.join(root, filename))
        return self

    def add_files(self, sources: Union[str, List[str]]):
        """Add a file path or a list of file paths to the file source list."""
        if isinstance(sources, str):
            self._file_sources.append(sources)
        else:
            self._file_sources.extend(sources)
        return self

    def add_string(self, name: str, source: str):
        """Add a inline contract to the text sources list.

        Args:
            name: Inline contract name.
            source: The source code of the inline contract.
        """
        self._text_sources.append((name, source))
        return self

    def _clear_sources(self):
        """Removes all the contracts references in the file source and text lists."""
        self._file_sources = []
        self._text_sources = []
