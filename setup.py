from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import sys
import setuptools
import subprocess
import os
import pybind11

class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=''):
        # Assuming the setup.py is located at the project root which also contains the CMakeLists.txt
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)

class CMakeBuild(build_ext):
    def run(self):
        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        cfg = 'Debug' if self.debug else 'Release'
        build_args = ['--config', cfg]

        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
        cmake_args = ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
                      '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_' + f'{cfg.upper()}={extdir}',
                      '-Dpybind11_DIR=' + pybind11.get_cmake_dir(),
                      '-DPYTHON_EXECUTABLE=' + sys.executable]

        if "CMAKE_ARGS" in os.environ:
            cmake_args += os.environ["CMAKE_ARGS"].split()

        # Determine the number of cores to use
        num_cores = os.cpu_count()  # Get the number of cores available on your system
        if "CMAKE_BUILD_PARALLEL_LEVEL" not in os.environ:
            os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = str(num_cores)

        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)

        subprocess.check_call(['cmake', ext.sourcedir] + cmake_args, cwd=self.build_temp)
        subprocess.check_call(['cmake', '--build', '.', '--config', cfg], cwd=self.build_temp)  # Adjusted line

setup(
    name='pysuperansac',
    version='1.0',
    author='Daniel Barath',
    author_email="majti89@gmail.com",
    description='A RANSAC implementation for robust estimation.',
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    ext_modules=[CMakeExtension('pysuperansac', sourcedir='.')],
    cmdclass=dict(build_ext=CMakeBuild),
    url="https://github.com/you/superansac",
    zip_safe=False,
    license='MIT',
)
