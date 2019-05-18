# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
from typing import List, Tuple, Dict, Optional  # noqa
from solitude._internal import type_assert, RaiseForParam


class ContractSourceList:
    """A collection of contract sources
    """

    def __init__(self):
        """Create an empty collection of contract sources
        """
        self._file_sources = []  # type: List[str]
        self._text_sources = {}  # type: Dict[str, str]

    def add_directory(self, path: str, ext_filter: Optional[List[str]]=[".sol"]) -> None:
        """Add all sources from a directory.

        :param path: directory path
        :param ext_filter: list of allowed extensions for the source file names, including
            the '.' character (e.g. [".sol"]), or None for any extension
        """
        with RaiseForParam("path"):
            type_assert(path, str)
        for root, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                if ext_filter is None or os.path.splitext(filename)[1].lower() in ext_filter:
                    self._file_sources.append(os.path.join(root, filename))

    def add_file(self, path: str) -> None:
        """Add file to the list of sources.

        :param path: file path
        """
        with RaiseForParam("path"):
            type_assert(path, str)
        self._file_sources.append(path)

    def add_files(self, sources: List[str]) -> None:
        """Add list of files to the list of sources.

        :param sources: list of file paths
        """
        with RaiseForParam("source"):
            type_assert(sources, list, ", paths to source files")
            for source in sources:
                type_assert(source, str, ", item in source file list")
        self._file_sources.extend(sources)

    def add_string(self, unitname: str, source: str) -> None:
        """Add a source string to the list of sources

        :param unitname: a name for the provided source unit
        :param source: source code text
        """
        with RaiseForParam("unitname"):
            type_assert(unitname, str)
        with RaiseForParam("source"):
            type_assert(source, str)
        self._text_sources[unitname] = source

    def _clear_sources(self) -> None:
        self._file_sources = []
        self._text_sources = {}

    @property
    def text_sources(self) -> Dict[str, str]:
        """All added source strings as dictionary of unitname -> source.
        """
        return self._text_sources

    @property
    def file_sources(self) -> List[str]:
        """All added file sources as list of paths
        """
        return self._file_sources
