# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import sys
import os
import shutil

from solitude.tools.base import (
    Tool, ToolNpmTemplate, ToolDownloadTemplate)
from solitude.common.resource_util import get_resource_path, get_global_config
from solitude._internal.os_compat import (
    append_executable_extension, set_executable_flag, get_platform, Platform)
from solitude.common.errors import CommunicationError


class SolcEmscripten(ToolNpmTemplate):
    """Emscripten version of the solitude compiler
    """
    def __init__(self, tooldir: str, version: str):
        super().__init__(
            tooldir=tooldir,
            name="Solc",
            version=version,
            provides="solc",
            package="solc",
            executable="solcjs")

    def add(self):
        super().add()
        # The solc launch script is patched to fix stdin handling with node 11.
        # However this is still broken in node < 11 for large inputs.
        try:
            solcjs_standard_json = get_resource_path("solcjs_standard_json")
            executable_real_path = os.path.realpath(self._executable_path)
            shutil.copy(solcjs_standard_json, executable_real_path)
            set_executable_flag(executable_real_path)
        except (OSError, FileNotFoundError) as e:
            raise CommunicationError(str(e)) from e


class SolcNativeWindows(ToolDownloadTemplate):
    def __init__(self, tooldir: str, version: str):
        url = get_global_config()["Solc.URL.Windows"].format(version=version)
        super().__init__(
            tooldir=tooldir,
            name="Solc",
            version=version,
            provides="solc",
            url=url,
            executable="solc.exe",
            unzip=url.endswith(".zip"))


class SolcNativeLinux(ToolDownloadTemplate):
    def __init__(self, tooldir: str, version: str):
        url = get_global_config()["Solc.URL.Linux"].format(version=version)
        super().__init__(
            tooldir=tooldir,
            name="Solc",
            version=version,
            provides="solc",
            url=url,
            executable="solc",
            unzip=url.endswith(".zip"))


class SolcNativeDarwin(ToolDownloadTemplate):
    def __init__(self, tooldir: str, version: str):
        url = get_global_config()["Solc.URL.Darwin"].format(version=version)
        super().__init__(
            tooldir=tooldir,
            name="Solc",
            version=version,
            provides="solc",
            url=url,
            executable="solc",
            unzip=url.endswith(".zip"))


_platform = get_platform()
if _platform == Platform.LINUX:
    Solc = SolcNativeLinux
elif _platform == Platform.WINDOWS:
    Solc = SolcNativeWindows
elif _platform == Platform.DARWIN:
    Solc = SolcNativeDarwin
else:
    Solc = SolcEmscripten
