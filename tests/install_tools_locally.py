import argparse
from solitude.tools import Solc, GanacheCli, EthLint
from solitude.common import update_global_config
from conftest import (
    SOLIDITY_ALL_VERSIONS, GANACHE_ALL_VERSIONS, ETHLINT_ALL_VERSIONS, LOCAL_TOOLDIR)


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--nolocks",
        action="store_true",
        help="Do not use lockfiles in the global config")
    args = p.parse_args()

    if args.nolocks:
        update_global_config({
            "GanacheCli.PackageLock": None,
            "EthLint.PackageLock": None
        })

    TOOLS = [
        (Solc, SOLIDITY_ALL_VERSIONS),
        (GanacheCli, GANACHE_ALL_VERSIONS),
        (EthLint, ETHLINT_ALL_VERSIONS)
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
