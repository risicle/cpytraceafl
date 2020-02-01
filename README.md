# cpytraceafl

CPython bytecode instrumentation and forkserver tools for fuzzing python code using AFL.

The tools in this repository enable coverage-guided fuzzing of pure python code using
[American Fuzzy Lop](https://github.com/google/AFL) (even better,
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
