# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List  # noqa
import datetime
import os
from solitude.errors import SetupError


def unique_dumpname(dirname, logname) -> str:
    t = datetime.datetime.utcnow()
    for _ in range(1000):
        filename = "%04d%02d%02d_%02d%02d%02d_%03d_%s.log" % (
            t.year, t.month, t.day,
            t.hour, t.minute, t.second,
            t.microsecond // 1000,
            logname)
        path = os.path.join(dirname, filename)
        if not os.path.exists(path):
            return path
        t += datetime.timedelta(microseconds=1000)
    raise SetupError("Cannot get unique filename")


class DumpPushWithStatement:
    def __init__(self, ctx, name: str):
        self._ctx = ctx
        self._name = name

    def __enter__(self):
        self._ctx._push(self._name)
        return self

    def __exit__(self, _type, value, traceback):
        self._ctx._pop()


class Dump:
    FLUSH = 1000

    def __init__(self, filename: str=None, fileobj=None, prefix: str=None):
        self._need_close = False
        assert (filename is None) or (fileobj is None)
        if filename is not None:
            filedir = os.path.dirname(filename)
            if not os.path.isdir(filedir):
                os.makedirs(filedir, exist_ok=True)
            self._fp = open(filename, 'w')
            self._need_close = True
        elif fileobj is not None:
            self._fp = fileobj
        else:
            self._fp = None  # noqa
        self._count = 0
        self._stack = []  # type: List[str]
        self._prefix = ""
        if prefix is not None:
            self._push(prefix)

    def write(self, msg, *args):
        if self._fp is None:
            return
        msg = self._prefix + (msg % args)
        self._count += len(msg)
        print(msg, file=self._fp)
        if self._count > Dump.FLUSH:
            self._fp.flush()

    def raw(self, msg, *args):
        if self._fp is None:
            return
        msg = self._prefix + (msg % args)
        self._count += len(msg)
        print(msg % args, end="", file=self._fp)
        if self._count > Dump.FLUSH:
            self._fp.flush()

    def __call__(self, msg, *args):
        self.write(msg, *args)

    def __del__(self):
        if hasattr(self, '_fp'):
            self.close()

    def close(self):
        if self._need_close:
            self._need_close = False
            self._fp.close()

    def push(self, name):
        return DumpPushWithStatement(self, name)

    def _push(self, name):
        self._stack.append(name)
        self._prefix = "".join(self._stack)

    def _pop(self):
        del self._stack[-1]
        self._prefix = "".join(self._stack)


__all__ = [
    "Dump",
    "unique_dumpname"
]
