# -*- coding: utf-8 -*-
# Copyright 2007-2011 The HyperSpy developers
#
# This file is part of  HyperSpy.
#
#  HyperSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#  HyperSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with  HyperSpy.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import sys

v = sys.version_info
if v[0] != 3:
    error = "ERROR: From version 0.8.4 HyperSpy requires Python 3. " \
            "For Python 2.7 install Hyperspy 0.8.3 e.g. " \
            "$ pip install --upgrade hyperspy==0.8.3"
    print(error, file=sys.stderr)
    sys.exit(1)

from setuptools import setup, Extension, Command
import distutils.dir_util

import warnings

import os
import subprocess
import fileinput

setup_path = os.path.dirname(__file__)

import hyperspy.Release as Release
# clean the build directory so we aren't mixing Windows and Linux
# installations carelessly.
if os.path.exists('build'):
    distutils.dir_util.remove_tree('build')

install_req = ['scipy',
               'ipython>=2.0',
               'matplotlib>=1.2',
               'numpy',
               'traits>=4.5.0',
               'traitsui>=5.0',
               'natsort',
               'requests',
               'setuptools',
               'sympy']


# Extensions:
raw_extensions = [Extension("hyperspy.tests.misc.cython.test_cython_integration",
                        ['hyperspy/tests/misc/cython/test_cython_integration.pyx']),
                 ]

cleanup_list = []
for leftover in raw_extensions:
    path, ext = os.path.splitext(leftover.sources[0])
    if ext in ('.pyx', '.py'):
        cleanup_list.append(os.path.join(setup_path, path + '.c*'))
        cleanup_list.append(os.path.join(setup_path, path + '.cpython-*.so'))
        cleanup_list.append(os.path.join(setup_path, path + '.cpython-*.pyd'))


def count_c_extensions(extensions):
    c_num = 0
    for extension in extensions:
        # if first source file with extension *.c or *.cpp exists
        # it is cythonised or pure c/c++ extension:
        sfile = extension.sources[0]
        path, ext = os.path.splitext(sfile)
        if os.path.exists(path + '.c') or os.path.exists(path + '.cpp'):
            c_num += 1
    return c_num


def cythonize_extensions(extensions):
    try:
        from Cython.Build import cythonize
        return cythonize(extensions)
    except ImportError:
        warnings.warn("""WARNING: cython required to generate fast c code is not found on this system.
Only slow pure python alternative functions will be available.
To use fast implementation of some functions writen in cython either:
a) install cython and re-run the installation,
b) try alternative source distribution containing cythonized C versions of fast code,
c) use binary distribution (i.e. wheels, egg).""")
        return []


def no_cythonize(extensions):
    for extension in extensions:
        sources = []
        for sfile in extension.sources:
            path, ext = os.path.splitext(sfile)
            if ext in ('.pyx', '.py'):
                if extension.language == 'c++':
                    ext = '.cpp'
                else:
                    ext = '.c'
                sfile = path + ext
            sources.append(sfile)
        extension.sources[:] = sources
    return extensions


# to cythonize, or not to cythonize... :
if len(raw_extensions) > count_c_extensions(raw_extensions):
    extensions = cythonize_extensions(raw_extensions)
else:
    extensions = no_cythonize(raw_extensions)


# generate some git hook to clean up and re-build_ext --inplace
# after changing branches:
if os.path.exists('.git'):
    with open('.git/hooks/post-checkout', 'w') as pchook:
        pchook.write('#!/bin/sh\n')
        pchook.write('rm ' + ' '.join([i for i in cleanup_list]) + '\n')
        pchook.write(' '.join([sys.executable,
                               os.path.join(setup_path, 'setup.py'),
                               'build_ext --inplace']))
    hook_mode = 0o777  # make it executable
    os.chmod('.git/hooks/post-checkout', hook_mode)


class Recythonize(Command):
    """cythonize all extensions"""
    description = "(re-)cythonize all cython extensions"

    user_options = []

    def initialize_options(self):
        """init options"""
        pass

    def finalize_options(self):
        """finalize options"""
        pass

    def run(self):
        # if there is no cython it is supposed to fail:
        from Cython.Build import cythonize
        global raw_extensions
        global extensions
        cythonize(extensions)


class update_version_when_dev:

    def __enter__(self):
        self.release_version = Release.version

        # Get the hash from the git repository if available
        self.restore_version = False
        git_master_path = ".git/refs/heads/master"
        if "+dev" in self.release_version and \
                os.path.isfile(git_master_path):
            try:
                p = subprocess.Popen(["git", "describe",
                                      "--tags", "--dirty", "--always"],
                                     stdout=subprocess.PIPE)
                stdout = p.communicate()[0]
                if p.returncode != 0:
                    raise EnvironmentError
                else:
                    version = stdout[1:].strip().decode()
                    if str(self.release_version[:-4] + '-') in version:
                        version = version.replace(
                            self.release_version[:-4] + '-',
                            self.release_version[:-4] + '+git')
                    self.version = version
            except EnvironmentError:
                # Git is not available, but the .git directory exists
                # Therefore we can get just the master hash
                with open(git_master_path) as f:
                    masterhash = f.readline()
                self.version = self.release_version.replace(
                    "+dev", "+git-%s" % masterhash[:7])
            for line in fileinput.FileInput("hyperspy/Release.py",
                                            inplace=1):
                if line.startswith('version = '):
                    print("version = \"%s\"" % self.version)
                else:
                    print(line, end=' ')
            self.restore_version = True
        else:
            self.version = self.release_version
        return self.version

    def __exit__(self, type, value, traceback):
        if self.restore_version is True:
            for line in fileinput.FileInput("hyperspy/Release.py",
                                            inplace=1):
                if line.startswith('version = '):
                    print("version = \"%s\"" % self.release_version)
                else:
                    print(line, end=' ')


with update_version_when_dev() as version:
    setup(
        name="hyperspy",
        package_dir={'hyperspy': 'hyperspy'},
        version=version,
        ext_modules=extensions,
        packages=['hyperspy',
                  'hyperspy.datasets',
                  'hyperspy._components',
                  'hyperspy.datasets',
                  'hyperspy.io_plugins',
                  'hyperspy.docstrings',
                  'hyperspy.drawing',
                  'hyperspy.drawing._markers',
                  'hyperspy.drawing._widgets',
                  'hyperspy.learn',
                  'hyperspy._signals',
                  'hyperspy.gui',
                  'hyperspy.utils',
                  'hyperspy.tests',
                  'hyperspy.tests.axes',
                  'hyperspy.tests.component',
                  'hyperspy.tests.datasets',
                  'hyperspy.tests.drawing',
                  'hyperspy.tests.io',
                  'hyperspy.tests.model',
                  'hyperspy.tests.mva',
                  'hyperspy.tests.signal',
                  'hyperspy.tests.utils',
                  'hyperspy.tests.misc',
                  'hyperspy.models',
                  'hyperspy.misc',
                  'hyperspy.misc.eels',
                  'hyperspy.misc.eds',
                  'hyperspy.misc.io',
                  'hyperspy.misc.machine_learning',
                  'hyperspy.external',
                  'hyperspy.external.mpfit',
                  'hyperspy.external.astroML',
                  ],
        install_requires=install_req,
        setup_requires=[
            'setuptools'
        ],
        package_data={
            'hyperspy':
            [
                'misc/eds/example_signals/*.hdf5',
                'tests/io/blockfile_data/*.blo',
                'tests/io/dens_data/*.dens',
                'tests/io/dm_stackbuilder_plugin/test_stackbuilder_imagestack.dm3',
                'tests/io/dm3_1D_data/*.dm3',
                'tests/io/dm3_2D_data/*.dm3',
                'tests/io/dm3_3D_data/*.dm3',
                'tests/io/dm4_1D_data/*.dm4',
                'tests/io/dm4_2D_data/*.dm4',
                'tests/io/dm4_3D_data/*.dm4',
                'tests/io/FEI_new/*.emi',
                'tests/io/FEI_new/*.ser',
                'tests/io/FEI_new/*.npy',
                'tests/io/FEI_old/*.emi',
                'tests/io/FEI_old/*.ser',
                'tests/io/FEI_old/*.npy',
                'tests/io/msa_files/*.msa',
                'tests/io/hdf5_files/*.hdf5',
                'tests/io/tiff_files/*.tif',
                'tests/io/npy_files/*.npy',
                'tests/io/unf_files/*.unf',
                'tests/drawing/*.ipynb',
                'tests/signal/test_find_peaks1D_ohaver/test_find_peaks1D_ohaver.hdf5',
            ],
        },
        author=Release.authors['all'][0],
        author_email=Release.authors['all'][1],
        maintainer='Francisco de la Peña',
        maintainer_email='fjd29@cam.ac.uk',
        description=Release.description,
        long_description=open('README.rst').read(),
        license=Release.license,
        platforms=Release.platforms,
        url=Release.url,
        keywords=Release.keywords,
        cmdclass={
        'recythonize': Recythonize,
        },
        classifiers=[
            "Programming Language :: Python :: 3",
            "Development Status :: 4 - Beta",
            "Environment :: Console",
            "Intended Audience :: Science/Research",
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
            "Natural Language :: English",
            "Operating System :: OS Independent",
            "Topic :: Scientific/Engineering",
            "Topic :: Scientific/Engineering :: Physics",
        ],
    )
