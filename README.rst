=====
py7zr
=====

.. image:: https://readthedocs.org/projects/py7zr/badge/?version=latest
  :target: https://py7zr.readthedocs.io/en/latest/?badge=latest

.. image:: https://badge.fury.io/py/py7zr.svg
  :target: https://badge.fury.io/py/py7zr

.. image:: https://travis-ci.org/miurahr/py7zr.svg?branch=master
  :target: https://travis-ci.org/miurahr/py7zr

.. image:: https://ci.appveyor.com/api/projects/status/966k084122lhs3i6?svg=true
  :target: https://ci.appveyor.com/project/miurahr/py7zr/

.. image:: https://dev.azure.com/miurahr/github/_apis/build/status/miurahr.py7zr?branchName=master
  :target: https://dev.azure.com/miurahr/github/_build/latest?definitionId=14&branchName=master

.. image:: https://coveralls.io/repos/github/miurahr/py7zr/badge.svg?branch=master
  :target: https://coveralls.io/github/miurahr/py7zr?branch=master

.. image:: https://codecov.io/gh/miurahr/py7zr/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/miurahr/py7zr

Pure python 7-zip implementation


Dependency
==========

It uses a standard lzma module and its API supported.
It also uses type definitions introduced in Python3.6.

Minimum required version is Python 3.5.

Version recommendations are:

- CPython 3.7.5, CPython 3.8.0 and later.
- PyPy3.6-7.2.0 and later.

Following fixes are included in above versions and python3.6 series is not fixed it.

- `BPO-21872`_: LZMA library sometimes fails to decompress a file
- `PyPy3-3088`_: lzma.LZMADecomporessor.decompress does not respect max_length

.. _`BPO-21872`: https://bugs.python.org/issue21872
.. _`PyPy3-3088`: https://bitbucket.org/pypy/pypy/issues/3088/lzmalzmadecompressordecompress-data


Document
========

Here is a readthedocs `manual`_ document.

.. _`manual`: https://py7zr.readthedocs.io/en/latest/


Usage
=====

You can run command script py7zr like as follows;

.. code-block::

    $ py7zr l test.7z
    $ py7zr x test.7z
    $ py7zr w target.7z test_dir


py7zr is a library which can use in your pyhton application.
Here is a code snippet how to decompress some file in your applicaiton.

.. code-block::

    import py7zr

    archive = py7zr.SevenZipFile('sample.7z', mode='x')
    archive.extractall(path="/tmp")
    archive.close()


Here is a code snippet how to produce archive.

.. code-block::

    import py7zr

    archvie = py7zr.SevenZipFile('target.7z', 'w')
    archive.writeall('./base_dir')
    archive.close()


py7zr also support `shutil`  interface.

.. code-block::

    from py7zr import pack_7zarchvie, unpack_7zarchive
    import shutil

    # register file format at first.
    shutil.register_archive_format('7zip', pack_7zarchive, description='7zip archive')
    shutil.register_unpack_format('7zip', ['.7z'], unpack_7zarchive)

    # extraction
    shutil.unpack_archive('test.7z', '/tmp')

    # compression
    shutil.make_archive('target', '7zip', 'src')


License
=======

* Copyright (C) 2019 Hiroshi Miura
* Copyright (c) 2004-2015 by Joachim Bauch
* 7-Zip Copyright (C) 1999-2010 Igor Pavlov
* LZMA SDK Copyright (C) 1999-2010 Igor Pavlov

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
