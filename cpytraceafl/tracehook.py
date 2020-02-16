import ctypes
import sys

# this file is simply a facade for the (underscored) native module which ensures the module
# is loaded in a specific way...

# set RTLD_GLOBAL for tracehook import so that afl-instrumented native libs are able to find
# our __afl_area_ptr and __afl_prev_loc globals
_prev_dlopenflags = sys.getdlopenflags()
sys.setdlopenflags(_prev_dlopenflags | ctypes.RTLD_GLOBAL)
from cpytraceafl._tracehook import *
sys.setdlopenflags(_prev_dlopenflags)
