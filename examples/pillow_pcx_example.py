"""
    An example of mixed python/c code fuzzing. In this case, it is assumed that the Pillow
    package in use has been compiled with e.g. afl's llvm_mode..
"""
from cpytraceafl.rewriter import install_rewriter

install_rewriter()

from cpytraceafl import fuzz_from_here, DEFAULT_MAP_SIZE_BITS, get_map_size_bits_env
# must ensure the tracehook module gets imported *before* any instrumented native modules,
# so that the __afl_area_ptr and __afl_prev_loc global symbols have been loaded
from cpytraceafl.tracehook import set_map_start
import sysv_ipc

# if we're going to "warm up" the code under test in a way that executes native instrumented
# code *before* we do the fork & start tracing, we need to provide a dummy memory area for
# __afl_area_ptr to point to. here, use some fresh sysv shared memory because it's what we
# have to hand.
map_size_bits = get_map_size_bits_env() or DEFAULT_MAP_SIZE_BITS
dummy_sm = sysv_ipc.SharedMemory(None, size=1<<map_size_bits, flags=sysv_ipc.IPC_CREX)
set_map_start(dummy_sm.address)

import PIL
# we only want to exercise the PCX code for now: unregister all other plugins so our input
# doesn't get recognized as those formats. not getting recognized as a PCX should just lead to
# a single boring path that doesn't distract the fuzzing process.
PIL._plugins[:] = ["PcxImagePlugin"]

from PIL import Image
import codecs
from io import BytesIO
import sys
# warm up code under test, ensure lazy imports are performed and internal caches are populated.
Image.open(BytesIO(codecs.decode(
    "0A05010100000000570033004001C800000000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00010C0000003400000000000000"
    "000000000000000000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000CB0077CC77CC77CB7700CB0077CC77CC77CB7700CB0077CC77CC77CB"
    "7700CB0077CC77CC77CB7700CB0077CC77CC77CB7700CB0077CC77CC77CB7700CB0077CC77CC77"
    "CB7700CB0077CC77CC77CB7700CB0077CC77CC77CB7700CB0077CC77CC77CB7700CB0077CC77CC"
    "77CB7700CB0077CC77CC77CB7700CB0077CC77CC77CB7776CBFF77",
    "hex",
))).getdata()

fuzz_from_here()

with open(sys.argv[1], "rb") as f:
    try:
        Image.open(f).getdata()
    except Exception:
        # in this case, a python exception isn't the end of the world - we're after crashers
        pass
