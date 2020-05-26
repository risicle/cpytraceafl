#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "cpytraceafl.h"

#define HASH_PRIME 0xedb6417b

unsigned char afl_map_size_bits = 16;
unsigned char afl_ngram_size = 0;

char* __afl_area_ptr = NULL;

// non-ngram-aware AFL should be able to interpret this symbol as a
// plain old uint32 and work fine
__thread afl_prev_loc_vector_t __afl_prev_loc;

// needed by AFL++'s context sensitive coverage feature
__thread uint32_t __afl_prev_ctx;

static PyObject * tracehook_set_map_start(PyObject *self, PyObject *args) {
    unsigned long long _afl_map_start;

    if (!PyArg_ParseTuple(args, "K", &_afl_map_start))
        return NULL;

    __afl_area_ptr = (char *) _afl_map_start;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * tracehook_set_map_size_bits(PyObject *self, PyObject *args) {
    if (!PyArg_ParseTuple(args, "b", &afl_map_size_bits))
        return NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * tracehook_set_ngram_size(PyObject *self, PyObject *args) {
    unsigned char ngram_size;
    if (!PyArg_ParseTuple(args, "b", &ngram_size))
        return NULL;

    if (ngram_size != 0 && (ngram_size < 2 || ngram_size > NGRAM_SIZE_MAX)) {
        PyErr_SetString(PyExc_ValueError, "ngram size must be 0 or between 2 and NGRAM_SIZE_MAX");
        return NULL;
    }

    afl_ngram_size = ngram_size;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * tracehook_global_trace_hook(PyObject *self, PyObject *args) {
    PyObject* frame;
    char* event;
    PyObject* arg;

    if (!PyArg_ParseTuple(args, "OsO", &frame, &event, &arg))
        return NULL;

    if (!strcmp(event, "call")) {
        PyObject* code = PyObject_GetAttrString(frame, "f_code");
        if (code == NULL) return NULL;
        PyObject* lnotab = PyObject_GetAttrString(code, "co_lnotab");
        Py_DECREF(code);
        if (lnotab == NULL) return NULL;
        Py_ssize_t len = PyObject_Length(lnotab);
        Py_DECREF(lnotab);
        if (len > 0) {  // else this is not a function we're interested in
            PyObject* line_trace_hook = PyObject_GetAttrString(self, "line_trace_hook");
            if (line_trace_hook == NULL) return NULL;
            Py_INCREF(line_trace_hook);
            return line_trace_hook;
        }
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * tracehook_line_trace_hook(PyObject *self, PyObject *args) {
    PyObject* frame;
    char* event;
    PyObject* arg;

    if (!PyArg_ParseTuple(args, "OsO", &frame, &event, &arg))
        return NULL;

    // In instrumented code objects, this number is effectively the current basic block number
    // added to the code object's co_firstlineno (which is used as a "base hash" for the code
    // object). Previously we used the raw memory location of the code object for this, but
    // that has the potential to be chaotic if an execution path affects the order in which
    // various memory allocations are made.
    PyObject* f_lineno = PyObject_GetAttrString(frame, "f_lineno");
    if (f_lineno == NULL) return NULL;
    uint32_t lineno = (uint32_t)PyLong_AsUnsignedLong(f_lineno);
    Py_DECREF(f_lineno);

    // bytecode offset is also useful & consistent entropy - we'll have that too.
    PyObject* f_lasti = PyObject_GetAttrString(frame, "f_lasti");
    if (f_lasti == NULL) return NULL;
    uint32_t bytecode_offset = (uint32_t)PyLong_AsUnsignedLong(f_lasti);
    Py_DECREF(f_lasti);

    if (!lineno)  // avoid zero multiplication
        lineno = ~(uint32_t)0;
    if (!bytecode_offset)  // avoid zero multiplication
        bytecode_offset = ~(uint32_t)0;

    // multiplicative hashing - keep most significant bits of a modular multiplication as "hash"
    uint32_t state = HASH_PRIME;
    state *= lineno;
    state *= bytecode_offset;

    cpytraceafl_record_loc(state >> (32-afl_map_size_bits));

    PyObject* line_trace_hook = PyObject_GetAttrString(self, "line_trace_hook");
    if (line_trace_hook == NULL) return NULL;
    Py_INCREF(line_trace_hook);
    return line_trace_hook;
}

static PyMethodDef TracehookMethods[] = {
    {
        "set_map_start",
        tracehook_set_map_start,
        METH_VARARGS,
        "Set start address of AFL shared memory region"
    },
    {
        "set_map_size_bits",
        tracehook_set_map_size_bits,
        METH_VARARGS,
        "Set log2 of size of AFL shared memory region"
    },
    {
        "set_ngram_size",
        tracehook_set_ngram_size,
        METH_VARARGS,
        "Set number of branches to remember, 0 to disable ngram mode"
    },
    {
        "global_trace_hook",
        tracehook_global_trace_hook,
        METH_VARARGS,
        "Global tracehook callable for passing to sys.settrace()"
    },
    {
        "line_trace_hook",
        tracehook_line_trace_hook,
        METH_VARARGS,
        "'line' tracehook callable, returned by global_trace_hook when appropriate"
    },
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef tracehookmodule = {
    PyModuleDef_HEAD_INIT,
    // name
    "_tracehook",
    // documentation
    NULL,
    // per-interpreter state size
    -1,
    TracehookMethods
};

PyMODINIT_FUNC
PyInit__tracehook(void)
{
    return PyModule_Create(&tracehookmodule);
}
