# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import sys


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
