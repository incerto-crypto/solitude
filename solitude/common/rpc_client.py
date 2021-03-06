# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import List, Tuple
import json
import requests
from solitude.common.errors import CommunicationError


def iter_list_or_single(obj):
    if isinstance(obj, list):
        for item in obj:
            yield item
    else:
        yield obj


class RPCClient:
    """Communicate with a JSON-RPC server

    Any method can be called by RPCClient.rpcFunctionName(arguments...)
    """
    def __init__(self, endpoint: str):
        """
        :param endpoint: JSON-RPC server URL
        """
        self._endpoint = endpoint
        self._session = requests.Session()
        self._json_rpc_id = 1

    def _prepare(self, key, args):
        rpc_call_id = self._json_rpc_id
        self._json_rpc_id += 1
        return {
            "jsonrpc": "2.0",
            "method": key,
            "params": args,
            "id": rpc_call_id
        }

    def _communicate(self, data):
        try:
            http_response = self._session.post(self._endpoint, json=data)
        except requests.exceptions.ConnectionError:
            raise CommunicationError("Connection Error: %s" % self._endpoint)
        if http_response.status_code != 200:
            raise CommunicationError("Received HTTP status code %d" % http_response.status_code)
        response = json.loads(http_response.text)

        for req, resp in zip(iter_list_or_single(data), iter_list_or_single(response)):
            if resp.get("id") != req["id"]:
                raise CommunicationError("Call id mismatch: expected %r, received %r" % (
                    req["id"], resp.get("id")))
            if "result" not in resp:
                raise CommunicationError("Received empty response")
            yield resp["result"]

    def __getattr__(self, key):
        """Call any function of rpc server by RPCClient.rpcFunctionName
        """
        def rpc_call(*args):
            data = self._prepare(key, args)
            return next(self._communicate(data))
        return rpc_call

    def batch_call(self, functions: List[Tuple[str, list]]):
        """Perform a batch call

        :param function: list of the requests to perform in batch, as tuples of
            (method name, list of arguments)
        :return: the list of responses from the server
        """
        data = []
        for (key, args) in functions:
            data.append(self._prepare(key, args))
        return list(self._communicate(data))
