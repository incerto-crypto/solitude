# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os


def get_resource_path(resource_name):
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "resources",
        resource_name)
