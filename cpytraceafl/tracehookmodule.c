#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdint.h>

#define HASH_PRIME 0xedb6417b

static char* afl_map_start = NULL;
static unsigned char afl_map_size_bits = 16;

static PyObject * tracehook_set_map_start(PyObject *self, PyObject *args) {
    unsigned long long _afl_map_start;

    if (!PyArg_ParseTuple(args, "K", &_afl_map_start))
        return NULL;

    afl_map_start = (char *) _afl_map_start;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * tracehook_set_map_size_bits(PyObject *self, PyObject *args) {
    if (!PyArg_ParseTuple(args, "b", &afl_map_size_bits))
        return NULL;

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
    static __thread uint32_t prev_loc;

    PyObject* frame;
    char* event;
    PyObject* arg;

    if (!PyArg_ParseTuple(args, "OsO", &frame, &event, &arg))
        return NULL;

    // In instrumented code objects, this number is effetively the current basic block number
    // added to the code object's co_firstlineno, which is used as a "base hash" for the code
    // object. Previously we used the raw memory location of the code object for this, but
    // that has the potential to be chaotic if an execution path affects the order in which
    // various memory allocations were made.
    PyObject* f_lineno = PyObject_GetAttrString(frame, "f_lineno");
    if (f_lineno == NULL) return NULL;
    unsigned long lineno = PyLong_AsUnsignedLong(f_lineno);
    Py_DECREF(f_lineno);

    // bytecode offset is also useful & consistent entropy, we'll have that too.
    PyObject* f_lasti = PyObject_GetAttrString(frame, "f_lasti");
    if (f_lasti == NULL) return NULL;
    unsigned long bytecode_offset = PyLong_AsUnsignedLong(f_lasti);
    Py_DECREF(f_lasti);

    // multiplicative hashing - keep most significant bits of a modular multiplication as "hash"
    uint32_t state = HASH_PRIME;
    state *= (uint32_t)lineno;
    state *= (uint32_t)bytecode_offset;

    uint32_t this_loc = state >> (32-afl_map_size_bits);

    afl_map_start[this_loc ^ (prev_loc>>1)]++;
    prev_loc = this_loc;

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
    "tracehook",   /* name of module */
    NULL, /* module documentation, may be NULL */
    -1,       /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
    TracehookMethods
};

PyMODINIT_FUNC
PyInit_tracehook(void)
{
    return PyModule_Create(&tracehookmodule);
}
