from os import path
from setuptools import setup, Extension, find_packages

here = path.abspath(path.dirname(__file__))

version_namespace = {}
with open(path.join(here, "cpytraceafl/version.py")) as f:
    exec(f.read(), version_namespace)

tracehookmodule = Extension(
    "cpytraceafl.tracehook",
    sources=["cpytraceafl/tracehookmodule.c"],
)

setup(
    name="cpytraceafl",
    version=version_namespace["__version__"],
    description="CPython bytecode instrumentation and forkserver tools for fuzzing python code using AFL",
    ext_modules=[tracehookmodule],
    packages=find_packages(),
    setup_requires=["pytest-runner"],
    install_requires=["sysv_ipc"],
    tests_require=["pytest"],
    python_requires=">=3.5, <3.9",  # not tested with other versions (yet)
    license='MIT',
)
