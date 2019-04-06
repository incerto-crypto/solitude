# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude.tools.base import ToolNpmTemplate
from solitude._internal import get_global_config


class Solium(ToolNpmTemplate):
    def __init__(self, tooldir: str, version: str):
        lockfile = get_global_config()["Solium.PackageLock"]
        if lockfile is not None:
            lockfile = lockfile.format(version=version)
        super().__init__(
            tooldir=tooldir,
            name="Solium",
            version=version,
            provides="solium",
            package="solium",
            executable="solium",
            lockfile=lockfile)
