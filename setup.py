from os import path
from setuptools import setup, Extension, find_packages

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md")) as f:
    long_description = f.read()

version_namespace = {}
with open(path.join(here, "cpytraceafl/version.py")) as f:
    exec(f.read(), version_namespace)

tracehookmodule = Extension(
    "cpytraceafl._tracehook",
    sources=["cpytraceafl/_tracehookmodule.c"],
)

setup(
    name="cpytraceafl",
    version=version_namespace["__version__"],

    description="CPython bytecode instrumentation and forkserver tools for fuzzing python and mixed python/c code using AFL",
    long_description=long_description,
    long_description_content_type="text/markdown",

    url='https://github.com/risicle/cpytraceafl',

    author="Robert Scott",
    author_email="code@humanleg.org.uk",

    ext_modules=[tracehookmodule],
    packages=find_packages(),
    setup_requires=["pytest-runner"],
    install_requires=["sysv_ipc"],
    tests_require=["pytest"],
    python_requires=">=3.5, <3.9",  # not tested with other versions (yet)
    license='MIT',
)
