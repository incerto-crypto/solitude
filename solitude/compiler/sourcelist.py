# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
from typing import List, Tuple, Union  # noqa


class SourceList:
    SOURCE_FILE_EXT_FILTER = [".sol"]

    def __init__(self):
        self._file_sources = []  # type: List[str]
        self._text_sources = []  # type: List[Tuple[str, str]]

    def add_directory(self, path: str):
        for root, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                if os.path.splitext(filename)[1].lower() in SourceList.SOURCE_FILE_EXT_FILTER:
                    self._file_sources.append(os.path.join(root, filename))
        return self

    def add_files(self, sources: Union[str, List[str]]):
        if isinstance(sources, str):
            self._file_sources.append(sources)
        else:
            self._file_sources.extend(sources)
        return self

    def add_string(self, name: str, source: str):
        self._text_sources.append((name, source))
        return self

    def _clear_sources(self):
        self._file_sources = []
        self._text_sources = []
