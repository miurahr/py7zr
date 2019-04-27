#!/usr/bin/env python

import io
import os
import re

from setuptools import setup

package_name = "py7zr"

root_dir = os.path.abspath(os.path.dirname(__file__))

def readme():
    with io.open(os.path.join(os.path.dirname(__file__), 'README.rst'), mode="r", encoding="UTF-8") as readmef:
        return readmef.read()

with open(os.path.join(root_dir, package_name, '__init__.py')) as f:
    init_text = f.read()
    version = re.search(r'__version__\s*=\s*[\'\"](.+?)[\'\"]', init_text).group(1)
    license = re.search(r'__license__\s*=\s*[\'\"](.+?)[\'\"]', init_text).group(1)
    author = re.search(r'__author__\s*=\s*[\'\"](.+?)[\'\"]', init_text).group(1)
    author_email = re.search(r'__author_email__\s*=\s*[\'\"](.+?)[\'\"]', init_text).group(1)
    url = re.search(r'__url__\s*=\s*[\'\"](.+?)[\'\"]', init_text).group(1)

assert version
assert license
assert author
assert author_email
assert url

setup(name=package_name,
      version=version,
      description='Pure python 7zr implementation',
      url='http://github.com/miurahr/py7zr',
      license=license,
      long_description=readme(),
      keywords='compression, 7zip, lzma',
      author=author,
      author_email=author_email,
      packages=[package_name],
      requires=['bringbuf'],
      extras_require={
        'dev': [
            'pytest'
        ]
      },
      scripts=["bin/py7zr"],
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: System :: Archiving :: Compression',
        'Topic :: Software Development :: Libraries :: Python Modules',
      ]
      )
