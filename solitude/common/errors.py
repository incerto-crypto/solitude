# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List
from solitude._internal.errors import SolitudeError
from solitude.common.structures import TransactionInfo, FileMessage, file_message_format, hex_repr


class CLIError(SolitudeError):
    pass


class SetupError(SolitudeError):
    pass


class CommunicationError(SolitudeError):
    pass


class RequestError(SolitudeError):
    pass


class TransactionError(RequestError):
    def __init__(
            self,
            message: str,
            info: TransactionInfo):
        super().__init__(
            "Transaction Error in %s:%s.%s. %s. debug with txhash: %s" % (
                info.unitname,
                info.contractname,
                info.function,
                message,
                hex_repr(info.txhash)))
        self.info = info


class CompilerError(SolitudeError):
    def __init__(
            self,
            messages: List[FileMessage]):
        self.messages = messages
        super().__init__(self.format_message(0))

    def format_message(self, index: int):
        m = self.messages[index]
        return file_message_format(m)
