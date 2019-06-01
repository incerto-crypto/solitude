# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import sys
import re
import datetime
import json
from collections import OrderedDict


def path_to_unitname(path: str) -> str:
    """Create a source unit name from a path

    :param path: source file path
    :return: the corresponding normalized source unit name
    """
    # solc does not accept r"\" in source unit names
    # C:\path\to\file.sol -> /C/path/to/file.sol
    if sys.platform == "win32":
        path = path.replace("\\", "/")
        if path[1] == ":":
            path = "/" + path[0] + path[2:]
        return path
    return path


def convert_contract_truffle_to_solitude(x) -> dict:
    unitname = path_to_unitname(x["sourcePath"])
    contractname = x["contractName"]
    try:
        # TODO support more variants of ISO timestamp
        timestamp = datetime.datetime.strptime(
            x["updatedAt"],
            "%Y-%m-%dT%H:%M:%S.%f%z").isoformat()
    except ValueError:
        timestamp = datetime.datetime.utcnow().isoformat()

    metadata = json.loads(x["metadata"], object_pairs_hook=OrderedDict)
    source_list = [path_to_unitname(key) for key in metadata["sources"]]

    contract = {}
    contract["abi"] = x["abi"]
    contract["bin"] = x["bytecode"][2:]
    contract["srcmap"] = x["sourceMap"]
    contract["bin-runtime"] = x["deployedBytecode"][2:]
    contract["srcmap-runtime"] = x["deployedSourceMap"]
    contract["_solitude"] = {
        "ast": x["ast"],
        "unitName": unitname,
        "contractName": contractname,
        "sourceList": [],
        "sourcePath": x["sourcePath"],
        "source": x["source"],
        "timestamp": timestamp
    }
    return contract
