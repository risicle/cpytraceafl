import ctypes
import os
import signal
import struct
import sys

import sysv_ipc

from cpytraceafl import tracehook


# these values *must* agree with those set in afl's config.h, and also those used when compiling
# any instrumented native modules
FORKSRV_FD = 198
DEFAULT_MAP_SIZE_BITS = 16
DEFAULT_SHM_ENV_VAR = "__AFL_SHM_ID"

MAP_SIZE_ENV_VAR = "AFL_MAP_SIZE"
NGRAM_SIZE_ENV_VAR = "AFL_NGRAM_SIZE"


def get_map_size_bits_env():
    if MAP_SIZE_ENV_VAR in os.environ:
        map_size = int(os.environ[MAP_SIZE_ENV_VAR])
        map_size_bits = map_size.bit_length() - 1
        if 1<<map_size_bits != map_size:
            raise ValueError("Non-power-of-two AFL_MAP_SIZE not supported")
        return map_size_bits


def install_trace_hook(map_start_addr, map_size_bits=None, ngram_size=None):
    if map_size_bits is None:
        map_size_bits = get_map_size_bits_env() or DEFAULT_MAP_SIZE_BITS
    if ngram_size is None:
        ngram_size = int(os.environ.get(NGRAM_SIZE_ENV_VAR, 0))

    tracehook.set_map_start(map_start_addr)
    tracehook.set_map_size_bits(map_size_bits)
    tracehook.set_ngram_size(ngram_size)

    sys.settrace(tracehook.global_trace_hook)


def attach_afl_map_shm(shm_env_var=None):
    shm_env_var = shm_env_var or DEFAULT_SHM_ENV_VAR
    shm = sysv_ipc.attach(int(os.environ[shm_env_var]))
    shm.write(b"\x01", offset=0)
    return shm


def cheap_excepthook(exc_class, exc, traceback):
    "An excepthook which won't waste any time rendering a traceback"
    sys.exit(99)


def crashing_excepthook(exc_class, exc, traceback):
    "An excepthook which will raise a genuine segfault, easy for AFL to detect as a 'crash'"
    ctypes.memset(0, 1, 1)


def forkserver(forksrv_read_fd=None, forksrv_write_fd=None):
    """
        Attempt to start forkserver for AFL, if successful, parent process will never
        return, child will return True. If not successful, parent will return False.
    """
    forksrv_read_fd = forksrv_read_fd or FORKSRV_FD
    forksrv_write_fd = forksrv_write_fd or (forksrv_read_fd + 1)

    try:
        forksrv_reader = open(forksrv_read_fd, "rb", buffering=0)
        forksrv_writer = open(forksrv_write_fd, "wb", buffering=0)
    except OSError:
        # don't run a forkserver
        return False

    # tell parent we're alive
    forksrv_writer.write(b"\0" * 4)

    while True:
        # check parent is alive
        forksrv_reader.read(4)

        child_pid = os.fork()

        if not child_pid:
            # we are the child
            forksrv_reader.close()
            forksrv_writer.close()
            return True

        # we are the parent. continue in loop forever.
        forksrv_writer.write(struct.pack("I", child_pid))
        _, child_exit_status = os.waitpid(child_pid, 0)
        forksrv_writer.write(struct.pack("I", child_exit_status))


def fuzz_from_here(excepthook=cheap_excepthook):
    """
        Shortcut to setup & start forkserver on parent process, Child processes will return
        from this function with tracing started. Will also install `excepthook` if provided.
    """
    shm = attach_afl_map_shm()
    forked = forkserver()
    install_trace_hook(shm.address)
    if excepthook:
        sys.excepthook = excepthook
    return forked
