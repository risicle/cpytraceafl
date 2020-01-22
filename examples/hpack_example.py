from cpytraceafl.rewriter import install_rewriter

install_rewriter()

import hpack

# initial call to set up any internal caches or imports before the fork
d = hpack.Decoder()
d.decode(b'\x82\x86\x84\x01\x8c\xf1\xe3\xc2\xe5\xf2:k\xa0\xab\x90\xf4\xff')
d.decode(
    b'\x82\x86\x84\x01\x8c\xf1\xe3\xc2\xe5\xf2:k\xa0\xab\x90\xf4\xff'
    b'\x0f\t\x86\xa8\xeb\x10d\x9c\xbf'
)

import sys
from cpytraceafl import fuzz_from_here, crashing_excepthook

fuzz_from_here(excepthook=crashing_excepthook)

with open(sys.argv[1], "rb") as f:
    try:
        d = hpack.Decoder()
        # we have inserted the sentinel 0xdeadbeef into our examples as a marker signifying
        # a new part of a differentially encoded header
        for fragment in f.read().split(b"\xde\xad\xbe\xef"):
            if fragment:
                d.decode(fragment)
    except hpack.HPACKDecodingError:
        pass
