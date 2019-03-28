#!/usr/bin/env python

import io
import os

from setuptools import setup


def readme():
    with io.open(os.path.join(os.path.dirname(__file__), 'README.rst'), mode="r", encoding="UTF-8") as readmef:
        return readmef.read()


setup(name='py7zr',
      version='0.0.1',
      description='Pure python 7zr implementation',
      url='http://github.com/miurahr/py7zr',
      license='LGPL-2.1',
      long_description=readme(),
      author='Hioshi Miura',
      author_email='miurahr@linux.com',
      packages=["py7zr"],
      requires=['bringbuf'],
      extras_require={
        'dev': [
            'pytest'
        ]
      },
      scripts=["bin/py7zr"]
      )
