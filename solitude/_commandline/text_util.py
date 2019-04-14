# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Tuple
import sys


class TablePrinter:
    def __init__(self, cols: List[Tuple[str, int]], file=sys.stdout):
        self._fp = file
        self._sizes = [x[1] for x in cols]
        self._header = [x[0] for x in cols]
        self.width = sum(abs(x[1]) for x in cols)

    def write_header(self):
        self.write(self._header)

    def write(self, row: list):
        assert(len(row) == len(self._sizes))
        text = []
        for i, element in enumerate(row):
            x = str(element)
            c = self._sizes[i]
            if len(x) < abs(c):
                text.append(x + (" " * (abs(c) - len(x))))
            elif c > 0:
                text.append(x[:c])
            elif c < 0:
                text.append(x[c:])
            else:
                text.append(x)
        print("".join(text), file=self._fp)


class _FileWrapper:
    def __init__(self, fp):
        self._fp = fp

    def __enter__(self):
        return self._fp

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def open_write(filename):
    if filename == "-":
        return _FileWrapper(sys.stdout)
    else:
        return open(filename, "w")
