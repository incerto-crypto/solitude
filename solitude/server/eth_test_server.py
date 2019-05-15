# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Tuple, Sequence, Dict, Set, Optional, Union, List  # noqa
import time
import os
import sys
import signal
import threading
import subprocess
from collections import namedtuple
from solitude.common import RPCClient
from solitude.common.errors import SetupError, CommunicationError

# TODO fix coordination of multiple ganache instances for test parallelization

ServerInfo = namedtuple('RPCServerInfo', ['pid', 'port', 'endpoint'])

_all_servers_lock = threading.Lock()
_all_servers = {}  # type: Dict[int, ServerInfo]


def get_all_servers() -> Sequence[ServerInfo]:
    with _all_servers_lock:
        return [server for server in _all_servers.values()]


def kill_all_servers():
    servers = get_all_servers()
    for server in servers:
        os.kill(server.pid, signal.SIGKILL)
        _remove_server(server.pid)


def _add_server(pid: int, info: ServerInfo):
    with _all_servers_lock:
        if pid in _all_servers:
            raise SetupError("A server with the same pid exists")
        _all_servers[pid] = info


def _remove_server(pid: int):
    with _all_servers_lock:
        try:
            del _all_servers[pid]
        except KeyError:
            pass


class ETHTestServer:
    """Wrapper around the ganache-cli executable
    """
    def __init__(
            self,
            executable="ganache-cli",
            host="127.0.0.1",
            port: int=8545,
            accounts: List[Tuple[str, int]]=None,
            blocktime: Optional[float]=None,
            gasprice=20000000000,
            gaslimit=6721975):
        """
        Create a ganache-cli server instance

        :param executable: path to the ganache-cli executable file
        :param host: address of the interface to which the server will bind to
        :param port: port on which the server will listen
        :param accounts: list of accounts to create on the server, as a list of
            (private_key, wei_balance) tuples, where private_key is a hex string
            of 32 bytes prefixed with "0x".
        :param blocktime: if not None, enable automatic mining with blocktime
            interval, in seconds.
        :param gasprice: price of gas (wei)
        :param gaslimit: gas limit
        """
        self._executable = executable
        self._host = host
        self._port = port
        self._accounts = accounts
        self._blocktime = blocktime
        self._gasprice = gasprice
        self._gaslimit = gaslimit

        self._endpoint = None  # type: Optional[str]
        self._pid = None  # type: Optional[int]
        self._process = None  # type: Optional[subprocess.Popen]
        self._thread = None  # type: Optional[threading.Thread]
        self._rpc = None  # type: Optional[RPCClient]
        self._stdout = b''
        self._stderr = b''

    def _ganache_cli_main(self) -> None:
        assert(isinstance(self._process, subprocess.Popen))
        self._stdout, self._stderr = self._process.communicate()
        assert(isinstance(self._pid, int))
        _remove_server(self._pid)

    def start(self, timeout: float=15.0) -> None:
        """Start ganache-cli in the background.

        When this function terminates (without errors), it means the server is running
        in the background and ready to receive requests.

        :param timeout: timeout to wait for ganache-cli to respond, seconds
        """
        assert self._pid is None

        self._endpoint = "http://%s:%d" % (self._host, self._port)
        self._rpc = RPCClient(self._endpoint)

        cmd = [
            self._executable,
            "-v",
            "--host", self._host,
            "--port", str(self._port),
            "--noVMErrorsOnRPCResponse"]
        if self._blocktime is not None:
            cmd.extend([
                "--blockTime", str(self._blocktime)])
        cmd.extend([
            "--gasPrice", str(self._gasprice),
            "--gasLimit", str(self._gaslimit)])
        if self._accounts is not None:
            for account in self._accounts:
                cmd.append("--account=%s,%d" % account)

        if sys.platform == "win32":
            # start the process through the process container, which ensures all
            #   child processes are terminated before it terminates
            import inspect
            from solitude._internal import win32_process_container
            cmd = [sys.executable, inspect.getfile(win32_process_container)] + cmd

        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False)
        # start background thread waiting for ganache-cli termination
        self._pid = self._process.pid
        _add_server(
            self._pid,
            ServerInfo(pid=self._pid, port=self._port, endpoint=self._endpoint))
        self._thread = threading.Thread(target=self._ganache_cli_main)
        self._thread.start()
        # wait for process to respond on JSON/RPC interface
        time_begin = time.time()
        while True:
            try:
                is_listening = self._rpc.net_listening()
                if is_listening is True:
                    break
            except CommunicationError:
                pass
            if time.time() - time_begin > timeout:
                self.kill()
                raise SetupError("Failed to start ganache-cli")
        # _cli_version = self._rpc.web3_clientVersion()
        # print("ganache-cli version %s" % cli_version)

    @property
    def endpoint(self) -> str:
        """Endpoint URL
        """
        return self._endpoint

    def kill(self, timeout: float=1.0) -> None:
        """Forcibly kill (SIGKILL) the ganache-cli process and wait

        :param timeout: time to wait for ganache-cli to terminate
        """
        try:
            assert(self._pid is not None)
            assert(self._thread is not None)
            os.kill(self._pid, signal.SIGKILL)
            self._thread.join(timeout=timeout)
        except OSError as err:
            # print(str(err), file=sys.stderr)
            pass

    def stop(self, timeout: float=15.0) -> None:
        """Terminate (SIGTERM) the ganache-cli process and wait. If this fails,
            kill the process (SIGKILL).

        :param timeout: time to wait for ganache-cli to terminate
        """
        assert(self._pid is not None)
        assert(self._thread is not None)
        # send termination signal and wait timeout
        self._process.terminate()
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            # if the process has not terminated yet, kill it
            self.kill()
            self._thread.join(timeout=5.0)

    def is_alive(self) -> bool:
        """Check if the ganache-cli process is running

        :return: True if ganache-cli is running
        """
        if self._thread is None:
            return False
        return self._thread.is_alive()
