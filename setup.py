import numpy as np

# import setuptools_scm  # noqa: F401 - to avoid version = 0.0.0 errors if built without setuptools_scm installed
from Cython.Build import cythonize
from setuptools import Extension, setup

setup(
    ext_modules=cythonize(
        [Extension("qoi", sources=["qoi/*.pyx", "qoi/implementation.c"])],
        compiler_directives={"language_level": "3"},
    ),
    headers=["qoi/c/qoi.h"],
    include_dirs=["qoi/c", np.get_include()],
)
