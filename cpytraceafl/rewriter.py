INST_RATIO_PRECISION_BITS = 7


# here we rely on injected dependencies, the `dis` module and the class `ramdom.Random`,
# because of the risk of recursion during import. we avoid module-level imports so we can
# ensure we're only importing whatever's strictly necessary before the rewriter has been
# installed
def rewrite(python_version, dis, random_class, code, selector=True):
    code_type = type(code)
    consts = tuple(
        rewrite(python_version, dis, random_class, const, selector) if isinstance(const, code_type) else const
        for const in code.co_consts
    )

    selection = selector(code) if callable(selector) else selector

    if selection is True:
        inst_sel = True
    elif not selection:
        inst_sel = False
    else:
        # use (hash of) code object to seed the random instance
        rng = random_class(code)
        inst_sel = lambda: (
            rng.getrandbits(INST_RATIO_PRECISION_BITS) <= (
                (1<<INST_RATIO_PRECISION_BITS) * selection/100
            )
        )

    if inst_sel:
        # inspired by Ned Batchelder's "wicked hack" detailed at
        # https://nedbatchelder.com/blog/200804/wicked_hack_python_bytecode_tracing.html, we
        # abuse the code object's "lnotab" or line-number table to trick cpython's line-by-line
        # tracing mechanism to call a tracehook in places we choose. in this case, we decide
        # to denote these "new lines" as starting at the beginning of "basic blocks", or at
        # least a rough approximation of basic blocks as far as they apply to the cpython vm.
        delayed_flag_opcodes = tuple(dis.opmap[m] for m in (
            "YIELD_VALUE",
            "YIELD_FROM",
            "POP_JUMP_IF_TRUE",
            "POP_JUMP_IF_FALSE",
            "JUMP_IF_TRUE_OR_POP",
            "JUMP_IF_FALSE_OR_POP",
        ))

        flagged_offsets = []
        flag_next_instr = True
        for instr in dis.Bytecode(code):
            if flag_next_instr or instr.is_jump_target:
                flagged_offsets.append(instr.offset)

            flag_next_instr = instr.opcode in delayed_flag_opcodes

        lnotab = b""
        last_offset = 0

        for offset in (
            fo for fo in flagged_offsets
            if inst_sel is True or inst_sel()
        ):
            offset_delta = offset - last_offset
            lnotab = (
                lnotab
                + (b"\xff\x01" * (offset_delta // 0x100))
                + bytes(((offset_delta % 0x100), 1,))
            )
            last_offset += offset_delta
    else:
        # a blank lnotab signals to the trace hook that we don't want line tracing here
        lnotab = b""

    code_args = (
        code.co_argcount,
    ) + (() if python_version[:2] < (3, 8) else (code.co_posonlyargcount,)) + (
        code.co_kwonlyargcount,
        code.co_nlocals,
        code.co_stacksize,
        code.co_flags,
        code.co_code,
        consts,
        code.co_names,
        code.co_varnames,
        code.co_filename,
        code.co_name,
        # construct co_firstlineno - this value effectively gets used as the "base hash" for
        # the identity of instrumentation points in the code object. we mix in the original
        # co_filename and co_firstlineno as these are not included in PyCodeObject's hash
        # implementation and we want to reduce the possibility of aliases as much as possible.
        # note the use of hash() here makes use of PYTHONHASHSEED critical when fuzzing
        abs(hash(code) ^ hash(code.co_filename) ^ code.co_firstlineno) & 0xffff,
        lnotab,
        code.co_freevars,
        code.co_cellvars,
    )

    return code_type(*code_args)


def install_rewriter(selector=None):
    """
        Installs instrumenting bytecode rewriter.

        Monkeypatches builtins.compile and importlib's .pyc file reader with wrapper which will
        rewrite code object's line number information in a way suitable for basic block
        tracing.

        This should be called as early as possible in a target program - any imports performed
        before the rewriter is installed will cause their modules to not be properly rewritten
        and so not properly traced.

        `selector` can be used to control which code objects are instrumented and to what
        degree. This can be a callable which takes a single argument, `code`, the code object
        about to be rewritten. This callable should return:
         - True, to indicate the code object should be fully instrumented for tracing.
         - False, indicating the code object should receive no instrumentation and tracing
           should not happen here.
         - A numeric value indicating the approximate percentage of potential locations that
           should be instrumented for this code. This equates approximately to AFL_INST_RATIO.

        Alternatively `selector` can be set to one of the above values to act on all code
        objects with that behaviour equally.

        The default, None, will attempt to read the environment variable AFL_INST_RATIO and
        apply that behaviour to all code. Failing that, it'll instrument everything 100%.
    """
    # nested imports rather than module level imports to be as precise as possible about what
    # is needed for each function to operate. a module unnecessarily imported before the
    # rewriter has been installed is another module that will have inaccurate instrumentation.
    import dis
    import functools
    import random
    import os
    import _frozen_importlib_external
    import builtins
    from sys import version_info

    if selector is None:
        afl_inst_ratio = os.environ.get("AFL_INST_RATIO")
        selector = int(afl_inst_ratio) if afl_inst_ratio else True

    original_compile = builtins.compile

    # why monkeypatch when importlib has provided a comprehensive overridable import system
    # implementation through sys.path_hooks? we want to be able to work with the environment's
    # existing importer setup rather than mandating a single special importer of our own, which
    # could be bypassed with the addition of another importer to path_hooks, leading to
    # weird situations. why not wrap the system's existing path_hooks in-place? due to the
    # architecture of InspectLoaders and ModuleSpecs etc. this would require wrappers of
    # object proxies of wrappers of object proxies...

    @functools.wraps(original_compile)
    def rewriting_compile(*args, **kwargs):
        return rewrite(version_info, dis, random.Random, original_compile(*args, **kwargs), selector)
    builtins.compile = rewriting_compile

    original_compile_bytecode = _frozen_importlib_external._compile_bytecode
    @functools.wraps(original_compile_bytecode)
    def rewriting_compile_bytecode(*args, **kwargs):
        return rewrite(version_info, dis, random.Random, original_compile_bytecode(*args, **kwargs), selector)
    _frozen_importlib_external._compile_bytecode = rewriting_compile_bytecode
