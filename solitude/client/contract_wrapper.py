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
    "payable",
    "view",
    "pure",
    "nonpayable",
    "cached_property",
    "ContractWrapper"
]


class DecoratorStack:
    VALUES = [
        "nonpayable", "payable", "view", "pure"]
    TRANSITIONS = {
        "payable": ["payable", "nonpayable", "view", "pure"],
        "nonpayable": ["nonpayable", "view", "pure"],
        "view": ["view", "pure"],
        "pure": ["pure"]}

    def __init__(self):
        self._stack = []

    def push(self, x):
        assert(x in DecoratorStack.VALUES)
        if len(self._stack):
            prev = self._stack[-1]
            if x not in DecoratorStack.TRANSITIONS[prev]:
                raise CallForbiddenError(
                    "Cannot call @%s function in @%s" % (x, prev))
        self._stack.append(x)

    def pop(self):
        del self._stack[-1]

    @property
    def value(self):
        if not len(self._stack):
            return "nonpayable"
        return self._stack[-1]


def payable(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _self = args[0]
        _self._decorator.push("payable")
        try:
            return func(*args, **kwargs)
        finally:
            _self._decorator.pop()
    return wrapper


def view(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _self = args[0]
        _self._decorator.push("view")
        try:
            return func(*args, **kwargs)
        finally:
            _self._decorator.pop()
    return wrapper


def pure(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _self = args[0]
        _self._decorator.push("pure")
        try:
            return func(*args, **kwargs)
        finally:
            _self._decorator.pop()
    return wrapper


def nonpayable(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _self = args[0]
        _self._decorator.push("nonpayable")
        try:
            return func(*args, **kwargs)
        finally:
            _self._decorator.pop()
    return wrapper


class cached_property:
    def __init__(self, func):
        self._func = func
        self._cached = None
        self._is_cached = False

    def __get__(self, obj, cls):
        if not self._is_cached:
            self._cached = self._func(obj)
            self._is_cached = True
        return self._cached


class ContractWrapper:
    """Wrapper around web3 contract object. Allows to define wrapper methods
        to call contract functions
    """
    def __init__(
            self,
            client: "solitude.client.eth_client.ETHClient",
            contract_name: str,
            contract: web3.contract.Contract):
        """
        :param w3: web3 instance
        :param contract: web3 contract instance:
        """
        self._client = client  # type solitude.client.eth_client.ETHClient
        self._contract_name = contract_name
        self._contract = contract
        self._decorator = DecoratorStack()

    @property
    def name(self) -> str:
        return self._contract_name

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
        if self._decorator.value not in ("view", "pure"):
            raise CallForbiddenError("Call not allowed in function not marked @pure, @view")
        return getattr(self._contract.functions, func)(*args).call()

    def transact_sync(self, func: str, *args, value: int=None, gas: int=None, gasprice: int=None):
        """Send a transaction and wait for its receipt
        :param func: function name
        :param args: function arguments
        :param value: optional amount of ether to send (in wei)
        :param gas: optional gas limit
        :param gasPrice: optional gas price
        :return: web3 transaction receipt
        """
        if self._decorator.value in ("view", "pure"):
            raise CallForbiddenError("Transaction not allowed in function marked @pure, @view")
        txargs = {
            "from": self._client.get_current_account(),
            "gas": self._client._default_gas
        }
        if value is not None:
            if self._decorator.value not in ("payable", ):
                raise CallForbiddenError("Paying not allowed in function not marked @payable")
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
                contract=self._contract_name,
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
                    contract=self._contract_name,
                    address=self._contract.address,
                    function=func,
                    fnargs=args,
                    txargs=txargs,
                    txhash=bytes(txhash) if txhash is not None else None,
                    receipt=receipt))


class IContractNoCheck(ContractWrapper):
    @payable
    def transact_sync(self, func: str, *args, value: int=None, gas: int=None, gasprice: int=None):
        return super().transact_sync(func, *args, value=value, gas=gas, gasprice=gasprice)

    @view
    def call(self, func: str, *args):
        return super().call(func, *args)
