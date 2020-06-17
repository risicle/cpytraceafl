import ctypes
import mmap

import pytest

from cpytraceafl._testheader import _test_record_loc
from cpytraceafl import tracehook


@pytest.mark.parametrize("map_size_bits", (8, 13, 16, 18,))
def test_record_loc_masks_prev_loc(map_size_bits):
    with mmap.mmap(-1, 1<<map_size_bits, flags=mmap.MAP_PRIVATE) as mem:
        first_byte = ctypes.c_byte.from_buffer(mem)
        try:
            tracehook.set_map_start(ctypes.addressof(first_byte))
            tracehook.set_map_size_bits(map_size_bits)

            # simulate a tool using the c header interface to record a loc, not masking its
            # loc to the map size
            _test_record_loc(0xdeadbeef)

            # fortunately `pythonapi` is lenient enough to just let us peek on any of our
            # internal symbols
            __afl_prev_loc = ctypes.c_uint32.in_dll(ctypes.pythonapi, "__afl_prev_loc")

            # check any tool taking __afl_prev_loc as a map location directly won't address
            # beyond our allocated map
            assert __afl_prev_loc.value < (1<<map_size_bits)

        finally:
            del first_byte
