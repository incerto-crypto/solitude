# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import requests
import sys
import os
import stat
import shutil
from zipfile import ZipFile
from solitude.tools.base import Tool, ToolNpmTemplate, append_executable_extension
from solitude._internal.resource_util import get_resource_path


class SolcEmscripten(ToolNpmTemplate):
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
        try:
            solcjs_standard_json = get_resource_path("solcjs_standard_json")
            executable_real_path = os.path.realpath(self._executable_path)
            shutil.copy(solcjs_standard_json, executable_real_path)
            st = os.stat(executable_real_path)
            os.chmod(executable_real_path, st.st_mode | stat.S_IEXEC)
        except (OSError, FileNotFoundError) as e:
            raise InstallError from e


class SolcNative(Tool):
    def __init__(self, tooldir: str, version: str):
        super().__init__(tooldir, "Solc", version)
        name_version = "%s-%s" % (self._name, self._version)
        assert(os.pathsep not in name_version)
        self._toolname = "solc"
        self._location = os.path.join(self._tooldir, name_version)
        self._executable_path = os.path.join(
            self._location, "bin", append_executable_extension("solc", winext="exe"))
        self._provide(self._toolname, self._executable_path)

    def add(self):
        if sys.platform.startswith("linux"):
            self._add_linux()
        elif sys.platform == "win32":
            self._add_win32()
        else:
            raise Exception("Unsupported Platform: %s" % sys.platform)

    def remove(self):
        shutil.rmtree(self._location)

    def have(self):
        return os.path.isfile(self._executable_path)

    def get(self, key: str):
        assert(key == self._toolname)
        return self._executable_path

    def _add_linux(self):
        url = (
            "https://github.com/ethereum/solidity" +
            "/releases/download/v%s/solc-static-linux") % self._version
        os.makedirs(os.path.dirname(self._executable_path), exist_ok=True)
        Solc._download_file(url, self._executable_path)
        assert(os.path.isfile(self._executable_path))
        st = os.stat(self._executable_path)
        os.chmod(self._executable_path, st.st_mode | stat.S_IEXEC)

    def _add_win32(self):
        url = (
            "https://github.com/ethereum/solidity" +
            "/releases/download/v%s/solidity-windows.zip") % self._version
        exe_dirname = os.path.dirname(self._executable_path)
        os.makedirs(exe_dirname, exist_ok=True)
        zip_path = os.path.join(self._location, "package.zip")
        Solc._download_file(url, zip_path)
        with ZipFile(zip_path) as z:
            z.extractall(path=exe_dirname)
        assert(os.path.isfile(self._executable_path))

    @staticmethod
    def _download_file(url, destination):
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(destination, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)


if sys.platform == "darwin":
    Solc = SolcEmscripten
else:
    # Solc = SolcEmscripten
    Solc = SolcNative
