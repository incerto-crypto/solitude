# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Optional, Dict  # noqa
import os
import copy
import subprocess
import shutil
import sys
import json
from solitude.errors import InstallError


def append_executable_extension(filename, winext="cmd"):
    if sys.platform == "win32":
        return filename + "." + winext
    return filename


class Tool:
    def __init__(self, tooldir: str, name: str, version: str):
        self._tooldir = tooldir
        self._name = name
        self._version = version
        self._provided_modules = {}  # type: Dict[str, str]

    def add(self):
        raise NotImplementedError()

    def remove(self):
        raise NotImplementedError()

    def have(self) -> bool:
        raise NotImplementedError()

    def get(self, key: str) -> str:
        raise NotImplementedError()

    def _provide(self, name: str, path: str):
        self._provided_modules[name] = path

    @property
    def provided(self):
        return copy.copy(self._provided_modules)

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version


def make_package_json(name, packages: dict):
    return {
        "name": name + "-solitude-env",
        "version": "1.0.0",
        "description": "Solitude environment",
        "main": "index.js",
        "scripts": {
            "test": "echo \"Error: no test specified\" && exit 1"
        },
        "author": "",
        "license": "ISC",
        "dependencies": {
            k: ("%s" % v) for (k, v) in packages.items()
        }
    }


class ToolNpmTemplate(Tool):
    def __init__(self, tooldir: str, name: str, version: str, provides: str, package: str, executable: str):
        super().__init__(tooldir, name, version)
        self._package = package
        name_version = "%s-%s" % (self._name, self._version)
        assert(os.pathsep not in name_version)
        self._location = os.path.join(self._tooldir, name_version)
        self._lockfile = None
        # TODO implement for npm lockfiles
        # self._lockfile = get_resource_path("tools.%s.lock" % name_version)
        # if not os.path.isfile(self._lockfile):
        #    self._lockfile = None
        self._executable_path = os.path.join(
            self._location, "node_modules", ".bin", append_executable_extension(executable))
        self._provided_service = provides
        self._provide(provides, self._executable_path)

    def add(self):
        try:
            os.makedirs(self._location, exist_ok=True)
            # TODO implement for npm lockfiles
            # if self._lockfile is not None:
            #    lockfile_dest = os.path.join(self._location, "yarn.lock")
            #    shutil.copyfile(self._lockfile, lockfile_dest)
            #    assert(os.path.isfile(lockfile_dest))
            with open(os.path.join(self._location, "package.json"), "w") as fp:
                packages = {
                    self._package: self._version
                }
                json.dump(make_package_json(self._name, packages), fp)
            cmd = ["npm", "install"]
            is_windows = (sys.platform == "win32")
            subprocess.check_call(
                cmd,
                cwd=self._location,
                shell=is_windows)
        except (OSError, FileNotFoundError) as e:
            raise InstallError from e

    def remove(self):
        shutil.rmtree(self._location)

    def have(self):
        return os.path.isfile(self._executable_path)

    def get(self, key: str):
        assert(key == self._provided_service)
        return self._executable_path