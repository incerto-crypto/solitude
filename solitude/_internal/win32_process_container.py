# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree


from typing import List
import sys
import re
import time
import win32process
import win32job
import win32console
import win32file
import win32event
import win32api

import ctypes
import ctypes.wintypes


class JOBOBJECT_ASSOCIATE_COMPLETION_PORT(ctypes.Structure):
    _fields_ = [
        ("CompletionKey", ctypes.c_ulong),
        ("CompletionPort", ctypes.wintypes.HANDLE)]

JobObjectAssociateCompletionPortInformation = 7


class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ('Internal', ctypes.wintypes.LPVOID),
        ('InternalHigh', ctypes.wintypes.LPVOID),
        ('Offset', ctypes.wintypes.DWORD),
        ('OffsetHigh', ctypes.wintypes.DWORD),
        ('Pointer', ctypes.wintypes.LPVOID),
        ('hEvent', ctypes.wintypes.HANDLE)]


# The logic for escaping arguments for the CreateProcess function is derived from:
#   https://blogs.msdn.microsoft.com/twistylittlepassagesallalike/2011/04/23/everyone-quotes-command-line-arguments-the-wrong-way/

def _win32_quote_arg(arg):
    if arg and (re.search(r'[ \t\n\v"]', arg) is None):
        return arg
    ret = '"'
    i = 0
    while True:
        num_backslashes = 0
        while i < len(arg) and arg[i] == "\\":
            i += 1
            num_backslashes += 1
        if i == len(arg):
            ret += "\\" * (num_backslashes * 2)
            break
        elif arg[i] == '"':
            ret += "\\" * (num_backslashes * 2 + 1) + arg[i]
        else:
            ret += "\\" * num_backslashes + arg[i]
        i += 1
    return ret + '"'


def _win32_arglist_to_string(arglist: List[str]):
    return " ".join(_win32_quote_arg(arg) for arg in arglist)


def main():
    # escape list of arguments
    command = _win32_arglist_to_string(sys.argv[1:])

    # create job
    hJob = win32job.CreateJobObject(None, '')
    extended_info = win32job.QueryInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation)
    extended_info['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    win32job.SetInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation, extended_info)

    # associate job with completion port
    hIoPort = win32file.CreateIoCompletionPort(
        win32file.INVALID_HANDLE_VALUE, None, 0, 1)
    # pywin32 is missing support for JOBOBJECT_ASSOCIATE_COMPLETION_PORT, therefore
    #   we call it through ctypes
    port = JOBOBJECT_ASSOCIATE_COMPLETION_PORT()
    port.CompletionKey = hJob.handle
    port.CompletionPort = hIoPort.handle
    assert bool(ctypes.windll.kernel32.SetInformationJobObject(
            ctypes.wintypes.HANDLE(hJob.handle),
            ctypes.c_int(JobObjectAssociateCompletionPortInformation),
            ctypes.byref(port),
            ctypes.sizeof(JOBOBJECT_ASSOCIATE_COMPLETION_PORT)))

    # create process suspended
    si = win32process.STARTUPINFO()
    hProcess, hThread, processId, threadId = win32process.CreateProcess(
        None,
        command,
        None,
        None,
        True,
        win32process.CREATE_BREAKAWAY_FROM_JOB | win32process.CREATE_SUSPENDED,
        None,
        None,
        si)

    # add process to job
    win32job.AssignProcessToJobObject(hJob, hProcess)

    # resume process
    win32process.ResumeThread(hThread)
    win32api.CloseHandle(hThread)
    win32api.CloseHandle(hProcess)

    # wait for job termination
    numberOfBytes = ctypes.wintypes.DWORD(0)
    completionKey = ctypes.wintypes.HANDLE(0)
    overlapped = OVERLAPPED()
    while True:
        # calling this through pywin32 crashes the program, therefore we call it through ctypes
        res = bool(ctypes.windll.kernel32.GetQueuedCompletionStatus(
            ctypes.wintypes.HANDLE(hIoPort.handle),
            ctypes.byref(numberOfBytes),
            ctypes.byref(completionKey),
            ctypes.byref(overlapped),
            ctypes.wintypes.DWORD(win32event.INFINITE)))
        if not res or (
                bytes(completionKey) == bytes(ctypes.c_void_p(hJob.handle)) and
                bytes(numberOfBytes) == bytes(ctypes.c_ulong(win32job.JOB_OBJECT_MSG_ACTIVE_PROCESS_ZERO))):
            break


if __name__ == "__main__":
    main()
