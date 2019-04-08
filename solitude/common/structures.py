# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from collections import namedtuple
import binascii

TransactionInfo = namedtuple('TransactionInfo', [
    'unitname',
    'contractname',
    'address',
    'function',
    'fnargs',
    'txargs',
    'txhash',
    'receipt'])

FileMessage = namedtuple("FileMessage", [
    "type",
    "unitname",
    "line",
    "column",
    "message"])


def file_message_format(m: FileMessage):
    return "%s:%s:%s: %s: %s" % (
        m.unitname, m.line, m.column, m.type, m.message)


def hex_repr(b: bytes, pad=None, prefix=True):
    s = binascii.hexlify(b).decode()
    if pad is not None:
        s = ("00" * min(0, pad - len(b))) + s
    if prefix:
        s = "0x" + s
    return s
