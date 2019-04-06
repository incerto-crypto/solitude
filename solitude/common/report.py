# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List  # noqa
import os
import io
import pystache
import solitude
from solitude.common import FileMessage
from solitude._internal import copy_from_url


class FileMessageReport:
    def __init__(self, template: str, project: str, component: str):
        template_data = io.BytesIO()
        copy_from_url(template, template_data)
        template_data.seek(0)
        self._template = pystache.parse(template_data.read())
        self._data = {
            "project": project,
            "component": component,
            "info": [],
            "table_header": None,
            "files": []
        }

    def add_info(self, key: str, value: str):
        self._data["info"].append({
            "key": key,
            "value": value})

    def add_file(self, filename: str, messages: List[FileMessage]):
        self._data["files"].append({
            "filename": filename,
            "count": len(messages),
            "style": ("st-error" if messages else "st-ok"),
            "content": bool(messages),
            "messages": [{
                "line": m.line,
                "column": m.column,
                "type": m.type,
                "message": m.message} for m in messages]
        })

    def dump(self, fileobj):
        fileobj.write(self.dumps())

    def dumps(self):
        return pystache.render(self._template, self._data)
