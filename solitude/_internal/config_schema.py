# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import json
import jinja2
import re


import os
fname = 'resources/config_schema.json'

_file = os.path.abspath(__file__)
_dir = os.path.dirname(_file)
fname_path = os.path.join(_dir, fname)

SCHEMA_FILENAME = fname_path

DEFAULTS = {
    "DEFAULT_SOLC_VERSION": "0.5.2",
    "DEFAULT_GANACHECLI_VERSION": "6.4.1",
    "DEFAULT_SOLIUM_VERSION": "1.2.3",
    "DEFAULT_TOOLS_DIR": "~/.solitude-dev",
    "DEFAULT_REQUIRED_TOOLS": ["Solc", "GanacheCli"],
    "DEFAULT_RPC_PORT": 8545,
    "DEFAULT_ACCOUNTS": [
        "0xedf206987be3a32111f16c0807c9055e2b8b8fc84f42768015cb7f8471137890, 100 eth",
        "0x0ca1573d73a070cfa5c48ddaf000b9480e94805f96a79ffa2d5bc6cc3288a92d, 100 eth",
        "0x2688eabfae4637b73752d342991579500f231c72d52dd22b29bf018c0df4bdb7, 100 eth",
        "0x4a4dfe519c6182638d18c75523a95ed55a938426d5e80ac55a39ed83f9e4c5fd, 100 eth",
        "0x60fae350e15bdfdc227fc0616dbe26acb5f05d65d469a811383926a675940237, 100 eth",
        "0x9085677b64cb52d4b36058be795cb315722a361fb78b042a02600bcb2b3f2ce1, 100 eth",
        "0x372f46eae3eb91865809a90339acea1697555021d583dceb7dd05a635de7514d, 100 eth",
        "0x48d73da350f98b1b16ede5fab0078c1ee2c3525483d5365626b4ba3d798686cb, 100 eth",
        "0x669fd08dd8760b47b368153b2d8483c08295a0fa2853684746bf84ea533a611c, 100 eth",
        "0x6d3f46df88ffbaf2c7c5a9567f6c26414fa205ae6ca27312a656115a71dfc9f4, 100 eth"
    ],
}


# Configuration schema
# The configuration is a set of key-value pairs. It is not nested.
#
# When the value is of type object or array, only limited validation occours and
#   the resulting dict / list is provided as is. For instance, when passing object
#   values from the configuration files to an external application, as JSON,
#   the application will take care of validation, and it is responsibility of the
#   user to provide correct values.
#
# Each property in the configuration must have either a "type" directive, or a
#   "anyOf" directive with a list of "type" directives, to specify the possible
#   types of the value

# TODO enforce more strict schema on strings where possible

with open(SCHEMA_FILENAME) as fschema:
    raw_template = fschema.read() #"{{ DEFAULT_REQUIRED_TOOLS | tojson }}"
    raw_template = raw_template.replace('"[{{', '{{')
    raw_template = raw_template.replace('}}]"', '}}')
    template = jinja2.Template(raw_template)
    print(template.render(**DEFAULTS))
    SCHEMA = json.loads(template.render(**DEFAULTS))

SCHEMA_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "SolitudeConfigurationSchema",
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["object"]
        },
        "properties": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "object",
                    "properties": {
                        "type": {},
                        "description": {},
                        "default": {}
                    },
                    "required": [
                        "description",
                        "default"
                    ],
                    "oneOf": [
                        {"required": ["type"]},
                        {"required": ["anyOf"]}
                    ]
                }
            }
        }
    }
}
