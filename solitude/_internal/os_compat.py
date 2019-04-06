# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import sys
import os
import stat
import re
from solitude._internal.enum_type import EnumType


class Platform(EnumType):
    LINUX = 1
    WINDOWS = 2
    DARWIN = 3


def get_platform():
    platform_name = str(sys.platform)
    if platform_name.startswith("linux"):
        return Platform.LINUX
    elif platform_name == "win32":
        return Platform.WINDOWS
    elif platform_name == "darwin":
        return Platform.DARWIN


def platform_is_unix():
    return get_platform() in (Platform.LINUX, Platform.DARWIN)


def append_executable_extension(path, winext="exe"):
    if get_platform() == Platform.WINDOWS:
        return path + "." + winext
    return path


def set_executable_flag(path):
    if platform_is_unix():
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)


def is_valid_path(x):
    return re.search("[<>:\\\"\\/\\\\|\\?\\*]", x) is None


def safe_path(x):
    return re.sub("[<>:\\\"\\/\\\\|\\?\\*]", " ", x)
