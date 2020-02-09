import ctypes
from itertools import repeat
import mmap
from types import FrameType
from unittest import mock

import pytest

from cpytraceafl import tracehook


@pytest.mark.parametrize("map_size_bits,lineno0,lasti0,lineno1,lasti1,expected_inc_loc", (
    (16, 123, 234, 345, 456, 0x19a5,),
    (16, 124, 234, 345, 456, 0x7d19,),
    (16, 0, 0, 0, 0, 0x9b6d,),
    # alias because of zero-multiplication avoidance, but extremely unlikely in practice
    (16, 0, 0, 0, 0xffffffff, 0x9b6d,),
    (16, 0, 0, 0, 1, 0x6492,),
    # alias because of symmetry of operations, again extremely unlikely as lineno is usually
    # offset by a startlineno which we seed
    (16, 0, 0, 1, 0, 0x6492,),
    (12, 111, 222, 333, 444, 0x998,),
))
def test_line_trace_hook(map_size_bits, lineno0, lasti0, lineno1, lasti1, expected_inc_loc):
    expected_map = bytearray(repeat(0, 1<<map_size_bits))
    expected_map[expected_inc_loc] = 1

    with mmap.mmap(-1, 1<<map_size_bits, flags=mmap.MAP_PRIVATE) as mem:
        first_byte = ctypes.c_byte.from_buffer(mem)
        try:
            tracehook.set_map_start(ctypes.addressof(first_byte))
            tracehook.set_map_size_bits(map_size_bits)

            mock_frame0 = mock.create_autospec(
                FrameType,
                instance=True,
                f_lineno=lineno0,
                f_lasti=lasti0,
            )
            tracehook.line_trace_hook(mock_frame0, "line", mock.Mock())

            # we can't effectively assert the action of the first call as it will depend on
            # its *previous* call arguments, so clear it so we can make a clean assertion
            # following the next call
            mem.write(bytes(repeat(0, 1<<map_size_bits)))
            mem.seek(0)

            mock_frame1 = mock.create_autospec(
                FrameType,
                instance=True,
                f_lineno=lineno1,
                f_lasti=lasti1,
            )
            tracehook.line_trace_hook(mock_frame1, "line", mock.Mock())

            assert mem.read() == expected_map
        finally:
            del first_byte
