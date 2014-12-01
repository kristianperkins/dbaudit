#!/usr/bin/env python
from setuptools import setup

requires = ['SQLAlchemy', 'ipydb']
description = 'quickly add auditing to your database'

setup (
    name='dbaudit',
    version='0.0.1',
    description=description,
    long_description=open('README.md').read(),
    author='Kristian Perkins',
    author_email='krockode@gmail.com',
    url='http://github.com/krockode/dbaudit',
    packages=['dbaudit'],
    zip_safe=False,
    install_requires=requires,
    entry_points={
        'console_scripts': [
            'dbaudit = dbaudit.dbaudit:main',
        ],
    }
)
