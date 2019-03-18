# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List
from solitude.common import TransactionInfo, FileMessage, file_message_format
import binascii


class SolitudeError(Exception):
    pass


class CLIError(SolitudeError):
    pass


class ToolNotFoundError(SolitudeError):
    def __init__(self, toolname: str):
        super().__init__("Required tool is missing: %s" % toolname)


class AccountError(SolitudeError):
    pass


class SetupError(SolitudeError):
    pass


class InstallError(SolitudeError):
    pass


class RPCError(SolitudeError):
    pass


class InternalError(SolitudeError):
    def __init__(self, message: str, data):
        super().__init__(message)
        self._data = data


class TransactionError(SolitudeError):
    def __init__(
            self,
            message: str,
            info: TransactionInfo):
        super().__init__(
            "Transaction Error in %s.%s. %s. debug with txhash: 0x%s" % (
                info.contract,
                info.function,
                message,
                binascii.hexlify(info.txhash).decode()))
        self.info = info


class CallForbiddenError(SolitudeError):
    pass


class CompilerError(SolitudeError):
    def __init__(
            self,
            messages: List[FileMessage]):
        self.messages = messages
        super().__init__(self.format_message(0))

    def format_message(self, index: int):
        m = self.messages[index]
        return file_message_format(m)
