# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Union, Tuple, Optional
import os
import json
import yaml
import re
from collections import OrderedDict
from solitude.errors import SetupError
import jsonschema

from solitude._internal.config_schema import SCHEMA


def config_schema_to_defaults(schema):
    """Extracts default required values from a jsonschema

    The json schema must be an object and have defaults for
        all properties
    """
    cfg = OrderedDict()
    properties = schema["properties"]
    for key in schema["required"]:
        cfg[key] = properties[key]["default"]
    return cfg


# adapted from https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation
class MySafeDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


# adapted from https://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts
def yaml_ordered_load(stream, Loader=yaml.SafeLoader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def yaml_ordered_dump(data, stream=None, Dumper=MySafeDumper, **kwargs):
    class OrderedDumper(Dumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items())
    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwargs)


def read_yaml_or_json_file(path: str):
    if os.path.splitext(path)[-1] not in (".json", ".yaml"):
        raise SetupError("Configuration file must be either .yaml or .json")
    with open(path, 'r') as fp:
        if path.endswith(".json"):
            cfg_from_file = json.load(fp, object_pairs_hook=OrderedDict)
        else:
            cfg_from_file = yaml_ordered_load(fp)


def read_config_file(path: str):
    """Read a solitude configuration from yaml or json file.

    :param path: path to configuration file
    """
    cfg_from_file = read_yaml_or_json_file(path)
    cfg = config_schema_to_defaults(SCHEMA)
    cfg.update(cfg_from_file)
    update_cfg_with_env_overrides(cfg)
    try:
        jsonschema.validate(instance=cfg, schema=SCHEMA)
    except jsonschema.ValidationError as e:
        raise SetupError(str(e)) from e
    return cfg


def write_config_file(cfg: Union[dict, OrderedDict], path: str):
    if os.path.splitext(path)[-1] not in (".json", ".yaml"):
        raise SetupError("Configuration file must be either .yaml or .json")
    with open(path, 'w') as fp:
        if path.endswith(".json"):
            json.dump(cfg, fp, indent=4)
        else:
            yaml_ordered_dump(cfg, fp, default_flow_style=False)


def parse_port_range(port: Union[str, int]) -> Tuple[int, int]:
    if isinstance(port, str):
        v = port.split(",")
        if len(v) <= 2:
            return (int(v[0].strip()), int(v[1].strip()))
    elif isinstance(port, int):
        return (port, port)
    raise SetupError("Port is not a valid port or range")


def parse_server_account(account: str) -> Tuple[str, int]:
    units = {
        "": 1,
        "wei": 1,
        "kwei": 10**3,
        "ada": 10**3,
        "mwei": 10**6,
        "babbage": 10**6,
        "gwei": 10**9,
        "shannon": 10**9,
        "micro": 10**12,
        "szabo": 10**12,
        "finney": 10**15,
        "milli": 10**15,
        "eth": 10**18,
        "ether": 10**18,
        "kether": 10**21,
        "mether": 10**24,
        "gether": 10**27,
        "tether": 10**30}
    v = account.split(",")
    if len(v) == 1:
        return (v[0].strip(), 10**20)
    elif len(v) == 2:
        m = re.match(r"^([0-9\.]+)\s*(" + "|".join(u for u in units) + "|)$", v[1].strip())
        if m is not None:
            return (v[0].strip(), int(float(m.group(1)) * units[m.group(2)]))
    raise SetupError("Account must be of format '0xPrivateKey [,Ether]'")


def parse_path(path: Optional[str]) -> Optional[str]:
    if path is not None:
        return os.path.expanduser(path)
    return None


def update_cfg_with_env_overrides(cfg: Union[dict, OrderedDict]) -> None:
    PREFIX = "SOL_"
    for key, value in os.environ.items():
        if key.startswith(PREFIX):
            cfgkey = key[len(PREFIX):].replace("_", ".")
            if cfgkey in SCHEMA["required"]:
                try:
                    cfg[cfgkey] = interpret_value_with_schema(value, SCHEMA["properties"][cfgkey])
                except ValueError:
                    raise SetupError("Could not decode environment variable override %s=%s" % (key, value))


def try_interpret_value_with_schema_type(value, jsonschema_type):
    if jsonschema_type == "object":
        try:
            value_obj = json.loads(value)
            if isinstance(value_obj, dict):
                return value_obj
        except json.JSONDecodeError:
            raise ValueError(value)
    elif jsonschema_type == "array":
        try:
            value_obj = json.loads(value)
            if isinstance(value_obj, list):
                return value_obj
        except json.JSONDecodeError:
            raise ValueError(value)
    elif jsonschema_type == "string":
        return value
    elif jsonschema_type == "number":
        return float(value)
    elif jsonschema_type == "integer":
        return int(value)
    elif jsonschema_type == "null":
        if value == "null":
            return None
    raise ValueError(value)


def interpret_value_with_schema(value, schema):
    TYPE_PRIORITY = {
        "array": 0,
        "object": 0,
        "string": 1,
        "number": 2,
        "integer": 3,
        "null": 4
    }
    if "type" in schema:
        return try_interpret_value_with_schema_type(value, schema["type"])
    elif "anyOf" in schema:
        options = [option["type"] for option in schema["anyOf"] if ("type" in option)]
        options = sorted(options, key=lambda x: TYPE_PRIORITY[x], reverse=True)
        for option in options:
            try:
                return try_interpret_value_with_schema_type(value, option)
            except ValueError:
                pass
    raise ValueError(value)
