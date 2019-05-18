# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import json
import os


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

SCHEMA_FILENAME = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "resources",
    "config_schema.json")

with open(SCHEMA_FILENAME) as fschema:
    SCHEMA = json.load(fschema)


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
