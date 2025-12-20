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

.. image:: https://img.shields.io/pypi/dd/py7zr
  :target: https://pypi.org/project/py7zr

.. image:: https://img.shields.io/conda/vn/conda-forge/py7zr
  :target: https://anaconda.org/conda-forge/py7zr

.. image:: https://github.com/miurahr/py7zr/workflows/Run%20Tox%20tests/badge.svg
  :target: https://github.com/miurahr/py7zr/actions

.. image:: https://dev.azure.com/miurahr/github/_apis/build/status/miurahr.py7zr?branchName=master
  :target: https://dev.azure.com/miurahr/github/_build/latest?definitionId=14&branchName=master

.. image:: https://coveralls.io/repos/github/miurahr/py7zr/badge.svg?branch=master
  :target: https://coveralls.io/github/miurahr/py7zr?branch=master

.. image:: https://img.shields.io/pypi/l/py7zr
  :target: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
  
.. image:: https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraine.svg
  :target: https://github.com/vshymanskyy/StandWithUkraine/blob/main/docs/README.md
  
.. image:: https://snyk.io/advisor/python/py7zr/badge.svg
  :target: https://snyk.io/advisor/python/py7zr
  :alt: py7zr
  
.. image:: https://app.codacy.com/project/badge/Grade/d9d82e1c1708470a921a3a974ea0eedd
  :target: https://app.codacy.com/gh/miurahr/py7zr/dashboard
  :alt: Codacy


py7zr is a library and utility to support 7zip archive compression, decompression,
encryption and decryption written by Python programming language.

Incompatible change
===================

There is incompatible change between v1.0.0-rc1 to v1.0.0-rc2.
I abandon methods ``read`` and ``readall``.
When you want to extract the archive to memory, you need to use
``extract`` method with ``factory`` argument. The ``factory`` takes a factory class, as of the GoF design pattern,
that provides object implements ``Py7zIO`` interface as a call back instance.
``SevenZipFile`` extract and write uncompressed data into your ``Py7zIO`` object.

Discussion Forum
================

You are welcome to join discussions on project forum/builtin-board at
https://github.com/miurahr/py7zr/discussions

You can see announcements of new releases, questions and answers, and
new feature ideas. When you doubt for usage of py7zr library with unclear
manuals, please feel easy to raise question on forum.

Compression algorithms
======================

``py7zr`` supports algorithms and filters which `lzma module`_ and `liblzma`_ support,
and supports BZip2 and Deflate that are implemented in python core libraries,
It also supports ZStandard, Brotli and PPMd with third party libraries.

``py7zr`` is also able to encrypt and decrypt data using 3rd party encryption library.


Supported algorithms
--------------------

* compress
    * LZMA2
    * LZMA
    * Bzip2
    * Deflate
    * Copy
    * ZStandard
    * Brotli
    * PPMd
    * Enhanced Deflate (Experimental)

* crypt
    * 7zAES

* Filters
    * Delta
    * BCJ(X86,ARMT,ARM,PPC,SPARC,IA64)

.. note::
  * A feature handling symbolic link is basically compatible with ``p7zip`` implementation,
    but not work with original 7-zip because the original does not implement the feature.
  * ``py7zr`` try checking symbolic links strictly and raise ValueError when bad link is requested,
    but it does **not** guarantee to block all the bad cases.
  * ZStandard and Brotli is not default methods of 7-zip, so these archives are considered
    not to be compatible with original 7-zip on windows/p7zip on linux/mac.
  * Enhanced Deflate is also known as ``DEFLATE64`` :sup:`TM` that is a registered trademark of ``PKWARE, Inc.``
  * Enhanced Deflate is tested only on CPython. It is disabled on PyPy.

Not supported algorithms
------------------------

* BCJ2 (Standard `lzma module`_ does not provide).


Install
=======

You can install py7zr as usual other libraries using pip.

.. code-block:: shell

    $ pip install py7zr

OR, alternatively using conda:

.. code-block:: shell

    $ conda install -c conda-forge py7zr

Documents
=========

User manuals
------------

* `User Guide`_ for latest version.

* `API Guide`_ for latest version.

* `Manual`_ for stable version.

Developer guide
---------------

* `Contribution guidelines`_ for this project.

* `Contribution guidelines(html)`_  for this project.

* `Code of conduct`_ for this project.

* `Code of conduct(html)`_ for this project.

* `7z file specification`_ that py7zr stand on.


.. _`User Guide`: https://py7zr.readthedocs.io/en/latest/user_guide.html

.. _`API Guide` : https://py7zr.readthedocs.io/en/latest/api.html

.. _`Manual` : https://py7zr.readthedocs.io/en/stable/

.. _`Contribution guidelines(html)` : https://py7zr.readthedocs.io/en/latest/contribution.html

.. _`Contribution guidelines` : docs/contribution.rst

.. _`Code  of conduct` : docs/CODE_OF_CONDUCT.rst

.. _`Code  of conduct(html)` : https://py7zr.readthedocs.io/en/latest/CODE_OF_CONDUCT.html

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


``py7zr`` also supports extraction of single or selected files by 'extract(targets=['file path'])'.
Note: if you specify only a file but not a parent directory, it will fail.

.. code-block:: python

    import py7zr
    import re

    filter_pattern = re.compile(r'<your/target/file_and_directories/regex/expression>')
    with py7zr.SevenZipFile('archive.7z', 'r') as archive:
        allfiles = archive.getnames()
        selective_files = [f for f in allfiles if filter_pattern.match(f)]
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
    with py7zr.SevenZipFile('target.7z', 'w', filters=my_filters) as archive:
        archive.writeall('/path/to/base_dir', 'base')


shutil helper
=============

py7zr also support `shutil`  interface.

.. code-block:: python

    from py7zr import pack_7zarchive, unpack_7zarchive
    import shutil

    # register file format at first.
    shutil.register_archive_format('7zip', pack_7zarchive, description='7zip archive')
    shutil.register_unpack_format('7zip', ['.7z'], unpack_7zarchive)

    # extraction
    shutil.unpack_archive('test.7z', '/tmp')

    # compression
    shutil.make_archive('target', '7zip', 'src')


Requirements
============

`py7zr` uses a python3 standard `lzma module`_ for extraction and compression.
The standard lzma module uses `liblzma`_ that support core compression algorithm of 7zip.

Minimum required version is Python 3.10.

``py7zr`` tested on Linux, macOS, Windows and Ubuntu aarch64.

It hopefully works on M1 Mac too.

Recommended versions are:

- CPython 3.10.0 and later.
- PyPy3.10-7.3.17 and later.

Following fixes are included in these versions, and it is not fixed on python3.6.

- `BPO-21872`_: LZMA library sometimes fails to decompress a file
- `PyPy3-3090`_: lzma.LZMADecomporessor.decompress does not respect max_length
- `PyPy3-3242`_: '_lzma_cffi' has no function named 'lzma_stream_encoder'

Following improvements are included in CPython 3.10

- `BPO-41486`_: Faster bz2/lzma/zlib via new output buffering

.. _`lzma module`: https://docs.python.org/3/library/lzma.html
.. _`liblzma`: https://tukaani.org/xz/
.. _`BPO-21872`: https://bugs.python.org/issue21872
.. _`BPO-41486`: https://bugs.python.org/issue41486
.. _`PyPy3-3090`: https://foss.heptapod.net/pypy/pypy/-/issues/3090
.. _`PyPy3-3242`: https://foss.heptapod.net/pypy/pypy/-/issues/3242



Dependencies
============

There are several dependencies to support algorithms and CLI expressions.

===================== ===============================
Package               Purpose
===================== ===============================
`PyCryptodomex`_      7zAES encryption
`backports.zstd`      ZStandard compression for Python before 3.14
`PyPPMd`_             PPMd compression
`Brotli`_             Brotli compression (CPython)
`BrotliCFFI`_         Brotli compression (PyPy)
`inflate64`_          Enhanced deflate compression
`pybcj`_              BCJ filters
`multivolumefile`_    Multi-volume archive read/write
`texttable`_          CLI formatter
===================== ===============================


.. _`Pycryptodomex` : https://www.pycryptodome.org/en/latest/index.html
.. _`backports.zstd` : https://pypi.org/project/backports.zstd
.. _`PyPPMd` : https://pypi.org/project/pyppmd
.. _`Brotli` : https://pypi.org/project/brotli
.. _`BrotliCFFI` : https://pypi.org/project/brotlicffi
.. _`inflate64` : https://pypi.org/project/inflate64
.. _`pybcj` : https://pypi.org/project/pybcj
.. _`multivolumefile` : https://pypi.org/project/multivolumefile
.. _`texttable` : https://pypi.org/project/texttable


Performance
===========

You can find a compression and decompression benchmark results at
[Github issue](https://github.com/miurahr/py7zr/issues/297) and [wiki page](https://github.com/miurahr/py7zr/wiki/Benchmarks)

py7zr works well, but slower than ``7-zip`` and ``p7zip`` C/C++ implementation by several reasons.
When compression/decompression **speed** is important, it is recommended to use these
alternatives through ``subprocess.run`` python interface.

py7zr consumes some memory to decompress and compress data. It requires about 300MiB - 700MiB free memory to work well at least.


Use Cases
=========

- `PyTorch`_  Open-source deep learning framework.
- `aqtinstall`_ Another (unofficial) Qt (aqt) CLI Installer on multi-platforms.
- PreNLP_ Preprocessing Library for Natural Language Processing
- mlox_  a tool for sorting and analyzing Morrowind plugin load order

.. _`PyTorch`: https://pytorch.org/
.. _aqtinstall: https://github.com/miurahr/aqtinstall
.. _PreNLP: https://github.com/lyeoni/prenlp
.. _mlox: https://github.com/mlox/mlox

Security
========

Please find a `Security Policy`_ of this project.

Version 0.20.0, 0.19.0, 0.18.10 or before has a `vulnerability for path traversal`_  attack.
Details are on "CVE-2022-44900: path traversal vulnerability in py7zr" `disclose article`_ .

Affected versions  are vulnerable to Directory Traversal due to insufficient checks in the 'py7zr.py' and 'helpers.py' files

You are recommend to update immediately to version 0.20.2 or later

.. _`vulnerability for path traversal`: https://security.snyk.io/vuln/SNYK-PYTHON-PY7ZR-3092461

I really appreciate Mr. Matteo Cosentino for notification and corporation on security improvement.

.. _`disclose article`: https://lessonsec.com/cve/cve-2022-44900/

.. _`Security Policy` : https://py7zr.readthedocs.io/en/latest/SECURITY.html

License
=======

* Copyright (C) 2019-2024 Hiroshi Miura

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

