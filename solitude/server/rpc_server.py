# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Tuple, Sequence, Dict, Set, Optional, Union  # noqa
import time
import os
import sys
import signal
import threading
import subprocess
from collections import namedtuple
from solitude.client.rpc_client import RPCClient
from solitude.errors import SetupError, RPCError

# TODO fix coordination of multiple ganache instances for test parallelization

ServerInfo = namedtuple('RPCServerInfo', ['pid', 'port', 'endpoint'])

_all_servers_lock = threading.Lock()
_all_servers = {}  # type: Dict[int, ServerInfo]

_ports_lock = threading.Lock()
_ports = set()  # type: Set[int]


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


def _reserve_port(port_range: Tuple[int, int]) -> int:
    with _ports_lock:
        for port in range(port_range[0], port_range[1]+1):
            if port not in _ports:
                _ports.add(port)
                return port
    raise SetupError("No free port found in range (%d, %d)" % port_range)


def _free_port(port: int):
    with _ports_lock:
        try:
            _ports.remove(port)
        except KeyError:
            pass


class RPCTestServer:
    """Wrapper around the ganache-cli executable
    """
    def __init__(
            self,
            executable="ganache-cli",
            host="127.0.0.1",
            port: Union[int, Tuple[int, int]]=(8545, 8545),
            accounts=None,
            blocktime=None,
            gasprice=20000000000,
            gaslimit=6721975):
        """
        :param port: port on which the new ganache-cli instance will listen
        :param executable: path to executable or executable name in PATH
        """
        self._executable = executable
        self._host = host
        if isinstance(port, tuple):
            self._port_range = port
        else:
            self._port_range = (port, port)
        self._accounts = accounts
        self._blocktime = blocktime
        self._gasprice = gasprice
        self._gaslimit = gaslimit

        self._port = None  # type: Optional[int]
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
        assert(isinstance(self._port, int))
        _free_port(self._port)

    def start(self, timeout: float = 15.0) -> None:
        """Start in background
        :param timeout: timeout to wait for ganache-cli to respond on JSON-RPC interface
        """
        assert self._pid is None

        # choose port
        self._port = _reserve_port(self._port_range)
        self._endpoint = "http://127.0.0.1:%d" % self._port
        self._rpc = RPCClient(self._endpoint)

        cmd = [
            self._executable,
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
            except RPCError:
                pass
            if time.time() - time_begin > timeout:
                self.kill()
                _free_port(self._port)
                raise SetupError("Failed to start ganache-cli")
        # _cli_version = self._rpc.web3_clientVersion()
        # print("ganache-cli version %s" % cli_version)

    @property
    def endpoint(self) -> str:
        """Get endpoint
        :return: endpoint url string
        """
        return self._endpoint

    def kill(self, timeout: float = 1.0) -> None:
        """Forcibly kill (SIGKILL) the ganache-cli process and wait
        :param timeout: time to wait for ganache-cli to terminate
        """
        try:
            assert(self._pid is not None)
            assert(self._thread is not None)
            os.kill(self._pid, signal.SIGKILL)
            self._thread.join(timeout=timeout)
        except OSError as err:
            print(str(err), file=sys.stderr)

    def stop(self, timeout: float=15.0) -> None:
        """Terminate (SIGTERM) the ganache-cli process and wait. If this fails,
            kill the process

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
        :return: True if alive
        """
        if self._thread is None:
            return False
        return self._thread.is_alive()
