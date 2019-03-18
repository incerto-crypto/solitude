# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import colorama
from colorama import Style, Fore, Back

COLOR_MAP = {
    "black": Fore.BLACK,
    "red": Fore.RED,
    "green": Fore.GREEN,
    "yellow": Fore.YELLOW,
    "blue": Fore.BLUE,
    "magenta": Fore.MAGENTA,
    "cyan": Fore.CYAN,
    "white": Fore.WHITE,
    "bgblack": Back.BLACK,
    "bgred": Back.RED,
    "bggreen": Back.GREEN,
    "bgyellow": Back.YELLOW,
    "bgblue": Back.BLUE,
    "bgmagenta": Back.MAGENTA,
    "bgcyan": Back.CYAN,
    "bgwhite": Back.WHITE,
    "dim": Style.DIM,
    "normal": Style.NORMAL,
    "bright": Style.BRIGHT,
    "reset": Style.RESET_ALL
}


class Color:
    _enabled = False

    @classmethod
    def enable(cls):
        if not cls._enabled:
            colorama.init()
            cls._enabled = True

    @classmethod
    def wrap(cls, text, color=""):
        if cls._enabled:
            if isinstance(text, ColorText):
                return text.to_string(colored=True)
            else:
                return ColorText.wrap(str(text), color)
        else:
            return str(text)


class ColorText:
    def __init__(self, chunks=None):
        self._chunks = []
        if chunks:
            self._chunks.extend(chunks)

    @staticmethod
    def wrap(text, color):
        if not color:
            return text
        return "".join(COLOR_MAP[c] for c in color.split("+")) + text + Style.RESET_ALL

    def append(self, text, color=""):
        self._chunks.append([text, color])

    def to_string(self, colored=True):
        out = ""
        if colored:
            for text, color in self._chunks:
                if color:
                    out += ColorText.wrap(text, color)
                else:
                    out += text
        else:
            for text, _ in self._chunks:
                out += text
        return out

    def __str__(self):
        return self.to_string(colored=False)

    def to_obj(self):
        return {
            "chunks": [c for c in self._chunks]
        }

    @staticmethod
    def from_obj(obj):
        return ColorText(obj["chunks"])
