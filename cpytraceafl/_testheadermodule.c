#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "cpytraceafl.h"


static PyObject * _test_record_loc(PyObject *self, PyObject *args) {
    uint32_t this_loc;

    if (!PyArg_ParseTuple(args, "I", &this_loc))
        return NULL;

    cpytraceafl_record_loc(this_loc);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef TracehookMethods[] = {
    {
        "_test_record_loc",
        _test_record_loc,
        METH_VARARGS,
        "Method testing cpytraceafl_record_loc"
    },
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef testheadermodule = {
    PyModuleDef_HEAD_INIT,
    // name
    "_testheader",
    // documentation
    "Module to aid in testing use of cpytraceafl's c header interface",
    // per-interpreter state size
    -1,
    TracehookMethods
};

PyMODINIT_FUNC
PyInit__testheader(void)
{
    return PyModule_Create(&testheadermodule);
}
