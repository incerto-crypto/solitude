# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
from solitude._internal.config_util import (
    parse_port_range, parse_server_account, parse_path)
from solitude.errors import SetupError
from solitude.tools import (  # noqa
    Tool, GanacheCli, Solc, Solium)
from solitude.client import ETHClient
from solitude.common import ContractObjectList
from solitude.compiler import Compiler, Linter
from solitude.server import RPCTestServer
from solitude.common.dump import Dump, unique_dumpname


class Factory:
    """Create a Factory object

    The Factory object can be used to create pre-configured objects from a
    solitude configuration dictionary.

    :param cfg: solitude configuration dictionary
    """
    def __init__(self, cfg):
        self._cfg = cfg
        self._tools = {k: None for k in self._cfg["Tools.Required"]}
        tooldir = parse_path(self._cfg["Tools.Directory"])
        if not os.path.isdir(tooldir):
            raise SetupError("Directory Tools.Directory ('%s') not found" % tooldir)
        if "Solc" in self._tools:
            tool = Solc(tooldir, version=self._cfg["Tools.Solc.Version"])
            if tool.have():
                self._tools["Solc"] = tool
        if "GanacheCli" in self._tools:
            tool = GanacheCli(tooldir, self._cfg["Tools.GanacheCli.Version"])
            if tool.have():
                self._tools["GanacheCli"] = tool
        if "Solium" in self._tools:
            tool = Solium(tooldir, self._cfg["Tools.Solium.Version"])
            if tool.have():
                self._tools["Solium"] = tool
        for tool_name, tool in self._tools.items():
            if tool is None:
                raise SetupError("Tool not found: '%s'" % tool_name)

    def create_compiler(self, add_contract_dir=False) -> Compiler:
        """Create a Compiler object, used to compile contracts with solc.

        :param add_contract_dir: whether to load contracts from the directory
            specified in Compiler.ContractDir or not
        """
        if "Solc" not in self._tools:
            raise SetupError("Tool 'Solc' not configured")
        compiler = Compiler(
            executable=self._tools["Solc"].get("solc"),
            optimize=self._cfg["Compiler.Optimize"])
        if add_contract_dir and self._cfg["Compiler.ContractDir"]:
            compiler.add_directory(self._cfg["Compiler.ContractDir"])
        return compiler

    def create_server(self) -> RPCTestServer:
        """Create a RPCTestServer object, used to start a ganache test node.
        """
        if "Solc" not in self._tools:
            raise SetupError("Tool 'GanacheCli' not configured")
        return RPCTestServer(
            executable=self._tools["GanacheCli"].get("ganache-cli"),
            port=parse_port_range(self._cfg["Server.Port"]),
            host=self._cfg["Server.Host"],
            gasprice=self._cfg["Server.GasPrice"],
            gaslimit=self._cfg["Server.GasLimit"],
            accounts=[parse_server_account(account) for account in self._cfg["Server.Accounts"]])

    def create_client(self, endpoint=None) -> ETHClient:
        """Create a ETHClient object, used to interact with an ethereum node.

        :param endpoint: if set, it overrides the Client.Endpoint setting in the configuration
        """
        if endpoint is None:
            endpoint = self._cfg["Client.Endpoint"]
        compiled = ContractObjectList()
        contract_build_dir = parse_path(self._cfg["Client.ContractBuildDir"])
        if contract_build_dir is not None:
            compiled.add_directory(contract_build_dir)
        dump = None
        if self._cfg["Client.EnableGasLog"]:
            dump_filename = unique_dumpname(
                parse_path(self._cfg["Client.GasLogDir"]),
                "gas")
            dump = Dump(dump_filename)
        client = ETHClient(endpoint=endpoint, compiled=compiled, dump=dump)
        client.set_default_gas(self._cfg["Client.DefaultGas"])
        for name, account_num in self._cfg["Client.AccountAliases"].items():
            client.set_account_alias(name, account_num)
        return client

    def create_linter(self, add_contract_dir=False) -> Linter:
        """Create a Linter object, used to invoke solium.

        :param add_contract_dir: whether to load contracts from the directory
            specified in Compiler.ContractDir or not
        """
        if "Solium" not in self._tools:
            raise SetupError("Tool 'Solium' not configured")
        linter = Linter(
            executable=self._tools["Solium"].get("solium"),
            plugins=self._cfg["Compiler.Lint.Plugins"],
            rules=self._cfg["Compiler.Lint.Rules"])
        if add_contract_dir and self._cfg["Compiler.ContractDir"]:
            linter.add_directory(self._cfg["Compiler.ContractDir"])
        return linter

    def have_tool(self, name: str) -> bool:
        """Check if a tool is installed

        :param name: name of the tool
        """
        return name in self._tools
