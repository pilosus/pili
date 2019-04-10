#!/usr/bin/env python
# -*- coding: utf-8 -*

from setuptools import setup, find_packages
from subprocess import check_output

COMMIT_FILE = '.commit'
GIT_COMMAND = 'git describe --tags --long --dirty'
VERSION_FORMAT = '{tag}.dev{commit_count}+{commit_hash}'


def get_version() -> str:
    """ Return package version from git, write commit to file
    """

    output = check_output(GIT_COMMAND.split()).decode('utf-8').strip().split('-')
    tag, count, commit = output[:3]
    dirty = len(output) == 4

    if count == '0' and not dirty:
        return tag
    return VERSION_FORMAT.format(tag=tag, commit_count=count, commit_hash=commit)


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
