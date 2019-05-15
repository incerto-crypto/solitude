# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Optional  # noqa
import web3
import solitude.client.eth_client  # noqa
from solitude.common.errors import TransactionError
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
        :param client: solitude client object which produced this instance
        :param unitname: name of the source unit containing the contract
        :param contractname: name of the contract
        :param contract: web3 contract instance:
        """
        self._client = client  # type solitude.client.eth_client.ETHClient
        self._unitname = unitname
        self._contractname = contractname
        self._contract = contract

    @property
    def unitname(self):
        """Name of the source unit containing this contract"""
        return self._unitname

    @property
    def name(self) -> str:
        """Contract name"""
        return self._contractname

    @property
    def account(self):
        """Account which is being used as sender"""
        return self._client.web3.eth.defaultAccount

    @property
    def address(self):
        """Contract address"""
        return self._contract.address

    @property
    def abi(self) -> dict:
        """Contract ABI"""
        return self._contract.abi

    @property
    def functions(self):
        """Functions from web3 contract object"""
        return self._contract.functions

    @property
    def web3(self):
        """Raw web3 contract object"""
        return self._contract

    def call(self, func: str, *args):
        r"""Call a function in the contract

        :param func: function name
        :param \*args: function arguments
        """
        return getattr(self._contract.functions, func)(*args).call()

    def transact_sync(self, func: str, *args, value: int=None, gas: int=None, gasprice: int=None) -> TransactionInfo:
        r"""Send a transaction and wait for its receipt

        :param func: function name
        :param \*args: function arguments
        :param value: optional amount of ether to send (in wei)
        :param gas: optional gas limit
        :param gasprice: optional gas price
        :return: transaction information
        """
        txargs = {
            "from": self._client.get_current_account()
        }

        if value is not None:
            txargs["value"] = value

        if gas is not None:
            txargs["gas"] = gas
        elif self._client._default_gaslimit is not None:
            txargs["gas"] = self._client._default_gaslimit

        if gasprice is not None:
            txargs["gasPrice"] = gasprice
        elif self._client._default_gasprice is not None:
            txargs["gasPrice"] = self._client._default_gasprice

        txhash = None
        receipt = None
        try:
            # TODO if gas is not defined, web3 will automatically call estimateGas. In this case,
            #  when estimateGas fails, the transaction will fail without a TXHASH.
            # Instead of letting web3 call estimateGas, call it explicitly and return a different
            #   error in case estimateGas fails, explaining that the user should provide a
            #   gas value in order to obtain a txhash to debug.
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
                    unitname=self._unitname,
                    contractname=self._contractname,
                    address=self._contract.address,
                    function=func,
                    fnargs=args,
                    txargs=txargs,
                    txhash=bytes(txhash) if txhash is not None else None,
                    receipt=receipt))
