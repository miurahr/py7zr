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

.. image:: https://coveralls.io/repos/github/miurahr/py7zr/badge.svg?branch=master
  :target: https://coveralls.io/github/miurahr/py7zr?branch=master

Pure python 7zr implementation


Dependency
==========

It uses a standard lzma module that is supported in Python3.3 and later.


Document
========

Here is a readthedocs `manual`_ document.

.. _`manual`: https://py7zr.readthedocs.io/en/latest/


Usage
=====

You can run command script py7zr like as follows;

.. code-block::

    $ py7zr l test.7z


py7zr is a library which can use in your pyhton application.
Here is a code snippet how to decompress some file in your applicaiton.

.. code-block::

    import py7zr

    def decompress(file):
        archive = py7zr.Archive(file)
        archive.extractall(path="/tmp")


py7zr also support `shutil` unpack interface.

.. code-block::

    frpm py7zr import unpack_7zarchive
    import shutil

    shutil.register_unpack_format('7zip', ['.7z'], unpack_7zarchive)
    shutil.unpack_archive('test.7z', '/tmp')


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
