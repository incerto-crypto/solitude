# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from collections import namedtuple
import binascii

TransactionInfo = namedtuple('TransactionInfo', [
    'contract',
    'address',
    'function',
    'fnargs',
    'txargs',
    'txhash',
    'receipt'])

FileMessage = namedtuple("FileMessage", [
    "type",
    "filename",
    "line",
    "column",
    "message"])


def file_message_format(m: FileMessage):
    return "%s:%s:%s: %s: %s" % (
        m.filename, m.line, m.column, m.type, m.message)


def bhex(b: bytes, pad=None, prefix=True):
    s = binascii.hexlify(b).decode()
    if pad is not None:
        s = ("00" * (pad - len(b))) + s
    if prefix:
        s = "0x" + s
    return s
