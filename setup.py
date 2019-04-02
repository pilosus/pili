#!/usr/bin/env python
# -*- coding: utf-8 -*

from setuptools import setup, find_packages
from subprocess import check_output

COMMIT_FILE = '.commit'


def get_version() -> str:
    """ Return package version from git, write commit to file
    """
    tag = check_output(['git', 'describe', '--tags']).decode().strip().split('-')
    commit = check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()

    # Write commit SHA to file
    with open(COMMIT_FILE, 'w') as f:
        f.write(commit)

    # Return package version
    if len(tag) > 1:
        return '{}.dev{}'.format(tag[0], commit)
    return tag[0]


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
