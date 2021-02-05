======================================
|logo| py7zr -- a 7z library on python
======================================

.. |logo| image:: logo.svg
    :width: 80pt
    :height: 80pt
    :target: https://pypi.org/project/py7zr

.. image:: https://readthedocs.org/projects/py7zr/badge/?version=latest
  :target: https://py7zr.readthedocs.io/en/latest/?badge=latest

.. image:: https://badge.fury.io/py/py7zr.svg
  :target: https://badge.fury.io/py/py7zr

.. image:: https://github.com/miurahr/py7zr/workflows/Run%20Tox%20tests/badge.svg
  :target: https://github.com/miurahr/py7zr/actions

.. image:: https://dev.azure.com/miurahr/github/_apis/build/status/miurahr.py7zr?branchName=master
  :target: https://dev.azure.com/miurahr/github/_build/latest?definitionId=14&branchName=master

.. image:: https://coveralls.io/repos/github/miurahr/py7zr/badge.svg?branch=master
  :target: https://coveralls.io/github/miurahr/py7zr?branch=master




py7zr is a library and utility to support 7zip archive compression, decompression,
encryption and decryption written by Python programming language.

=======
WARNING
=======

**Test archive data, which affected a malware,  have been existed from Aug, 2020 - 20, Jan, 2021!**

All the git history is re-writed, so please remove your local and fork copy of the git repository,
and clone again(if necessary)!

Problematic file is named `issue_218.7z` and `issue_218_2.7z`.

**There is NO affected in library itself.**  and the test execution also does not extract the malware file.
There is no problem when you install py7zr with `pip` command.

Release that has a clean source:

- v0.11.3 and later
- v0.10.2
- v0.9.10
- v0.9.4 and before

Install
=======

You can install py7zr as usual other libraries using pip.

.. code-block:: shell

    $ pip install py7zr


Documents
=========

User manuals
------------

* `User Guide`_ for latest version.

* `API Guide`_ for latest version.

* `Manual`_ for stable version.

Developer guide
---------------

* `Contributor guide`_ for one want to contribute the project.

* `7z file specification`_


.. _`User Guide`: https://py7zr.readthedocs.io/en/latest/user_guide.html

.. _`API Guide` : https://py7zr.readthedocs.io/en/latest/api.html

.. _`Manual` : https://py7zr.readthedocs.io/en/stable/

.. _`Contributor guide` : https://py7zr.readthedocs.io/en/latest/contribution.html

.. _`7z file specification` : https://py7zr.readthedocs.io/en/latest/archive_format.html


CLI Usage
=========

You can run command script py7zr like as follows;

* List archive contents

.. code-block:: shell

    $ py7zr l test.7z

* Extract archive

.. code-block:: shell

    $ py7zr x test.7z

* Extract archive with password

.. code-block:: shell

    $ py7zr x -P test.7z
      password?: ****

* Create and compress to archive

.. code-block:: shell

    $ py7zr c target.7z test_dir

* Create multi-volume archive

.. code-block:: shell

    $ py7zr c -v 500k target.7z test_dir

* Test archive

.. code-block:: shell

    $ py7zr t test.7z

* Append files to archive

.. code-block:: shell

    $ py7zr a test.7z test_dir

* Show information

.. code-block:: shell

    $ py7zr i

* Show version

.. code-block:: shell

    $ py7zr --version


SevenZipFile Class Usage
========================

py7zr is a library which can use in your python application.

Decompression/Decryption
------------------------

Here is a code snippet how to decompress some file in your application.

.. code-block:: python

    import py7zr

    archive = py7zr.SevenZipFile('sample.7z', mode='r')
    archive.extractall(path="/tmp")
    archive.close()



You can also use 'with' block because py7zr provide context manager(v0.6 and later).

.. code-block:: python

    import py7zr

    with py7zr.SevenZipFile('sample.7z', mode='r') as z:
        z.extractall()

    with py7zr.SevenZipFile('target.7z', 'w') as z:
        z.writeall('./base_dir')


py7zr also supports extraction of single or selected files by 'extract(targets=['file path'])'.
Note: if you specify only a file but not a parent directory, it will fail.

.. code-block:: python

    import py7zr
    import re

    filter_pattern = re.compile(r'<your/target/file_and_directories/regex/expression>')
    with SevenZipFile('archive.7z', 'r') as archive:
        allfiles = archive.getnames()
        selective_files = [f if filter_pattern.match(f) for f in allfiles]
        archive.extract(targets=selective_files)


py7zr support an extraction of password protected archive.(v0.6 and later)

.. code-block:: python

    import py7zr

    with py7zr.SevenZipFile('encrypted.7z', mode='r', password='secret') as z:
        z.extractall()

Compression/Encryption
----------------------

Here is a code snippet how to produce archive.

.. code-block:: python

    import py7zr

    with py7zr.SevenZipFile('target.7z', 'w') as archive:
        archive.writeall('/path/to/base_dir', 'base')


To create encrypted archive, please pass a password.

.. code-block:: python

    import py7zr

    with py7zr.SevenZipFile('target.7z', 'w', password='secret') as archive:
        archive.writeall('/path/to/base_dir', 'base')


To create archive with algorithms such as zstandard, you can call with custom filter.

.. code-block:: python

    import py7zr

    my_filters = [{"id": py7zr.FILTER_ZSTD}]
    another_filters = [{"id": py7zr.FILTER_ARM}, {"id": py7zr.FILTER_LZMA2, "preset": 7}]
    with py7zr.SevenZipFile('target.7z', 'w', filters=my_filter) as archive:
        archive.writeall('/path/to/base_dir', 'base')


shutil helper
=============

py7zr also support `shutil`  interface.

.. code-block:: python

    from py7zr import pack_7zarchvie, unpack_7zarchive
    import shutil

    # register file format at first.
    shutil.register_archive_format('7zip', pack_7zarchive, description='7zip archive')
    shutil.register_unpack_format('7zip', ['.7z'], unpack_7zarchive)

    # extraction
    shutil.unpack_archive('test.7z', '/tmp')

    # compression
    shutil.make_archive('target', '7zip', 'src')


Required Python versions
========================

`py7zr` uses a python3 standard `lzma module`_ for extraction and compression.
The standard lzma module uses `liblzma`_ that support core compression algorithm of 7zip.

Minimum required version is Python 3.5.
Two additional library is required only on Python3.5; contextlib2 and pathlib2.

Compression is supported on Python 3.6 and later.
Multi-volume archive creation issupported on Python 3.7 and later.

There are other runtime requrements; texttable, pycryptodome

Version recommendations are:

- CPython 3.7.5, CPython 3.8.0 and later.
- PyPy3.6-7.2.0 and later.

Following fixes are included in these versions, and it is not fixed on python3.6.

- `BPO-21872`_: LZMA library sometimes fails to decompress a file
- `PyPy3-3090`_: lzma.LZMADecomporessor.decompress does not respect max_length


.. _`lzma module`: https://docs.python.org/3/library/lzma.html
.. _`liblzma`: https://tukaani.org/xz/
.. _`BPO-21872`: https://bugs.python.org/issue21872
.. _`PyPy3-3090`: https://foss.heptapod.net/pypy/pypy/-/issues/3090


Compression Methods supported
=============================

'py7zr' supports algorithms and filters which `lzma module`_ and `liblzma`_ support.
It also support BZip2 and Deflate that are implemented in python core libraries,
and ZStandard with third party libraries.

Supported algorithms are:

* compress
    * LZMA2
    * LZMA
    * Bzip2
    * Deflate
    * Copy
    * PPMd
    * Zstandard

* crypt
    * 7zAES

* Filters
    * Delta
    * BCJ(X86,ARMT,ARM,PPC,SPARC,IA64)

* No supported
    * BCJ2
    * Deflate64

- A feature handling symbolic link is basically compatible with 'p7zip' implementation,
  but not work with original 7-zip because the original does not implement the feature.

Dependencies
============

There are several dependencies to support algorithms and CLI expressions.

================  ================================
Package           Purpose
================  ================================
`Pycryptodome`_   7zAES encryption
`ppmd-cffi`_      PPMd compression
`zstandard`_      ZStandard compression
`texttable`_      CLI
================  ================================

.. _`Pycryptodome` : https://pypi.org/project/pycryptodome/
.. _`ppmd-cffi` : https://pypi.org/project/ppmd-cffi/
.. _`zstandard` : https://pypi.org/project/zstandard
.. _`texttable` : https://pypi.org/project/texttable


Use Cases
=========

- `aqtinstall`_ Another (unofficial) Qt (aqt) CLI Installer on multi-platforms.
- PreNLP_ Preprocessing Library for Natural Language Processing
- mlox_  a tool for sorting and analyzing Morrowind plugin load order

.. _aqtinstall: https://github.com/miurahr/aqtinstall
.. _PreNLP: https://github.com/lyeoni/prenlp
.. _mlox: https://github.com/mlox/mlox

License
=======

* Copyright (C) 2019-2021 Hiroshi Miura

* pylzma Copyright (c) 2004-2015 by Joachim Bauch
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
