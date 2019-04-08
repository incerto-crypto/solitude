# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Optional  # noqa
import web3
import solitude.client.eth_client  # noqa
from solitude.errors import TransactionError, CallForbiddenError
from solitude.common import TransactionInfo
import functools

__all__ = [
    "ContractBase"
]


class ContractBase:
    """Wrapper around web3 contract object. Allows to define wrapper methods
        to call contract functions
    """
    def __init__(
            self,
            client: "solitude.client.eth_client.ETHClient",
            unitname: str,
            contractname: str,
            contract: web3.contract.Contract):
        """
        :param w3: web3 instance
        :param contract: web3 contract instance:
        """
        self._client = client  # type solitude.client.eth_client.ETHClient
        self._unitname = unitname
        self._contractname = contractname
        self._contract = contract

    @property
    def unitname(self):
        return self._unitname

    @property
    def name(self) -> str:
        return self._contractname

    @property
    def account(self):
        """
        :return: account which is being as sender
        """
        return self._client.web3.eth.defaultAccount

    @property
    def address(self):
        """
        :return: contract address
        """
        return self._contract.address

    @property
    def abi(self):
        """
        :return: contract abi
        """
        return self._contract.abi

    @property
    def functions(self):
        """
        :return: functions from web3 contract object
        """
        return self._contract.functions

    def __getattr__(self, key):
        # redirect any unknown attribute to contract object
        return getattr(self._contract, key)

    def call(self, func: str, *args):
        return getattr(self._contract.functions, func)(*args).call()

    def transact_sync(self, func: str, *args, value: int=None, gas: int=None, gasprice: int=None):
        """Send a transaction and wait for its receipt
        :param func: function name
        :param args: function arguments
        :param value: optional amount of ether to send (in wei)
        :param gas: optional gas limit
        :param gasprice: optional gas price
        :return: web3 transaction receipt
        """
        txargs = {
            "from": self._client.get_current_account(),
            "gas": self._client._default_gas
        }
        if value is not None:
            txargs["value"] = value
        if gas is not None:
            txargs["gas"] = gas
        if gasprice is not None:
            txargs["gasPrice"] = gasprice
        txhash = None
        receipt = None
        try:
            txhash = getattr(self._contract.functions, func)(*args).transact(txargs)
            receipt = self._client.web3.eth.waitForTransactionReceipt(txhash)
            info = TransactionInfo(
                unitname=self._unitname,
                contractname=self._contractname,
                address=self._contract.address,
                function=func,
                fnargs=args,
                txargs=txargs,
                txhash=bytes(txhash),
                receipt=receipt)
            self._client._on_transaction(info)
            if receipt.status == 0:
                raise TransactionError(
                    message="Transaction returned status 0",
                    info=info)
            return info
        except ValueError as e:
            raise TransactionError(
                message=str(e),
                info=TransactionInfo(
                    contract=self._contractname,
                    address=self._contract.address,
                    function=func,
                    fnargs=args,
                    txargs=txargs,
                    txhash=bytes(txhash) if txhash is not None else None,
                    receipt=receipt))
