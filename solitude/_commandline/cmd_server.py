# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import time
from solitude import Factory
from solitude.server import kill_all_servers

from solitude.common.config_util import (
    read_config_file)


def main(args):
    cfg = read_config_file(args.config)
    if args.port > 0:
        cfg["Server.Port"] = args.port
    factory = Factory(cfg)
    server = factory.create_server()
    try:
        server.start()
        print("Server started at: %s" % server.endpoint)
        print("Ctrl-C to quit")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        print("Shutdown...")
        server.stop()
    finally:
        kill_all_servers()
