# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import shlex
import traceback


class ObjectInterfaceException(Exception):
    def __init__(self, name, args=None):
        self.name = name
        self.eargs = args if args else []
        super().__init__(name)


class ObjectInterface:
    def __init__(self):
        self._oui_commands = {}
        self._oui_handlers = {}
        self._oui_quit = False

    def error(self, func, names):
        if not isinstance(names, list):
            names = [names]
        for name in names:
            self._oui_handlers[name] = func

    def command(self, func, names):
        if not isinstance(names, list):
            names = [names]
        for name in names:
            self._oui_commands[name] = func

    def quit(self):
        self._oui_quit = True

    def _oui_default_handler(self, e):
        traceback.print_exc()
        return ObjectInterface._oui_make_error(e)

    @staticmethod
    def _oui_make_error(e):
        return {
            "status": "error",
            "what": {
                "name": "UnhandledException",
                "message": str(e)
            }
        }

    @staticmethod
    def _oui_make_quit():
        return {
            "status": "quit"
        }

    @staticmethod
    def _oui_make_response(response):
        return {
            "status": "ok",
            "response": response
        }

    def _oui_handle_error(self, e):
        if e.name == "_quit":
            self._oui_quit = True
            return ObjectInterface._oui_make_quit()
        try:
            if e.name in self._oui_handlers:
                response = self._oui_handlers[e.name](e.eargs)
                return ObjectInterface._oui_make_response(response)
            else:
                return self._oui_default_handler(e)
        except ObjectInterfaceException as e:
            if e.name == "_quit":
                self._oui_quit = True
                return ObjectInterface._oui_make_quit()
            raise
        except Exception as e:
            return self._oui_default_handler(e)

    def _oui_handle_command(self, obj: dict):
        try:
            command, args = obj["command"], obj["args"]
            if not isinstance(command, str):
                return self._oui_handle_error(ObjectInterfaceException("_syntax", [obj]))
        except (KeyError, ValueError):
            return self._oui_handle_error(ObjectInterfaceException("_syntax", [obj]))

        if command not in self._oui_commands:
            return self._oui_handle_error(ObjectInterfaceException("_command", [obj]))
        try:
            response = self._oui_commands[command](args)
            return ObjectInterface._oui_make_response(response)
        except ObjectInterfaceException as e:
            return self._oui_handle_error(e)
        except Exception as e:
            return self._oui_default_handler(e)

    def call(self, obj):
        if self._oui_quit:
            return ObjectInterface._oui_make_quit()
        return self._oui_handle_command(obj)


def parse_args(line):
    """
    :raises: ValueError
    """
    lexer = shlex.shlex(line)
    lexer.wordchars += ".:#"
    lexer.commenters = ""
    return list(lexer)
