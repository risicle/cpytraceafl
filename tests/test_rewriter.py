import builtins
import dis
from itertools import chain, count
import random
import sys
from types import CodeType
from unittest import mock

import pytest

from cpytraceafl import rewriter


pv = sys.version_info[:2]


test_source = """
foo = bar + 1

def baz(a, b=(foo*2)):
    a -= b
    try:
        import d
        for c in e(1):
            d.g[1:3] = d.h(c)
            if not e:
                del d[1]
                continue
            yield e(c).f[0]
        else:
            if d[2]:
                raise ValueError
    finally:
        if a < 2:
            a += b
        if b >= 2 or foo:
            raise StopIteration

    def qux(i, **j):
        i.oof += i("oof")[0]
        try:
            i.oof(j["rab"], len(j), lambda l: l or (i % 2))
        except XYZException as e:
            print(e)
        return i

    while a > b:
        a -= [a[0] or b[a] for k in bar(123)]
        yield qux(a and 321)
        if b:
            break

def zab(x, y, z, *w):
    z, _ = x if y(z) else w + "xuq"
    try:
        return (v(z) if v.y else v(y) for v in w if v and v({}))
    except A:
        return x()
    except B:
        return y()
    except C:
        return w[0]()
    finally:
        z[0] = 2
"""


def _extract_lnotabs(code_obj):
    return (
        tuple(_extract_lnotabs(const) for const in code_obj.co_consts if isinstance(const, CodeType)),
        code_obj.co_lnotab,
    )


# allows a compact way of representing a lnotab bytestring, handling interleaving & conversion
def _l(*a):
    return bytes(chain.from_iterable((b, 1) for b in a))


@pytest.mark.parametrize("selector,expected_lnotabs", tuple(chain.from_iterable(
    # keep together a number of "aliases" of a selector that should result in the same output
    ((selector, expected_lnotabs) for selector in selector_aliases)
    for selector_aliases, expected_lnotabs in (
        (
            (True, lambda _: True, 100, lambda _: 100, 99.99, lambda _: 99.99, 1000,),
            (
                (
                    (
                        (
                            (
                                (
                                    # lambda
                                    ((), _l(0, 6, 7,) if pv < (3, 6) else _l(0, 4, 6,)),
                                ),
                                # qux
                                (
                                    _l(0, 73, 10, 23, 13, 1,)
                                    if pv < (3, 6) else (
                                        _l(0, 58, 8, 22, 10, 2,)
                                        if pv < (3, 7) else
                                        _l(0, 58, 8, 20, 12, 2,)
                                    )
                                ),
                            ),
                            # listcomp
                            ((), _l(0, 6, 16, 7, 6,) if pv < (3, 6) else _l(0, 4, 12, 6, 4,),),
                        ),
                        # baz
                        (
                            _l(0, 38, 40, 10, 17, 4, 11, 6, 4, 12, 10, 12, 6, 6, 16, 12, 47, 3, 4, 7, 4, 1,)
                            if pv < (3, 6) else (
                                _l(0, 28, 28, 8, 14, 4, 10, 4, 4, 8, 8, 8, 4, 4, 12, 8, 34, 2, 4, 6, 4, 2,)
                                if pv < (3, 8) else
                                _l(0, 26, 28, 8, 14, 4, 8, 4, 4, 8, 8, 8, 4, 4, 10, 8, 34, 2, 4, 6, 4,)
                            )
                        ),
                    ),
                    (
                        (
                            # genexpr
                            (
                                (),
                                (
                                    _l(0, 3, 12, 12, 9, 12, 9, 1, 4,)
                                    if pv < (3, 6) else
                                    _l(0, 2, 8, 8, 6, 8, 6, 2, 4,)
                                ),
                            ),
                        ),
                        # zab
                        (
                            _l(0, 12, 6, 7, 45, 10, 14, 10, 14, 10, 18, 1, 4,)
                            if pv < (3, 6) else (
                                _l(0, 8, 4, 6, 30, 8, 12, 8, 12, 8, 16, 6,)
                                if pv < (3, 8) else
                                _l(0, 8, 4, 6, 36, 8, 20, 8, 20, 8, 24, 6,)
                            )
                        ),
                    ),
                ),
                # module
                _l(0,),
            ),
        ),
        (
            (False, lambda _: False, 0, lambda _: 0,),
            (
                (
                    (
                        (
                            (
                                (
                                    # lambda
                                    ((), b""),
                                ),
                                # qux
                                b"",
                            ),
                            # listcomp
                            ((), b"",),
                        ),
                        # baz
                        b"",
                    ),
                    (
                        (
                            # genexpr
                            ((), b"",),
                        ),
                        # zab
                        b"",
                    ),
                ),
                # module
                b"",
            ),
        ),
        (
            (
                lambda code: code.co_name in ("baz", "zab"),
                lambda code: 100 if code.co_name in ("baz", "zab") else 0,
            ),
            (
                (
                    (
                        (
                            (
                                (
                                    # lambda
                                    ((), b""),
                                ),
                                # qux
                                b"",
                            ),
                            # listcomp
                            ((), b"",),
                        ),
                        # baz
                        (
                            _l(0, 38, 40, 10, 17, 4, 11, 6, 4, 12, 10, 12, 6, 6, 16, 12, 47, 3, 4, 7, 4, 1,)
                            if pv < (3, 6) else (
                                _l(0, 28, 28, 8, 14, 4, 10, 4, 4, 8, 8, 8, 4, 4, 12, 8, 34, 2, 4, 6, 4, 2,)
                                if pv < (3, 8) else
                                _l(0, 26, 28, 8, 14, 4, 8, 4, 4, 8, 8, 8, 4, 4, 10, 8, 34, 2, 4, 6, 4,)
                            )
                        ),
                    ),
                    (
                        (
                            # genexpr
                            ((), b"",),
                        ),
                        # zab
                        (
                            _l(0, 12, 6, 7, 45, 10, 14, 10, 14, 10, 18, 1, 4,)
                            if pv < (3, 6) else (
                                _l(0, 8, 4, 6, 30, 8, 12, 8, 12, 8, 16, 6,)
                                if pv < (3, 8) else
                                _l(0, 8, 4, 6, 36, 8, 20, 8, 20, 8, 24, 6,)
                            )
                        ),
                    ),
                ),
                # module
                b"",
            ),
        ),
        (
            (20, lambda _: 20,),
            (
                (
                    (
                        (
                            (
                                (
                                    # lambda
                                    ((), b"",),
                                ),
                                # qux
                                _l(0,),
                            ),
                            # listcomp
                            ((), b"",),
                        ),
                        # baz
                        (
                            _l(0, 38, 88, 66, 77, 1,)
                            if pv < (3, 6) else (
                                _l(0, 28, 68, 48, 58, 2,)
                                if pv < (3, 8) else
                                _l(0, 26, 66, 46, 58,)
                            )
                        ),
                    ),
                    (
                        (
                            # genexpr
                            ((), _l(48,) if pv < (3, 6) else _l(32,),),
                        ),
                        # zab
                        (
                            _l(80, 14, 57,)
                            if pv < (3, 6) else (
                                _l(56, 12,)
                                if pv < (3, 8) else
                                _l(62, 20,)
                            )
                        ),
                    ),
                ),
                # module
                _l(0,),
            ),
        ),
    )
)))
def test_rewrite(selector, expected_lnotabs):
    orig_code = builtins.compile(test_source, "foo.py", "exec")

    def mk_mock_random_instance(code_obj):
        # a simple pseudo-pseudo-random number generator "seeded" on the co_firstlineno of
        # the provided code object - something that shouldn't be volatile between python
        # versions.
        # a new mock random instance is created for each use to confine the state of the
        # generator to one code object, limiting the amount changes in calling patterns can
        # propagate.
        inst = mock.create_autospec(random.Random, instance=True)
        inst_counter = count(code_obj.co_firstlineno, 19)
        inst.getrandbits.side_effect = lambda bits: next(inst_counter) % (1<<bits)
        return inst

    mock_random_class = mock.create_autospec(random.Random, side_effect=mk_mock_random_instance)

    rewritten = rewriter.rewrite(sys.version_info, dis, mock_random_class, orig_code, selector)

    assert _extract_lnotabs(rewritten) == expected_lnotabs
