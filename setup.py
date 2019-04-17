#!/usr/bin/env python
# -*- coding: utf-8 -*

from setuptools import setup, find_packages
from pili.version import get_version

setup(
    name='pili-cms',
    description='Blogging platform with social network features',
    author='Vitaly R. Samigullin',
    author_email='vrs@pilosus.org',
    url='https://github.com/pilosus/pili/',
    version=get_version(),
    python_requires='>=3.6',
    zip_safe=True,
    include_package_data=True,
    packages=find_packages(exclude=['tests']),
    namespace_packages=['pili'],
)
