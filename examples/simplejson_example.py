from cpytraceafl.rewriter import install_rewriter

install_rewriter(selector=lambda code: "simplejson" in code.co_filename)

import simplejson

simplejson._toggle_speedups(False)
simplejson.loads('{"foo": "bar", "baz": ["qux", 123, false]}')

import sys
from cpytraceafl import fuzz_from_here

fuzz_from_here()

with open(sys.argv[1], "rb") as f:
    try:
        simplejson.loads(f.read())
    except simplejson.JSONDecodeError:
        pass
