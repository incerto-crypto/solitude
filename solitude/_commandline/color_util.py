# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import colorama
from colorama import Style, Fore, Back

from solitude._internal.oi_common_objects import ColorText

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
                return render_colortext(text)
            else:
                return colorize_text(str(text), color)
        else:
            return str(text)


def colorize_text(text, color):
    if not color:
        return text
    return "".join(COLOR_MAP[c] for c in color.split("+")) + text + Style.RESET_ALL


def render_colortext(colortext: ColorText):
    for text, color in colortext.iter_chunks():
        if color:
            out += colorize_text(text, color)
        else:
            out += text
