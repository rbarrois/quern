#!/usr/bin/env python3
# This software is distributed under the two-clause BSD license.

import os
import re
import sys

from setuptools import find_packages, setup

root_dir = os.path.abspath(os.path.dirname(__file__))


def get_version(package_name):
    version_re = re.compile(r"^VERSION = [\"']([\w_.-]+)[\"']$")
    package_components = package_name.split('.')
    init_path = os.path.join(root_dir, *(package_components + ['version.py']))
    with open(init_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = version_re.match(line[:-1])
            if match:
                return match.groups()[0]
    return '0.1.0'


PACKAGE = 'quern'


setup(
    name=PACKAGE,
    version=get_version(PACKAGE),
    description="quern, a portage-based image builder",
    long_description=''.join(open('README.rst', 'r', encoding='utf-8').readlines()),
    author="Raphaël Barrois",
    author_email="raphael.barrois+%s@polytechnique.org" % PACKAGE,
    license="GPLv2",
    keywords=['portage', 'image', 'package', 'docker', 'embedded'],
    url="https://github.com/rbarrois/%s/" % PACKAGE,
    download_url="https://pypi.python.org/pypi/%s/" % PACKAGE,
    packages=find_packages(exclude=['tests*']),
    platforms=["OS Independent"],
    entry_points={
        'console_scripts': [
            'quern-builder=quern.builder_cli:main',
        ],
    },
    install_requires=[
        'getconf',
    ],
    setup_requires=[
        'setuptools>=0.8',
    ],
    extras_requires={
        'docker': [
            'docker-py>=1.6,<2',
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python",
        "Topic :: Software Development",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Systems Administration",
    ],
)
