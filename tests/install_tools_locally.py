from solitude.tools import Solc, GanacheCli, Solium
from conftest import (
    SOLIDITY_ALL_VERSIONS, GANACHE_ALL_VERSIONS, SOLIUM_ALL_VERSIONS, LOCAL_TOOLDIR)


def main():
    TOOLS = [
        (Solc, SOLIDITY_ALL_VERSIONS),
        (GanacheCli, GANACHE_ALL_VERSIONS),
        (Solium, SOLIUM_ALL_VERSIONS)
    ]
    for tool_class, tool_versions in TOOLS:
        for version in tool_versions:
            tool = tool_class(tooldir=LOCAL_TOOLDIR, version=version)
            if tool.have():
                print("Found %s-%s" % (tool.name, tool.version))
            else:
                print("Installing %s-%s... " % (tool.name, tool.version), end="", flush=True)
                tool.add()
                print("OK")


if __name__ == "__main__":
    main()
