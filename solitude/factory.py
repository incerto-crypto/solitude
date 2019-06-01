# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude.common.config_util import (
    parse_server_account, parse_path)
from solitude.errors import SetupError


class ToolsManager:
    def __init__(self, cfg: dict):
        from solitude.tools import Tool, GanacheCli, Solc, EthLint
        self._cfg = cfg
        self._tooldir = parse_path(self._cfg["Tools.Directory"])
        self._tools = {tool_name: None for tool_name in self._cfg["Tools.Required"]}

        self._create_tool_if_required(
            "Solc", Solc, "Tools.Solc.Version")
        self._create_tool_if_required(
            "GanacheCli", GanacheCli, "Tools.GanacheCli.Version")
        self._create_tool_if_required(
            "EthLint", EthLint, "Tools.EthLint.Version")

    def _create_tool_if_required(self, tool_name, tool_class, tool_version_field):
        if tool_name in self._tools:
            tool_version = self._cfg[tool_version_field]
            tool = tool_class(self._tooldir, version=tool_version)
            if not tool.have():
                raise SetupError(
                    "Tool '%s-%s' is required but not installed. Run 'solitude install'" % (
                        tool_name, tool_version))
            self._tools[tool_name] = tool

    def get(self, tool_name):
        try:
            return self._tools[tool_name]
        except KeyError:
            raise SetupError(
                "Tool '%s' is not in the requirements for this project" % tool_name)

    def get_required(self):
        return list(self._tools)

    def have(self, name):
        return name in self._tools


class Factory:
    """Create a Factory object

    The Factory object can be used to create pre-configured objects from a
    solitude configuration dictionary.

    :param cfg: solitude configuration dictionary
    """
    def __init__(self, cfg):
        self._cfg = cfg
        self._tools = ToolsManager(cfg)

    def create_compiler(self) -> "Compiler":
        from solitude.compiler import Compiler
        """Create a Compiler object, used to compile contracts with solc.

        :param add_contract_dir: whether to load contracts from the directory
            specified in Compiler.ContractDir or not
        """
        compiler = Compiler(
            executable=self._tools.get("Solc").get("solc"),
            optimize=self._cfg["Compiler.Optimize"])
        return compiler

    def create_server(self) -> "ETHTestServer":
        """Create a ETHTestServer object, used to start a ganache test node.
        """
        from solitude.server import ETHTestServer
        return ETHTestServer(
            executable=self._tools.get("GanacheCli").get("ganache-cli"),
            port=self._cfg["Server.Port"],
            host=self._cfg["Server.Host"],
            gasprice=self._cfg["Server.GasPrice"],
            gaslimit=self._cfg["Server.GasLimit"],
            accounts=[parse_server_account(account) for account in self._cfg["Server.Accounts"]])

    def create_client(self, endpoint=None) -> "ETHClient":
        """Create a ETHClient object, used to interact with an ethereum node.

        :param endpoint: if set, it overrides the Client.Endpoint setting in the configuration
        """
        from solitude.client import ETHClient
        if endpoint is None:
            endpoint = self._cfg["Client.Endpoint"]
        client = ETHClient(endpoint=endpoint)
        client.set_default_gaslimit(self._cfg["Client.GasLimit"])
        client.set_default_gasprice(self._cfg["Client.GasPrice"])
        return client

    def create_linter(self, add_contract_dir=False) -> "Linter":
        """Create a Linter object, used to invoke solium.

        :param add_contract_dir: whether to load contracts from the directory
            specified in Compiler.ContractDir or not
        """
        from solitude.linter import Linter
        linter = Linter(
            executable=self._tools.get("EthLint").get("solium"),
            plugins=self._cfg["Linter.Plugins"],
            rules=self._cfg["Linter.Rules"])
        return linter

    def get_sourcelist(self) -> "ContractSourceList":
        from solitude.common.contract_sourcelist import ContractSourceList
        source_dir = self._cfg["Project.SourceDir"]
        sources = ContractSourceList()
        if source_dir is not None:
            sources.add_directory(source_dir)
        return sources

    def get_objectlist(self) -> "ContractObjectList":
        from solitude.common.contract_objectlist import ContractObjectList
        object_dir = self._cfg["Project.ObjectDir"]
        object_dir_type = self._cfg["Project.ObjectDirType"]
        objects = ContractObjectList()
        if object_dir is not None:
            objects.add_directory(object_dir, buildtype=object_dir_type)
        return objects

    def get_project_name(self):
        return self._cfg["Project.Name"]

    def get_required(self):
        return self._tools.get_required()
