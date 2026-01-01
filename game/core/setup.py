# setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize
import os

here = os.path.abspath(os.path.dirname(__file__))

extensions = [
    Extension(
        "stein_core", 
        ["stein_core.pyx"],
        include_dirs=[here],
        library_dirs=[here],
        libraries=["libpython3.12"], 
        extra_compile_args=["/O2", "/fp:fast"],
    )
]

setup(
    name='Sayoristein Core Engine',
    ext_modules=cythonize(extensions, compiler_directives={
        'language_level': "3",
        'boundscheck': False,
        'wraparound': False,
        'cdivision': True,
    }),
)