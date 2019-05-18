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
import re

import requests
from zipfile import ZipFile

from solitude._internal import internal_assert
from solitude._internal.os_compat import (
    append_executable_extension, set_executable_flag, is_valid_path)
from solitude.common.resource_util import get_resource_path, get_global_config, copy_from_url


class Tool:
    """An external tool that can be installed on the local filesystem and used
    """
    def __init__(self, tooldir: str, name: str, version: str):
        self._tooldir = tooldir
        self._name = name
        self._version = version
        internal_assert(
            is_valid_path(name + version),
            "tool name or version includes characters that cannot be used in a path")
        self._provided_modules = {}  # type: Dict[str, str]

    def add(self):
        """Install the tool into the tools directory
        """
        raise NotImplementedError()

    def remove(self):
        """Remove (delete) the tool from the tools directory
        """
        raise NotImplementedError()

    def have(self) -> bool:
        """Check if the tool is present in the tools directory
        """
        raise NotImplementedError()

    def get(self, key: str) -> str:
        """Get a module from the tool

        :param key: a string key (name) associated with the module, usually
            the name of the file.
        :return: the filesystem path of the module location
        """
        raise NotImplementedError()

    def _provide(self, key: str, path: str) -> None:
        """Add a module (key, path) to the list of the modules provided by this
        tool.

        :param key: a key (name) associated to the module
        """
        self._provided_modules[key] = path

    @property
    def provided(self) -> Dict[str, str]:
        """Get the provided modules

        :return: dict of (key -> path) of all modules provided by the tool
        """
        return copy.copy(self._provided_modules)

    @property
    def name(self) -> str:
        """Tool name"""
        return self._name

    @property
    def version(self) -> str:
        """Tool version string"""
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
    """Template for creating tools from npm packages
    """
    def __init__(
            self,
            tooldir: str,
            name: str,
            version: str,
            provides: str,
            package: str,
            executable: str,
            lockfile: Optional[str]):

        super().__init__(tooldir, name, version)
        name_version = "%s-%s" % (self._name, self._version)
        self._package = package
        self._location = os.path.join(self._tooldir, name_version)
        self._lockfile = lockfile
        self._executable_path = os.path.join(
            self._location, "node_modules", ".bin", append_executable_extension(executable, winext="cmd"))
        self._provided_service = provides
        self._provide(provides, self._executable_path)

    def add(self):
        try:
            os.makedirs(self._location, exist_ok=True)
            if self._lockfile is not None:
                lockfile_dest = os.path.join(self._location, "package-lock.json")
                copy_from_url(self._lockfile, lockfile_dest)
                internal_assert(
                    os.path.isfile(lockfile_dest),
                    "LockFile could not be copied")
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
            raise CommunicationError(str(e)) from e

    def remove(self):
        shutil.rmtree(self._location)

    def have(self):
        return os.path.isfile(self._executable_path)

    def get(self, key: str):
        assert(key == self._provided_service)
        return self._executable_path


class ToolDownloadTemplate(Tool):
    """Template for creating tools from a downloadable executable or zipped executable
    """
    def __init__(self, tooldir: str, name: str, version: str, provides: str, url: str, executable: str, unzip: bool):
        super().__init__(tooldir, name, version)
        name_version = "%s-%s" % (self._name, self._version)
        self._url = url
        self._location = os.path.join(self._tooldir, name_version)
        self._executable_path = os.path.join(self._location, executable)
        self._provided_service = provides
        self._provide(provides, self._executable_path)
        self._unzip = unzip

    def add(self):
        try:
            dest = os.path.dirname(self._executable_path)
            os.makedirs(dest, exist_ok=True)
            if self._unzip:
                # download zip file and extract
                zip_path = os.path.join(self._location, "tool.zip")
                copy_from_url(self._url, zip_path)
                with ZipFile(zip_path) as z:
                    z.extractall(path=dest)
                internal_assert(
                    os.path.isfile(self._executable_path),
                    "Executable not found: archive file may have changed on the server")
                set_executable_flag(self._executable_path)
            else:
                # download executable
                copy_from_url(self._url, self._executable_path)
                set_executable_flag(self._executable_path)
        except (OSError, FileNotFoundError) as e:
            raise CommunicationError(str(e)) from e

    def remove(self):
        shutil.rmtree(self._location)

    def have(self):
        return os.path.isfile(self._executable_path)

    def get(self, key: str):
        internal_assert(
            key == self._provided_service,
            "This tool does not provide the requested service")
        return self._executable_path
