# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude.errors import CLIError
from solitude.tools import Solc, Solium, GanacheCli


def _iter_required_tools(cfg):
    required = cfg["Tools.Required"]  # type: List[str]
    tooldir = os.path.expanduser(cfg["Tools.Directory"])
    if "Solc" in required:
        yield Solc(tooldir, cfg["Tools.Solc.Version"])
    if "GanacheCli" in required:
        yield GanacheCli(tooldir, cfg["Tools.GanacheCli.Version"])
    if "Solium" in required:
        yield Solium(tooldir, cfg["Tools.Solium.Version"])


def _install_if_not_have(tool):
    if tool.have():
        print("Found %s %s" % (tool.name, tool.version))
    else:
        print("Installing %s %s" % (tool.name, tool.version))
        tool.add()
        print("Installed %s" % tool.name)


def _check_have(tool):
    if not tool.have():
        raise CLIError(
            "Tool not installed: %s %s. To install all required tools, run:\n    solitude install" % (
                tool.name, tool.version))


def _require_tool(cfg, name):
    for tool in _iter_required_tools(cfg):
        if tool.name == name:
            if not tool.have():
                break
            return tool
    raise CLIError("This function requires a tool which is not installed: %s" % name)


def main():
    cfg = read_config_file(args.config)
    for tool in _iter_required_tools(cfg):
        _install_if_not_have(tool)
