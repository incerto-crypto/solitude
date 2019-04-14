# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import os


def test_0001_resources():
    from solitude.common.resource_util import get_resource_path
    REQUIRED_RESOURCES = [
        "report.filemessage.default.html"
    ]
    for resource_name in REQUIRED_RESOURCES:
        assert os.path.isfile(get_resource_path(resource_name))


def test_0002_config_schema():
    from solitude._internal.config_schema import SCHEMA, SCHEMA_SCHEMA
    from solitude import make_default_config
    import jsonschema

    # validate schema
    jsonschema.validate(instance=SCHEMA, schema=SCHEMA_SCHEMA)

    # validate default configuration
    cfg = make_default_config()
    jsonschema.validate(instance=cfg, schema=SCHEMA)
