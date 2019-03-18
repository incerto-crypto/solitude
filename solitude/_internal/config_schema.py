# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

DEFAULT_SOLC_VERSION = "0.5.2"
DEFAULT_GANACHECLI_VERSION = "6.4.1"
DEFAULT_SOLIUM_VERSION = "1.2.3"
DEFAULT_TOOLS_DIR = "~/.solitude-dev"
DEFAULT_REQUIRED_TOOLS = ["Solc", "GanacheCli"]
DEFAULT_RPC_PORT = 8545
DEFAULT_ACCOUNTS = [
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
]


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

SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "SolitudeConfiguration",
    "type": "object",
    "properties": {
        "Project.Name": {
            "type": "string",
            "description": "Your project's name",
            "default": "MyProject"
        },
        "Tools.Directory": {
            "type": "string",
            "description": "Path to the directory where the downloaded tools will be installed",
            "default": DEFAULT_TOOLS_DIR
        },
        "Tools.Solc.Version": {
            "type": "string",
            "description": "solc (Compiler) required version",
            "default": DEFAULT_SOLC_VERSION
        },
        "Tools.GanacheCli.Version": {
            "type": "string",
            "description": "ganache-cli (Server) required version",
            "default": DEFAULT_GANACHECLI_VERSION
        },
        "Tools.Solium.Version": {
            "type": "string",
            "description": "solium (Linter) required version",
            "default": DEFAULT_SOLIUM_VERSION
        },
        "Tools.Required": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["Solc", "GanacheCli", "Solium"]
            },
            "description": "List of tools required by your project",
            "default": DEFAULT_REQUIRED_TOOLS
        },
        "Server.Port": {
            "anyOf": [
                {"type": "number"},
                {"type": "string"}
            ],
            "description": "Port or range of ports on which the server can be started",
            "default": DEFAULT_RPC_PORT
        },
        "Server.Accounts": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Initial accounts and balances for the server",
            "default": DEFAULT_ACCOUNTS
        },
        "Server.BlockTime": {
            "anyOf": [
                {"type": "integer"},
                {"type": "null"}
            ],
            "description": "Starting block time for the server",
            "default": None
        },
        "Server.Host": {
            "type": "string",
            "description": "Host on which to start the server",
            "default": "127.0.0.1"
        },
        "Server.GasPrice": {
            "type": "integer",
            "description": "Price of gas for the server",
            "default": 20000000000
        },
        "Server.GasLimit": {
            "type": "integer",
            "description": "Gas limit for the server",
            "default": 6721975
        },
        "Testing.StartServer": {
            "type": "boolean",
            "description": "Run a server instance on creation of the testing context",
            "default": True
        },
        "Client.Endpoint": {
            "type": "string",
            "description": "Endpoint to which the RPC client should connect to",
            "default": "http://127.0.0.1:%d" % DEFAULT_RPC_PORT
        },
        "Client.AccountAliases": {
            "type": "object",
            "description": "Friendly names for the accounts from the account storage",
            "default": {"attila": 0, "george": 1}
        },
        "Client.ContractBuildDir": {
            "type": "string",
            "description": "Directory where built contracts are found, to get the ABI",
            "default": "./eth/build"
        },
        "Client.GasLogDir": {
            "type": "string",
            "description": "Directory where the transaction logs will be stored",
            "default": "./log"
        },
        "Client.EnableGasLog": {
            "type": "boolean",
            "description": "Enable transaction logging",
            "default": False
        },
        "Client.DefaultGas": {
            "type": "integer",
            "description": "Default amount of gas configured for the client's transactions",
            "default": 1000000
        },
        "Compiler.ContractDir": {
            "type": "string",
            "description": "Directories where the contract sources to compile are located",
            "default": "./eth/contracts"
        },
        "Compiler.BuildDir": {
            "type": "string",
            "description": "Directory where contracts built by the compiler will be stored",
            "default": "./eth/build"
        },
        "Compiler.Optimize": {
            "anyOf": [
                {"type": "integer"},
                {"type": "null"}
            ],
            "description": "Solidity compiler optimize runs, or null for no optimization",
            "default": None
        },
        "Compiler.Lint.Plugins": {
            "type": "array",
            "description": "List of plugins solium linter",
            "items": {
                "type": "string"
            },
            "default": ["security"]
        },
        "Compiler.Lint.Rules": {
            "type": "object",
            "description": "Rules (configuration) for solium linter",
            "default": {
                "quotes": ["error", "double"],
                "indentation": ["error", 4]
            }
        }
    },
    "additionalProperties": False,
    "required": [
        "Project.Name",
        "Tools.Directory",
        "Tools.Solc.Version",
        "Tools.GanacheCli.Version",
        "Tools.Solium.Version",
        "Tools.Required",
        "Server.Port",
        "Server.Accounts",
        "Server.BlockTime",
        "Server.Host",
        "Server.GasPrice",
        "Server.GasLimit",
        "Testing.StartServer",
        "Client.Endpoint",
        "Client.AccountAliases",
        "Client.ContractBuildDir",
        "Client.GasLogDir",
        "Client.EnableGasLog",
        "Client.DefaultGas",
        "Compiler.ContractDir",
        "Compiler.BuildDir",
        "Compiler.Optimize",
        "Compiler.Lint.Plugins",
        "Compiler.Lint.Rules"
    ]
}


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