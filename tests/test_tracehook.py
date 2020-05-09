import ctypes
from itertools import repeat
import mmap
from types import FrameType
from unittest import mock

import pytest

from cpytraceafl import tracehook


@pytest.mark.parametrize("map_size_bits,ngram_size,lineno_lasti_pairs,expected_inc_loc", (
    (16, 0, ((123, 234), (345, 456)), 0x19a5,),
    (16, 0, ((124, 234), (345, 456)), 0x7d19,),
    (16, 0, ((567, 678), (123, 234), (345, 456)), 0x19a5,),
    (16, 0, ((0, 0), (0, 0)), 0x9b6d,),
    # alias because of zero-multiplication avoidance, but extremely unlikely in practice
    (16, 0, ((0, 0), (0, 0xffffffff)), 0x9b6d,),
    (16, 0, ((0, 0), (0, 1)), 0x6492,),
    # alias because of symmetry of operations, again extremely unlikely as lineno is usually
    # offset by a startlineno which we seed
    (16, 0, ((0, 0), (1, 0)), 0x6492,),
    (12, 0, ((111, 222), (333, 444)), 0x998,),

    # tests with a non-zero ngram_size must make at least enough calls to flush their full
    # ngram buffer, else result will depend on pre-test state of buffer
    (16, 2, ((567, 678), (123, 234), (345, 456)), 0x25df,),
    (16, 2, ((789, 890), (567, 678), (123, 234), (345, 456)), 0x25df,),
    (16, 3, ((789, 890), (567, 678), (123, 234), (345, 456)), 0x7c5b,),
    (16, 3, ((789, 891), (567, 678), (123, 234), (345, 456)), 0x0f3f,),
))
def test_line_trace_hook(map_size_bits, ngram_size, lineno_lasti_pairs, expected_inc_loc):
    expected_map = bytearray(repeat(0, 1<<map_size_bits))
    expected_map[expected_inc_loc] = 1

    with mmap.mmap(-1, 1<<map_size_bits, flags=mmap.MAP_PRIVATE) as mem:
        first_byte = ctypes.c_byte.from_buffer(mem)
        try:
            tracehook.set_map_start(ctypes.addressof(first_byte))
            tracehook.set_map_size_bits(map_size_bits)
            tracehook.set_ngram_size_bits(ngram_size)

            for lineno, lasti in lineno_lasti_pairs[:-1]:
                mock_frame = mock.create_autospec(
                    FrameType,
                    instance=True,
                    f_lineno=lineno,
                    f_lasti=lasti,
                )
                tracehook.line_trace_hook(mock_frame, "line", mock.Mock())

            # we can't effectively assert the action of the prior calls as they will depend on
            # their *previous* call arguments, so clear it so we can make a clean assertion
            # following the next call
            mem.write(bytes(repeat(0, 1<<map_size_bits)))
            mem.seek(0)

            lineno, lasti = lineno_lasti_pairs[-1]
            mock_frame = mock.create_autospec(
                FrameType,
                instance=True,
                f_lineno=lineno,
                f_lasti=lasti,
            )
            tracehook.line_trace_hook(mock_frame, "line", mock.Mock())

            assert mem.read() == bytes(expected_map)

        finally:
            del first_byte


@pytest.mark.parametrize("value", (1, 128,))
def test_invalid_ngram_size_bits(value):
    with pytest.raises(ValueError):
        tracehook.set_ngram_size_bits(value)


@pytest.mark.parametrize("value", (0, 2, 3,))
def test_valid_ngram_size_bits(value):
    tracehook.set_ngram_size_bits(value)
