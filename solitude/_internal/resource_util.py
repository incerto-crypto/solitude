# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os
import json
import shutil
import io
import requests
import contextlib
from solitude._internal import RaiseForParam, type_assert, EnumType, value_assert


def get_resource_path(resource_name):
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "resources",
        resource_name)


class Schema(EnumType):
    HTTPS = "https://"
    HTTP = "http://"
    RESOURCE = "resource://"
    FILE = "file://"


def _parse_url(url):
    for schema in Schema.iter_values():
        if url.startswith(schema):
            return (schema, url[len(schema):])
    return (Schema.FILE, url)


def _copy_fileobj_to_destination(source, destination):
    with contextlib.ExitStack() as stack:
        if isinstance(destination, str):
            fp = stack.enter_context(open(destination, "wb"))
        elif hasattr(destination, "write"):
            fp = destination
        else:
            internal_assert(
                False, "destination must be either a path or file-like")
        shutil.copyfileobj(source, fp)


def _url_to_fileobj(url: str):
    schema, path = _parse_url(url)
    if schema in (Schema.HTTP, Schema.HTTPS):
        r = requests.get(url, stream=True)
        r.raise_for_status()
        r.raw.decode_content = True
        yield r.raw
    elif schema == Schema.FILE:
        with open(path, "rb") as fp:
            yield fp
    elif schema == Schema.RESOURCE:
        with open(get_resource_path(path), "rb") as fp:
            yield fp
    else:
        value_assert(False, "Schema not recognized for URL: %s" % url)


def copy_from_url(url: str, destination):
    source = _url_to_fileobj(url)
    _copy_fileobj_to_destination(next(source), destination)
    _ = list(source)


class _GlobalConfig:
    def __init__(self):
        with open(get_resource_path("global_config.json"), "r") as fp:
            self._config = json.load(fp)

    def update(self, config: dict):
        self._config.update(config)

    def get(self):
        return self._config


def _DEBUG_SolcEmscripten(enable):
    from solitude.tools import solc
    with RaiseForParam("enable_emscripten"):
        type_assert(enable_emscripten, bool)
    solc.Solc = solc.SolcEmscripten


_global_config = _GlobalConfig()
_debug_hooks = {
    "SolcEmscripten": _DEBUG_SolcEmscripten
}


def update_global_config(config: dict):
    _global_config.update(config)
    if "DebugHooks" in config:
        debug_hooks = config["DebugHooks"]
        for key, value in debug_hooks:
            _debug_hooks[key](value)


def get_global_config():
    return _global_config.get()
