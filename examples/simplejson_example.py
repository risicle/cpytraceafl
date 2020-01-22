from cpytraceafl.rewriter import install_rewriter

install_rewriter(selector=lambda code: "simplejson" in code.co_filename)

import simplejson

# we want to fuzz the python implementation, not the c extension
simplejson._toggle_speedups(False)
# initial call to set up any internal caches or imports before the fork
simplejson.loads('{"foo": "bar", "baz": ["qux", 123, false]}')

import sys
from cpytraceafl import fuzz_from_here

fuzz_from_here()

with open(sys.argv[1], "rb") as f:
    try:
        simplejson.loads(f.read())
    except simplejson.JSONDecodeError:
        pass
