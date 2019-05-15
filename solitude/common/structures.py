# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree
from typing import Optional
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
TransactionInfo.__doc__ = "Transaction information"
TransactionInfo.unitname.__doc__ = "source unit name"
TransactionInfo.contractname.__doc__ = "contract name"
TransactionInfo.address.__doc__ = "contract instance address"
TransactionInfo.function.__doc__ = "function name"
TransactionInfo.fnargs.__doc__ = "function arguments as tuple"
TransactionInfo.txargs.__doc__ = "transaction arguments as dictionary ('gas', 'gasprice', 'value')"
TransactionInfo.receipt.__doc__ = "full web3 receipt"


FileMessage = namedtuple("FileMessage", [
    "type",
    "unitname",
    "line",
    "column",
    "message"])
FileMessage.__doc__ = "message (error, warning) related to a text file"
FileMessage.type.__doc__ = "a string indicating the message type"
FileMessage.unitname.__doc__ = "source unit name or file name"
FileMessage.line.__doc__ = "line number, optional"
FileMessage.column.__doc__ = "column number, optional"
FileMessage.message.__doc__ = "the message string"


def file_message_format(m: FileMessage):
    """Format a FileMessage object to string
    """
    return "%s:%s:%s: %s: %s" % (
        m.unitname, m.line, m.column, m.type, m.message)


def hex_repr(b: bytes, pad: Optional[int]=None, prefix=True):
    """Get hex string representation of a byte array

    :param b: byte array
    :param pad: pad to fixed number of characters
    :param prefix: prefix with '0x'
    """
    s = binascii.hexlify(b).decode()
    if pad is not None:
        s = ("00" * min(0, pad - len(b))) + s
    if prefix:
        s = "0x" + s
    return s
