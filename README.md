# cpytraceafl

CPython bytecode instrumentation and forkserver tools for fuzzing python code using AFL.

The tools in this repository enable coverage-guided fuzzing of pure python and mixed python/c
code using [American Fuzzy Lop](https://github.com/google/AFL) (even better,
[AFL++](https://github.com/vanhauser-thc/AFLplusplus)).

There are three main parts to this:

 - A bytecode rewriter using a technique inspired by inspired by Ned Batchelder's "wicked hack"
   detailed at https://nedbatchelder.com/blog/200804/wicked_hack_python_bytecode_tracing.html.
   In this case, the rewriter identifies "basic blocks" in the python bytecode and abuses the
   `code` object's `lnotab` (line-number table) to mark each basic block as a new "line".
   These new "lines" are what trigger CPython's line-level trace hooks. The result of this being
   that we can get our trace hook executed on every new basic block.
 - A minimal & fast tracehook written in C, tallying visited locations to sysv shared memory.
 - A basic forkserver implementation.

Preparing code for fuzzing involves a couple of steps. The first thing that should happen in
the python process is a call to `install_rewriter()`. It's important that this is done very
early as any modules that are imported before this will not be properly instrumented.

```python
from cpytraceafl.rewriter import install_rewriter

install_rewriter()
```

`install_rewriter()` can optionally be provided with a `selector` controlling which code objects
are instrumented and to what degree.

Following this, modules can be imported as normal and will be instrumented by the monkeypatched
`compile` functions. It's usually a good idea to initialize the test environment next, 
performing as many setup procedures as possible before the input file is read. This may
include doing an initial run of the function under test to ensure any internal imports or caches
are set up. This is because we want to minimize work that has to be done post-fork - any work
done now only has to be done once,

After calling

```python
from cpytraceafl import fuzz_from_here

fuzz_from_here()
```

the `fork()` will have been made and tracing started. You now simply read your input file and
call your function under test.

Examples for fuzzing some common packages are provided in [examples/](./examples/).

As for hooking this script up to AFL, I tend to use the included
[dummy-afl-qemu-trace](./dummy-afl-qemu-trace) shim script to fool AFL's QEmu mode into
communicating directly with the python process.

## Fuzzing mixed python/c code

As of version 0.4.0, `cpytraceafl` can gather trace information from C extension modules that
have been compiled with AFL instrumentation (e.g. using `llvm_mode`). This means that it can
be used to seamlessly fuzz projects which have a mix of python and C "speedups". This is
important not only because a lot of python format-parsing packages use this approach, but
because issues revealed in native code are far more likely to have security implications.

Including instrumented native code requires a little more care when preparing a target for
fuzzing. For instance, it's important to ensure the `cpytraceafl.tracehook` module has been
imported and it has had its `set_map_start(...)` function provided with a valid memory
area *before* any instrumented extension modules are loaded. This is because simply loading an
instrumented native module will cause it to attempt to log its execution trace somewhere.

The example [pillow_pcx_example.py](./examples/pillow_pcx_example.py) demonstrates a fuzzing
target taking the necessary precautions into account.

It's possible that you're _only_ interested in tracing the native code, using `cpytraceafl`
just as a driver, in which case you can omit the early `install_rewriter()` call and all
the weirdness involved with that.

## Q & A

### Is there any point in fuzzing python? Isn't it too slow?

Well, yes and no. My experience has been that fuzzing python code is simply "a bit different"
from fuzzing native code - you tend to be looking for different things. In terms of raw speed,
fuzzing python is certainly not fast, but iteration rates I tend to work with aren't completely
dissimilar to what I'm used to getting with AFL's Qemu mode (of course, no two fuzzing targets
are really directly comparable).

Because of the memory-safe nature of pure python code, it's also more uncommon for issues
uncovered through fuzzing to be security issues - logical flaws in parsing tend to lead to
unexpected/unhandled exceptions. So it's still a rather useful tool in simply looking for bugs.
It can be used, for example, to generate a corpus of example inputs for your test suite which
exercise a large amount of the code.

### Does basic block analysis make any sense for python code?

From a rigorous academic stance, and for some uses, possibly not - you've got to keep in mind
that half the bytecode instructions could result in calls out to more arbitrary python or
(uninstrumented) native code that could have arbitrary side effects. But for our needs it works
well enough (recall that AFL coverage analysis is robust to random instrumentation
sites being omitted through `AFL_INST_RATIO` or `AFL_INST_LIBS`).

### Doesn't abusing `lnotab` break python's debugging mechanisms?

Absolutely it does. Don't use instrumented programs to debug problematic cases - use it to
generate problematic inputs. Analyze them with instrumentation turned off.

### I'm getting `undefined symbol: __afl_area_ptr`

Looks like you're trying to import an (instrumented) native extension module before the
`cpytraceafl.tracehook` module has been loaded (which is what provides that symbol).

### I'm getting Segmentation Faults after importing an instrumented native module

You probably also need to provide `cpytraceafl.tracehook.set_map_start(...)` with a valid
writeable memory area before the import. Assuming you're not interested in the trace associated
with the import process, this can just be a dummy which you later discard. I'd recommend either
using an `mmap` object or `sysv_ipc.SharedMemory`. When `fuzz_from_here()` is called, this will
be replaced with right one.

It's also possible the instrumented module was built with a different AFL `MAP_SIZE_POW2` from
that in `cpytraceafl.MAP_SIZE_BITS`.
