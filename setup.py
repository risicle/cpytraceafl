from os import path
from setuptools import setup, Extension, find_packages

here = path.abspath(path.dirname(__file__))

version_namespace = {}
with open(path.join(here, "cpytraceafl/version.py")) as f:
    exec(f.read(), version_namespace)

tracehookmodule = Extension(
    "tracehook",
    sources=["cpytraceafl/tracehookmodule.c"],
)

setup(
    name="cpytraceafl",
    version=version_namespace["__version__"],
    description="CPython bytecode instrumentation and forkserver tools for fuzzing python code using AFL",
    ext_modules=[tracehookmodule],
    packages=find_packages(),
    install_requires=["sysv_ipc"],
    python_requires="==3.7",  # specifically cpython 3.7 - not tested with any other version (yet)
    license='MIT',
)
