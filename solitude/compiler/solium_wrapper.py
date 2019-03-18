# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Union  # noqa
from collections import OrderedDict
import os
import json
import subprocess
import re
from solitude.common import FileMessage


class SoliumWrapper:
    def __init__(self, executable: str, plugins: List[str], rules: Union[dict, OrderedDict]):
        self._executable = executable
        self._args = [
            "--no-soliumrc",
            "--no-soliumignore",
            "--reporter", "gcc"]
        for plugin in plugins:
            self._args.extend([
                "--plugin",
                plugin])
        for key, value in rules.items():
            self._args.extend([
                "--rule",
                "%s: %s" % (key, json.dumps(value))])

    def lint_source(self, source: str, name: str="<stdin>"):
        return self._lint(stdin=source, stdin_alias=name)

    def lint_file(self, filename: str):
        return self._lint(filename=os.path.abspath(filename))

    def _lint(self, filename: str=None, stdin=None, stdin_alias="<stdin>") -> List[FileMessage]:
        assert not (filename is not None and stdin is not None)

        stdin_data = None
        if filename is not None:
            cmd = [self._executable] + self._args + ["--file", filename]
        elif stdin is not None:
            # TODO according to comment in solium sources, this feature does not work on Windows
            #   We may have to work around by writing a temporary file on windows
            cmd = self._args + ["--stdin"]
            stdin_data = stdin.encode('utf-8')

        # TODO solium is slow!

        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out, err = p.communicate(stdin_data)
        return _decode_linter_output(out.decode('utf-8'), stdin_alias=stdin_alias)


def _decode_linter_output(out, stdin_alias: str) -> List[FileMessage]:
    errors = []
    pos_regex = re.compile(r"^(.+):([0-9]+):([0-9]+):\s*([^:\s]+)\s*:")
    for line in out.split("\n"):
        m = pos_regex.search(line)
        if m is not None:
            try:
                err_msg = line[m.span(0)[1]:].strip()
                err_file = m.group(1)
                if err_file == "<stdin>":
                    err_file = stdin_alias
                err_line = int(m.group(2))
                err_col = int(m.group(3))
                err_type = m.group(4).lower()
                errors.append(FileMessage(
                    type=err_type,
                    filename=err_file,
                    line=err_line,
                    column=err_col,
                    message=err_msg))
            except (ValueError, IndexError):
                pass
    return errors
