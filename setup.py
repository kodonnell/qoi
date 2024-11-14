import os
import sys

import numpy as np
import setuptools_scm  # noqa: F401 - to avoid version = 0.0.0 errors if built without setuptools_scm installed
from setuptools import Extension, setup

USE_CYTHON = os.getenv("USE_CYTHON") == "1"

try:
    from Cython.Build import cythonize
    from Cython.Compiler.Version import version as cython_version
    from packaging.version import Version
except ImportError:
    cythonize = None
    if USE_CYTHON:
        raise RuntimeError("You've set USE_CYTHON=1 but don't have Cython installed!")


# https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html#distributing-cython-modules
def no_cythonize(extensions, **_ignore):
    for extension in extensions:
        sources = []
        for sfile in extension.sources:
            path, ext = os.path.splitext(sfile)
            if ext in (".pyx", ".py"):
                ext = ".c"
                sfile = path + ext
            sources.append(sfile)
        extension.sources[:] = sources
    return extensions

define_macros=[("QOI_MALLOC", "PyMem_RawMalloc"), ("QOI_FREE", "PyMem_RawFree"), ("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")]
if (
    sys.version_info > (3, 13, 0)
    and hasattr(sys, "_is_gil_enabled")
    and not sys._is_gil_enabled()
):
    print("build nogil")
    define_macros.append(
        ("Py_GIL_DISABLED", "1"),
    )  # ("CYTHON_METH_FASTCALL", "1"), ("CYTHON_VECTORCALL",  1)]


extensions = [
    Extension(
        "qoi.qoi",
        sources=["src/qoi/qoi.pyx", "src/qoi/implementation.c"],
        define_macros=define_macros,
    )
]


if USE_CYTHON:
    compiler_directives = {
        "language_level": 3,
        "embedsignature": True,
        "boundscheck": False,
        "wraparound": False,
        "cdivision": True,
    }
    if Version(cython_version) >= Version("3.1.0a0"):
        compiler_directives["freethreading_compatible"] = True
    extensions = cythonize(extensions, compiler_directives=compiler_directives)
else:
    extensions = no_cythonize(extensions)

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

with open("requirements-dev.txt") as f:
    dev_requires = f.read().strip().split("\n")

setup(
    ext_modules=extensions,
    install_requires=install_requires,
    extras_require={
        "dev": dev_requires,
    },
    include_dirs=[np.get_include()],
)
