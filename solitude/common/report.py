# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List  # noqa
import os
import pystache
import solitude
from solitude.common import FileMessage


class FileMessageReport:
    def __init__(self, template: str, project: str, component: str):
        if os.path.isfile(template):
            template_path = template
        else:
            template_path = os.path.join(
                os.path.dirname(solitude.__file__),
                "resources",
                "report." + template)
        with open(template_path, "r") as fp:
            self._template = pystache.parse(fp.read())
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
