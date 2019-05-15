# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Mapping, Union, Optional  # noqa
import os
import shutil
import tempfile
from functools import wraps
from collections import OrderedDict

from solitude._internal.error_util import type_assert, RaiseForParam
from solitude.server import ETHTestServer, kill_all_servers  # noqa
from solitude.client import ContractBase, ETHClient, EventLog  # noqa
from solitude.common import ContractObjectList
from solitude.compiler import Compiler  # noqa
from solitude import Factory, read_config_file


class TestingContext:
    def __init__(self, cfg: dict):
        """Create a testing context containing configured instances of the client,
        server and compiler.

        Contracts from Project.ObjectDir (if not null) are added to the client's collection.

        A server is started if Testing.RunServer is true. In this case, the client is
        connected to the new server endpoint address, whatever it is, overriding the client
        endpoint configuration.

        :param cfg: configuration dictionary
        """
        self._cfg = cfg
        self._factory = Factory(self._cfg)

        self._client = None  # type: ETHClient
        self._server = None  # type: ETHTestServer
        self._compiler = None  # type: Compiler
        self._server_started = False

        endpoint = None

        project_tools = self._factory.get_required()
        if "Solc" in project_tools:
            self._compiler = self._factory.create_compiler()

        if "GanacheCli" in project_tools:
            self._server = self._factory.create_server()
            if self._cfg["Testing.RunServer"]:
                self._server.start()
                self._server_started = True
                # ovverride endpoint for client
                endpoint = self._server.endpoint

        self._client = self._factory.create_client(
            endpoint=endpoint)

        object_dir = self._cfg["Project.ObjectDir"]
        if object_dir is not None:
            objects = ContractObjectList()
            objects.add_directory(object_dir)
            self._client.update_contracts(objects)

    @property
    def cfg(self):
        """Configuration"""
        return self._cfg

    @property
    def client(self):
        """Client instance"""
        return self._client

    @property
    def server(self):
        """Server instance"""
        return self._server

    @property
    def compiler(self):
        """Compiler instance"""
        return self._compiler

    def teardown(self):
        """Teardown the testing context, terminating the test server if any."""
        if self._server_started:
            self._server.stop()

    @wraps(ETHClient.account)
    def account(self, address):
        return self._client.account(name)

    @wraps(ETHClient.address)
    def address(self, account_id: int):
        return self._client.address(name)

    @wraps(ETHClient.deploy)
    def deploy(self, contract_selector: str, args=(), wrapper=ContractBase):
        return self._client.deploy(contract_selector, args, wrapper)

    @wraps(ETHClient.capture)
    def capture(self, pattern):  # noqa
        return self._client.capture(pattern)

    @wraps(ETHClient.get_accounts)
    def get_accounts(self, reload=False) -> list:
        return self._client.get_accounts()

    @wraps(ETHClient.get_events)
    def get_events(self):
        return self._client.get_events()

    @wraps(ETHClient.clear_events)
    def clear_events(self):
        return self._client.clear_events()

    @wraps(ETHClient.get_current_account)
    def get_current_account(self):
        return self._client.get_current_account()

    @wraps(ETHClient.mine_block)
    def mine_block(self) -> None:
        return self._client.mine_block()

    @wraps(ETHClient.increase_blocktime_offset)
    def increase_blocktime_offset(self, seconds: int) -> int:
        return self._client.increase_blocktime_offset(seconds)

    @wraps(ETHClient.get_last_blocktime)
    def get_last_blocktime(self) -> int:
        return self._client.get_last_blocktime()


def SOL_new(
        cfg: Union[dict, str]="solitude.yaml",
        relative_to: Optional[str]=None) -> TestingContext:
    """Create a new testing context

    :param cfg: configuration dictionary or path. If `cfg` is a string, it is interpreted
        as a path to the yaml or json file containing the configuration dictionary.
    :param relative_to: a path, or None; if `cfg` is a path and `relative_to` is not None,
        make the path of the configuration file `cfg` relative to the parent directory of
        `relative_to`. This can be used with `__file__` to make the configuration file
        location relative to the test script.
    """
    with RaiseForParam("cfg"):
        type_assert(cfg, (dict, OrderedDict))

    if isinstance(cfg, str):
        path = cfg
        if relative_to is not None:
            rel_dir = os.path.dirname(
                os.path.abspath(relative_to))
            path = os.path.join(rel_dir, path)
        cfg_dict = read_config_file(path)
    else:
        cfg_dict = cfg

    try:
        return TestingContext(cfg_dict)
    except Exception:
        kill_all_servers()
