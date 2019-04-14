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
import solitude._internal
from solitude._internal import RaiseForParam, type_assert, EnumType, value_assert
from solitude.common.errors import CommunicationError


def get_resource_path(resource_name):
    return os.path.join(
        os.path.dirname(os.path.abspath(solitude._internal.__file__)),
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


def _copy_fileobj_to_destination(source, destination, is_text=False):
    with contextlib.ExitStack() as stack:
        if isinstance(destination, str):
            fp = stack.enter_context(open(destination, "wb" if not is_text else "w"))
        elif hasattr(destination, "write"):
            fp = destination
        else:
            internal_assert(
                False, "destination must be either a path or file-like")
        shutil.copyfileobj(source, fp)


def _url_to_fileobj(url: str, decode=False):
    schema, path = _parse_url(url)
    try:
        if schema in (Schema.HTTP, Schema.HTTPS):
            r = requests.get(url, stream=True)
            r.raise_for_status()
            r.raw.decode_content = True
            stream = r.raw
            if decode:
                stream = io.TextIOWrapper(r.raw)
            return stream
        elif schema == Schema.FILE:
            return open(os.path.expanduser(path), "rb" if not decode else "r")
        elif schema == Schema.RESOURCE:
            return open(get_resource_path(path), "rb" if not decode else "r")
    except (requests.RequestException, FileNotFoundError, IOError) as e:
        raise CommunicationError("Cannot open '%s'" % url) from e
    raise CommunicationError("Schema not recognized for '%s'" % url)


def open_url(url: str, decode=False):
    return _url_to_fileobj(url, decode=decode)


def read_from_url(url: str, decode=False):
    with _url_to_fileobj(url, decode=decode) as source:
        if decode:
            data = io.StringIO()
        else:
            data = io.BytesIO()
        _copy_fileobj_to_destination(source, data, is_text=decode)
        data.seek(0, 0)
        return data.read()


def copy_from_url(url: str, destination, decode=False):
    with _url_to_fileobj(url, decode=decode) as source:
        _copy_fileobj_to_destination(source, destination, is_text=decode)


class _GlobalConfig:
    def __init__(self):
        with open(get_resource_path("global_config.json"), "r") as fp:
            self._config = json.load(fp)

    def update(self, config: dict):
        self._config.update(config)

    def get(self):
        return self._config


def _DEBUG_SolcEmscripten(enable_emscripten):
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
