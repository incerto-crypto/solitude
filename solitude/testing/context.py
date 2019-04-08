# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Mapping, Union, Optional  # noqa
import os
import shutil
import tempfile
from collections import OrderedDict

from solitude.server import RPCTestServer, kill_all_servers  # noqa
from solitude.client import ContractBase, ETHClient, EventLog  # noqa
from solitude.compiler import Compiler  # noqa
from solitude import Factory, read_config_file


class TestingContext:
    def __init__(self, cfg: dict, tmpdir=None):
        self._cfg = cfg
        self._factory = Factory(self._cfg)

        self.client = None  # type: ETHClient
        self.server = None  # type: RPCTestServer
        self.compiler = None  # type: Compiler
        self._tmpdir = tmpdir
        self._server_started = False

        endpoint = None

        if self._factory.have_tool("Solc"):
            self.compiler = self._factory.create_compiler()

        if self._factory.have_tool("GanacheCli"):
            self.server = self._factory.create_server()
            if self._cfg["Testing.StartServer"]:
                self.server.start()
                self._server_started = True
                # ovverride endpoint for client
                endpoint = self.server.endpoint

        self.client = self._factory.create_client(
            endpoint=endpoint)

    @property
    def cfg(self):
        return self._cfg

    @property
    def tmpdir(self):
        if self._tmpdir is None:
            self._tmpdir = tempfile.mkdtemp()
        return self._tmpdir

    def teardown(self):
        if self._server_started:
            self.server.stop()
        if self._tmpdir is not None:
            shutil.rmtree(self._tmpdir)

    def account(self, name: Union[str, int]):
        return self.client.account(name)

    def address(self, name: Union[str, int]):
        return self.client.address(name)

    def deploy(self, contract_selector: str, args=(), wrapper=ContractBase):
        return self.client.deploy(contract_selector, args, wrapper)

    def capture(self, pattern):  # noqa
        return self.client.capture(pattern)

    def set_account_alias(self, name: str, account_num: int):
        return self.client.set_account_alias(name, account_num)

    def get_accounts(self):
        return self.client.get_accounts()

    def get_events(self):
        return self.client.get_events()

    def clear_events(self):
        return self.client.clear_events()

    def get_current_account(self):
        return self.client.get_current_account()

    @property
    def rpc(self):
        return self.client.rpc

    @property
    def web3(self):
        return self.client.web3

    def mine_block(self) -> None:
        return self.client.mine_block()

    def increase_blocktime_offset(self, seconds: int) -> int:
        return self.client.increase_blocktime_offset(seconds)

    def get_last_blocktime(self) -> int:
        return self.client.get_last_blocktime()


SOL = TestingContext


def SOL_new(cfg: Union[dict, OrderedDict, str]="solitude.yaml", relative_to: Optional[str]=None, tmpdir=None) -> SOL:
    if isinstance(cfg, str):
        path = cfg
        if relative_to is not None:
            rel_dir = os.path.dirname(
                os.path.abspath(relative_to))
            path = os.path.join(rel_dir, path)
        cfg_dict = read_config_file(path)
    elif isinstance(cfg, dict):
        cfg_dict = cfg
    else:
        raise TypeError("cfg is not dict or str")
    try:
        return SOL(cfg_dict, tmpdir=tmpdir)
    except Exception:
        kill_all_servers()
        raise
