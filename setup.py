#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
"""

import os
from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='lifx_circ',
    version='0.0.1',
    author='Brandon Martin',
    author_email='brandon.d.martin@gmail.com',

    description=('A Python library to control and monitor LIFX bulbs'),
    license='BSD',
    keywords=['lifx', 'smart', 'light', 'bulb'],
    packages=['lifx_circ'],
    long_description=read('README.txt'),
    package_data={'': ['LICENSE.txt']},
    install_requires=[],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Utilities',
        'License :: OSI Approved :: BSD License',
    ],
)
