# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from solitude.tools.base import ToolNpmTemplate


class GanacheCli(ToolNpmTemplate):
    def __init__(self, tooldir: str, version: str):
        super().__init__(
            tooldir=tooldir,
            name="GanacheCli",
            version=version,
            provides="ganache-cli",
            package="ganache-cli",
            executable="ganache-cli")
