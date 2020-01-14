from distutils.core import setup, Extension

tracehookmodule = Extension(
    "tracehook",
    sources=["cpytraceafl/tracehookmodule.c"],
)

setup(
    name = "cpytraceafl",
    version = "0.1",
    description = "Foo",
    ext_modules = [tracehookmodule],
)
