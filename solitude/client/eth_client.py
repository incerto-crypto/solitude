# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Union, List, Dict, Tuple, Optional  # noqa
import binascii
import fnmatch
import time
import warnings
import itertools
from collections import namedtuple
from solitude._internal import RaiseForParam, type_assert, value_assert

# import web3 and suppress the warnings it generates
with warnings.catch_warnings():  # noqa
    warnings.simplefilter("ignore")  # noqa
    from web3 import Web3
    from web3.utils.events import get_event_data
    import web3.contract

from solitude.common.errors import SetupError
from solitude.common import (
    ContractObjectList, TransactionInfo, hex_repr, Dump)

from solitude.common import RPCClient
from solitude.client.contract import ContractBase


class EventCaptureContext:
    def __init__(self):
        super().__init__()
        self._event_filter_stack = []

    def _push_filter(self, pattern):
        self._event_filter_stack.append(pattern)

    def _pop_filter(self):
        del self._event_filter_stack[-1]

    def _check_filters(self, text: str):
        for flt in self._event_filter_stack:
            if isinstance(flt, str):
                if fnmatch.fnmatch(text, flt):
                    return True
            else:
                if flt.match(text) is not None:
                    return True
        return False


class AccountContext:
    def __init__(self):
        super().__init__()
        self._account_stack = []  # type: List[Union[str, int]]

    def _push_account(self, name: Union[str, int]):
        self._account_stack.append(name)

    def _pop_account(self):
        del self._account_stack[-1]

    def _get_account(self) -> Union[str, int]:
        try:
            return self._account_stack[-1]
        except IndexError:
            value_assert(False, "No account in current scope")


class AccountWithStatement:
    def __init__(self, ctx: AccountContext, name: Union[str, int]):
        self._ctx = ctx
        self._name = name

    def __enter__(self):
        self._ctx._push_account(self._name)
        return self

    def __exit__(self, _type, value, traceback):
        self._ctx._pop_account()


class EventCaptureWithStatement:
    def __init__(self, ctx: EventCaptureContext, flt):
        self._ctx = ctx
        self._flt = flt

    def __enter__(self):
        self._ctx._push_filter(self._flt)
        return self

    def __exit__(self, _type, value, traceback):
        self._ctx._pop_filter()


EventAbi = namedtuple("EventAbi", ["unitname", "contractname", "name", "signature", "abi"])

EventLog = namedtuple("EventLog", ["unitname", "contractname", "name", "address", "args", "data"])
EventLog.__doc__ = "Event information"
EventLog.unitname.__doc__ = "Source unit of the contract which contains the event definition"
EventLog.contractname.__doc__ = "Contract which contains the event definition"
EventLog.name.__doc__ = "Event name"
EventLog.address.__doc__ = "Address of the contract instance which produced the event"
EventLog.args.__doc__ = "Arguments of the emitted event"
EventLog.data.__doc__ = "Raw event data from web3"

Filter = namedtuple("Filter", ["index", "unitname", "contractname", "event_names", "valid"])
Filter.__doc__ = "Filter information"
Filter.index.__doc__ = "Index of the filter on the ETH node"
Filter.unitname.__doc__ = "Source unit of the contract which contains the event definition"
Filter.contractname.__doc__ = "Contract which contains the event definition"
Filter.event_names.__doc__ = "Names of the events to filter"
Filter.valid.__doc__ = "Whether the filter is still valid and it should keep being used"

ZERO_ADDRESS = hex_repr(b"", pad=20, prefix=True)


class ETHClient(AccountContext, EventCaptureContext):
    """
    The ethereum node client object allows to communicate with an ethereum node.

    It is mainly used to produce contract objects which allow to interact with a
    contract instance on the blockchain.

    It stores a collection of contracts, their ABI and optionally their bytecode.
    """
    def __init__(self, endpoint: str):
        """Initialize a new ETH client without any contract.

        :param endpoint: URL of the ethereum server node
        """
        super().__init__()
        self._endpoint = endpoint
        self._web3 = Web3(Web3.HTTPProvider(self._endpoint))
        self._rpc = RPCClient(endpoint=endpoint)
        self._compiled = ContractObjectList()
        self._dump = Dump(fileobj=None)

        self._default_gaslimit = None
        self._default_gasprice = None

        # accounts
        self._account_aliases = {}  # type: Dict[str, int]
        self._reload_accounts()
        self._initial_default_account = self._web3.eth.defaultAccount

        # collect contracts and events
        self._events = []  # type: List[EventAbi]
        self._event_logs = []  # type: List[EventLog]
        self._event_map = {}  # type: Dict[Tuple[str, bytes], EventAbi]
        self._filters = []  # type: List[Filter]

    def update_contracts(self, contracts: ContractObjectList):
        """Update the collection of contracts known to this client

        :param contracts: a collection of contracts (see ContractObjectList)
        """
        self._compiled.update(contracts)
        self._update_events_index(contracts)

    def _update_events_index(self, compiled: ContractObjectList):
        for (unitname, contractname), contract in compiled.contracts.items():
            for abi in contract['abi']:
                if abi.get("type") == "event":
                    event_selector = "{name}({params})".format(
                        name=abi["name"],
                        params=",".join([inp["type"] for inp in abi["inputs"]]))
                    event = EventAbi(
                        unitname,
                        contractname,
                        name=abi["name"],
                        signature=bytes(self._web3.sha3(text=event_selector)),
                        abi=abi)
                    self._events.append(event)
                    key = (event.unitname, event.contractname, event.signature)
                    self._event_map[key] = event

    def _reload_accounts(self):
        self._accounts = list(self._web3.eth.accounts)

    def set_default_gaslimit(self, gas: Optional[int]):
        """Set the default gas limit for transactions

        :param gas: default gas limit, or None. If the gas limit is not set either through
            the default or explicitly in the transaction, web3 will call eth.estimateGas
            first to determine this value.
        """
        self._default_gaslimit = gas

    def set_default_gasprice(self, gasprice: Optional[int]):
        """Set the default gas price for transactions

        :param gasprice: default gas limit, or None. If the gas price is not set,
            web3 will call eth.gasPrice first to determine this value.
        """
        self._default_gasprice = gasprice

    def get_accounts(self, reload=False) -> list:
        """Get the accounts stored in the ETH node

        :param reload: whether to refresh the account list by querying the node
        :retrurn: list of accounts
        """
        # TODO review the _reload_accounts implementation and also provide
        #   the possibility to 'unlock' accounts
        if reload:
            self._reload_accounts()
        return self._accounts[:]

    @property
    def rpc(self) -> RPCClient:
        """A raw JSON-RPC client instance to communicate with the ETH node
        """
        return self._rpc

    @property
    def web3(self):
        """A raw web3 library client instance connected to the ETH node
        """
        return self._web3

    @property
    def contracts(self) -> ContractObjectList:
        """The collection of all contracts known by this client, as a
        ContractObjectList object
        """
        return self._compiled

    def mine_block(self) -> None:
        """Ask the ETH node to mine a new block
        """
        self._rpc.evm_mine()

    def increase_blocktime_offset(self, seconds: int) -> int:
        """Increase the offset to apply to block.timestamp for newly mined blocks

        :param seconds: number of seconds to add to block.timestamp offset (in seconds)
        :return: new block.timestamp offset (in seconds)
        """
        response = self._rpc.evm_increaseTime(seconds)
        return response

    def get_last_blocktime(self) -> int:
        """Get timestamp of last mined block

        :return: last block's timestamp (in seconds)
        """
        time_hex = self._rpc.eth_getBlockByNumber('latest', True)['timestamp']  # type: str
        assert time_hex.startswith("0x")
        return int(time_hex[2:], 16)

    def capture(self, pattern):
        r"""Enter a context which captures events emitted by transactions.

        :param pattern: a glob pattern string, or a regex object, to match the event name
        :return: a capture context

        The event name is in the format: ``{unitname}:{contractname}.{eventname}``

        All emitted events that match are stored within the client and can be accessed with
        ``client.get_events()``. They are cleared before every capture.

        Nested captures will filter events that match any of the patterns in the context.

        .. code-block:: python

            with client.capture("*:MyToken.Transfer"):
                my_token_instance.transfer(address, 13)

            assert client.get_events()[0].args[2] == 13

            with client.capture(re.compile(r".*:MyToken\.Transfer")):
                my_token_instance.transfer(address, 1)

            assert client.get_events()[0].args[2] == 1
        """
        return EventCaptureWithStatement(self, pattern)

    def _on_transaction(self, info: TransactionInfo):
        # reporting
        self._dump("{contract}[{address}]".format(
            contract=info.contractname,
            address=info.address))
        with self._dump.push("    "):
            self._dump("Call: {function}({fnargs}), {txargs}".format(
                function=info.function,
                fnargs=", ".join(repr(x) for x in info.fnargs),
                txargs=repr(info.txargs)))
            self._dump("Hash: 0x{txhash}".format(
                txhash=binascii.hexlify(info.txhash).decode()))
            self._dump("Cost: {gasused}".format(
                gasused=info.receipt.gasUsed))

        # read events
        for log in info.receipt.logs:
            try:
                event_signature = bytes(log.topics[0])
                key = (info.unitname, info.contractname, event_signature)
                event = self._event_map[key]
            except KeyError:
                continue
            match_friendly_name = event.unitname + ":" + event.contractname + "." + event.name
            if self._check_filters(match_friendly_name):
                decoded_log = self._decode_event_log(event, log)
                self._event_logs.append(decoded_log)

    def _decode_event_log(self, event: EventAbi, log) -> EventLog:
        data = get_event_data(event.abi, log)
        args = []
        for inp in event.abi["inputs"]:
            args.append(data["args"][inp["name"]])
        return EventLog(
            unitname=event.unitname,
            contractname=event.contractname,
            name=event.name,
            address=log["address"],
            args=args,
            data=data)

    def account(self, address):
        """Enter a context which uses a specific account to perform all transactions
        in the context.

        :param address: address of the account to use
        :return: an account context

        Contexts can be nested. In this case, the account in the last context will
        be used.

        .. code-block:: python

            with client.account(client.address(0)):
                client.deploy("ContractName", args=())
        """
        return AccountWithStatement(self, address)

    def address(self, account_id: int):
        """Get the address of an account in the ETH node

        :param account_id: index of the account in the ETH node
        :return: address of the account
        """
        try:
            return self._accounts[account_id]
        except (IndexError, KeyError):
            value_assert(False, "%s is not a valid account" % repr(account_id))

    def _push_account(self, name: Union[str, int]):
        super()._push_account(name)
        self._web3.eth.defaultAccount = self.get_current_account()

    def _pop_account(self):
        super()._pop_account()
        try:
            self._web3.eth.defaultAccount = self.get_current_account()
        except ValueError:
            self._web3.eth.defaultAccount = self._initial_default_account

    def _push_filter(self, pattern):
        if not self._event_filter_stack:
            self._event_logs = []
        super()._push_filter(pattern)

    def get_events(self) -> List[EventLog]:
        """Get events generated within the last capture context

        :return: list of event logs
        """
        return [log for log in self._event_logs]

    def clear_events(self) -> None:
        """Clear events generated within the last capture context
        """
        self._event_logs = []

    def get_current_account(self):
        """Get the account which is currently in use

        :return: address of the account in use
        """
        return self._get_account()

    def deploy(self, contract_selector: str, args=(), wrapper=ContractBase):
        """Deploy a contract

        :param contract_selector: contract selector string,
            see :py:meth:`solitude.common.ContractObjectList.select`. The contract
            must be present in the compiler's collection and must contain ABI and
            bytecode.
        :param args: constructor arguments
        :param wrapper: wrapper class for contract (see ContractBase)
        """
        account = self.get_current_account()
        compiled_contract = self._compiled.select(contract_selector)
        unitname = compiled_contract["_solitude"]["unitName"]
        contractname = compiled_contract["_solitude"]["contractName"]
        contract = self._web3.eth.contract(
            abi=compiled_contract['abi'],
            bytecode=compiled_contract['bin'])
        txhash = contract.constructor(*args).transact({"from": account})
        receipt = self._web3.eth.waitForTransactionReceipt(txhash)
        # Check whether there is any code in the deployed contract. Sometimes web3 would just produce
        #   an empty contract after unsuccessful deployment, instead of raising an exception.
        code = self._web3.eth.getCode(receipt.contractAddress)
        if (not code) or (code == bytes([0])):
            raise SetupError("Error deploying contract")
        deployed_contract = self._web3.eth.contract(
            address=receipt.contractAddress,
            abi=compiled_contract['abi'])
        return wrapper(self, unitname, contractname, deployed_contract)

    def use(self, contract_selector: str, address: str, wrapper=ContractBase):
        """Use a contract at a specific address

        :param contract_selector: contract selector string,
            see :py:meth:`solitude.common.ContractObjectList.select`. The contract
            must be present in the client's collection and must contain the ABI at
            least.
        :param args: constructor arguments
        :param account: deployer account, default is account 0
        :param wrapper: wrapper class for contract (see ContractBase)
        """
        compiled_contract = self._compiled.select(contract_selector)
        unitname = compiled_contract["_solitude"]["unitName"]
        contractname = compiled_contract["_solitude"]["contractName"]
        deployed_contract = self._web3.eth.contract(
            address=address,
            abi=compiled_contract['abi'])
        return wrapper(self, unitname, contractname, deployed_contract)

    def add_filter(self, contracts: List[ContractBase], event_names: List[str], parameters=None) -> Filter:
        """Subscribe to events occurring on the ETH node

        Creates a filter on the ETH node. Returns an object with the filter information,
        which can be used to retrieve the events or unsubscribe.

        :param contracts: list of contract instances which can generate the event. All instances
            must refer to the same contract, possibly deployed at multiple addresses.
        :param event_names: names of events to listen for
        :param parameters: additional raw topics (optional)
        :return: a Filter object
        """
        unitname = None
        contractname = None
        param_address = []

        def single_or_list(lst):
            if len(lst) == 1:
                return lst[0]
            return lst

        for contract in contracts:
            if contractname is not None and (contract.name != contractname or contract.unitname != unitname):
                raise SetupError("All contract instances must refer to the same contract")
            contractname = contract.name
            unitname = contract.unitname
            param_address.append(contract.address)
        param_events = []
        for event in self._events:
            if event.contractname == contractname and event.unitname == unitname and event.name in event_names:
                param_events.append(hex_repr(event.signature, prefix=True))
        param_topics = [single_or_list(param_events)]
        if parameters is not None:
            param_topics += parameters

        params = {
            "fromBlock": "latest",
            "toBlock": "latest",
            "address": single_or_list(param_address),
            "topics": param_topics}
        result = self._rpc.eth_newFilter(params)
        assert result.startswith("0x")
        flt = Filter(
            index=int(result[2:], 16),
            unitname=unitname,
            contractname=contractname,
            event_names=event_names,
            valid=[True])
        self._filters.append(flt)
        return flt

    def remove_filter(self, flt: Filter) -> None:
        """Unsubscribe from previously created filter.

        Clean up the filter from the ETH node.

        :param flt: a Filter object (created by :py:meth:`EthClient.add_filter`)
        """
        for i, saved_filter in enumerate(self._filters):
            if saved_filter.index == flt.index:
                del self._filters[i]
                break
        if flt.valid:
            del flt.valid[0]
        self._rpc.eth_uninstallFilter(hex(flt.index))

    def iter_filters(self, filters: List[Filter], interval=1.0):
        """Iterate over events generated by a list of filters

        :param interval: polling interval in seconds
        :return: an iterator of EventLog objects
        """
        invalid_filters = False
        while True:
            for flt in filters:
                if not flt.valid:
                    invalid_filters = True
                    continue
                logs = self._web3.eth.getFilterChanges(hex(flt.index))
                for log in logs:
                    key = (flt.unitname, flt.contractname, bytes(log["topics"][0]))
                    event = self._event_map[key]
                    decoded_log = self._decode_event_log(event, log)
                    yield decoded_log
            if invalid_filters:
                filters = [flt for flt in filters if flt.valid]
                invalid_filters = False
            if not filters:
                return
            time.sleep(interval)

    def import_raw_key(self, private_key: str, passphrase: str=""):
        with RaiseForParam("private_key"):
            value_assert(
                private_key.startswith("0x"), "must be a hex string prefixed with 0x")
        account_address = self._web3.personal.importRawKey(
            private_key, passphrase)
        if account_address not in self._accounts:
            self._accounts.append(account_address)

    def unlock_account(self, address: str, passphrase: str="", unlock_duration: int=300):
        self._web3.personal.unlockAccount(address, passphrase, unlock_duration)

    def miner_start(self, num_threads: int):
        self._web3.miner.start(num_threads)


class BatchCaller:
    """Utility to batch function call requests to the ETH node
    """
    def __init__(self, client: ETHClient):
        """Create a BatchCaller

        :param client: an ETH client
        """
        self.client = client
        self._data = []  # type: List[tuple]
        self._calls = []  # type: List[tuple]

    def add_call(self, contract: ContractBase, func: str, args=()) -> None:
        """Add a function call to the batch call

        :param contract: a contract object (from :py:meth:`EthClient.deploy` or :py:meth:`EthClient.use`).
        :param func: function name
        :param args: function arguments
        """
        contract_function = getattr(contract._contract.functions, func)(*args)
        self._data.append(("eth_call", [contract_function.buildTransaction()]))
        self._calls.append((contract, contract_function))

    def execute(self) -> list:
        """Execute the call batch

        :return: a list containing the result from each function call, in the same order
            in which they were added.
        """
        out = []
        results = self.client.rpc.batch_call(self._data)
        for (contract, contract_function), result in zip(self._calls, results):
            output_types = web3.contract.get_abi_output_types(contract_function.abi)
            output_data = web3.contract.decode_abi(output_types, binascii.unhexlify(result[2:]))
            normalizers = itertools.chain(
                web3.contract.BASE_RETURN_NORMALIZERS,
                contract_function._return_data_normalizers)
            normalized_data = tuple(web3.contract.map_abi_data(normalizers, output_types, output_data))
            if len(normalized_data) > 1:
                out.append(normalized_data)
            else:
                out.append(normalized_data[0])
        return out
