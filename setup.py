#!/usr/bin/env python

# ----------------------------------------------------------------------------
# Copyright (c) 2013--, IAB development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

from setuptools import find_packages, setup
from glob import glob

__version__ = "0.0.0-dev"

classes = """
    Development Status :: 1 - Planning
    License :: OSI Approved :: BSD License
    Topic :: Software Development :: Libraries
    Programming Language :: Python
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3.3
    Programming Language :: Python :: 3.4
    Operating System :: Unix
    Operating System :: POSIX
    Operating System :: MacOS :: MacOS X
"""
classifiers = [s.strip() for s in classes.split('\n') if s]

description = ('Build script for An Introduction to Applied Bioinformatics.')

with open('README.rst') as f:
    long_description = f.read()

setup(name='build-iab',
      version=__version__,
      license='BSD',
      description=description,
      long_description=long_description,
      author="IAB development team",
      author_email="gregcaporaso@gmail.com",
      maintainer="IAB development team",
      maintainer_email="gregcaporaso@gmail.com",
      url='http://readIAB.org',
      test_suite='nose.collector',
      packages=find_packages(),
      scripts=glob("scripts/*"),
      install_requires=['ipymd', 'PyYAML', 'CommonMark', 'click', 'jupyter',
                        'six', 'runipy', 'boto', 'markdown2'],
      extras_require={'test': ["nose >= 0.10.1", "pep8", "flake8"]},
      classifiers=classifiers,
      )
