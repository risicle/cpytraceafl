
def rewrite(dis, code, selector=True):
    code_type = type(code)
    consts = tuple(
        rewrite(dis, const, selector) if isinstance(const, code_type) else const
        for const in code.co_consts
    )

    if selector is True or (selector is not False and selector(code)):
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

        for offset in flagged_offsets:
            offset_delta = offset - last_offset
            lnotab = (
                lnotab
                + (b"\xff\x01" * (offset_delta // 0x100))
                + bytes(((offset_delta % 0x100), 1,))
            )
            last_offset += offset_delta
    else:
        lnotab = b""

    return code_type(
        code.co_argcount,
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
        1,
        lnotab,
        code.co_freevars,
        code.co_cellvars,
    )


def install_rewriter(builtins_module=None, selector=True):
    import dis
    import functools
    import sys
    import _frozen_importlib_external
    if builtins_module is None:
        import builtins
    else:
        builtins = builtins_module

    original_compile = builtins.compile

    @functools.wraps(original_compile)
    def rewriting_compile(*args, **kwargs):
        return rewrite(dis, original_compile(*args, **kwargs), selector)
    builtins.compile = rewriting_compile

    original_compile_bytecode = _frozen_importlib_external._compile_bytecode
    @functools.wraps(original_compile_bytecode)
    def rewriting_compile_bytecode(*args, **kwargs):
        return rewrite(dis, original_compile_bytecode(*args, **kwargs), selector)
    _frozen_importlib_external._compile_bytecode = rewriting_compile_bytecode
