.. _api_documentation:

*****************
API Documentation
*****************

:mod:`py7zr` --- 7-Zip archive library
======================================

.. module:: py7zr
   :synopsis: Read and write 7Z-format archive files.

.. moduleauthor:: Hiroshi Miura <miurahr@linux.com>


The module is built upon awesome development effort and knowledge of `pylzma` module
and its `py7zlib.py` program by Joachim Bauch. Great appreciation for Joachim!

The module defines the following items:

.. exception:: Bad7zFile

   The error raised for bad 7z files.


.. class:: SevenZipFile
   :noindex:

   The class for reading 7z files.  See section sevenzipfile-object_


.. class:: FileInfo

   The class used to represent information about a member of an archive file. See section


.. function:: is_7zfile(filename)

   Returns ``True`` if *filename* is a valid 7z file based on its magic number,
   otherwise returns ``False``.  *filename* may be a file or file-like object too.


.. function:: unpack_7zarchive(archive, path, extra=None)

   Helper function to intend to use with :mod:`shutil` module which offers a number of high-level operations on files
   and collections of files. Since :mod:`shutil` has a function to register decompressor of archive, you can register
   an helper function and then you can extract archive by calling :meth:`shutil.unpack_archive`

.. code-block:: python

    shutil.register_unpack_format('7zip', ['.7z'], unpack_7zarchive)
    shutil.unpack_archive(filename, extract_dir)


.. function:: pack_7zarchive(archive, path, extra=None)

   Helper function to intend to use with :mod:`shutil` module which offers a number of high-level operations on files
   and collections of files. Since :mod:`shutil` has a function to register maker of archive, you can register
   an helper function and then you can produce archive by calling :meth:`shutil.make_archive`

.. code-block:: python

    shutil.register_archive_format('7zip', pack_7zarchive, description='7zip archive')
    shutil.make_archive(base_name, '7zip', base_dir)


.. seealso::

   (external link) `shutil`_  :mod:`shutil` module offers a number of high-level operations on files and collections of files.

.. _shutil: https://docs.python.org/3/library/shutil.html


Class description
=================

.. _archiveinfo-object:

ArchiveInfo Object
------------------

.. autoclass:: py7zr.ArchiveInfo
   :members:
   :member-order: bysource


.. _sevenzipfile-object:

SevenZipFile Object
-------------------

.. autoclass:: py7zr.SevenZipFile
   :members:
   :member-order: bysource
   :special-members: __init__, __enter__, __exit__

.. note::

   The following examples show how to use pattern matching for extraction
   and custom factory objects.

   Extract files matching a pattern:

   .. code-block:: python

      filter_pattern = re.compile(r'scripts.*')
      with SevenZipFile('archive.7z', 'r') as archive:
           allfiles = archive.getnames()
           targets = [f for f in allfiles if filter_pattern.match(f)]
      with SevenZipFile('archive.7z', 'r') as archive:
           archive.extract(targets=targets)
      with SevenZipFile('archive.7z', 'r') as archive:
           archive.extract(targets=targets, recursive=True)

   Extract to custom objects using a factory:

   .. code-block:: python

      from typing import override, Union, Optional
      from py7zr import Py7zIO, SevenZipFile, WriterFactory

      class MyIO(Py7zIO):
          def __init__(self, limit):
              self._limit = limit
              self._buffer = None
              self._empty = True

          @override
          def write(self, s: Union[bytes, bytearray]):
              """keep only bytes of limit"""
              if self._empty:
                  self._buffer = s[:self._limit]
                  self._empty = False

          @override
          def read(self, size: Optional[int] = None) -> bytes:
              size = 0 if size is None else size
              if self._empty:
                  return bytes()
              return self._buffer[:size]

          @override
          def seek(self, offset: int, whence: int = 0) -> int:
              return 0

          @override
          def flush(self) -> None:
              pass

          @override
          def size(self) -> int:
              return len(self._buffer)


      class MyFactory(WriterFactory):
          def __init__(self, size):
              self.size = size
              self.products = {}

          @override
          def create(self, filename: str) -> Py7zIO:
              product = MyIO(self.size)
              self.products[filename] = product
              return product


      size = 10
      factory = MyFactory(size)
      with SevenZipFile('archive.7z', 'r') as archive:
          archive.extractall(factory=factory)
      for filename, fileobj in factory.products.items():
          print(f'{filename}: {fileobj.read(size)}...')


Compression Methods
===================

'py7zr' supports algorithms and filters which `lzma module`_ and `liblzma`_ support.
It also support BZip2 and Deflate that are implemented in python core libraries,
and ZStandard with third party libraries.
`py7zr`, python3 core `lzma module`_ and `liblzma` do not support some algorithms
such as PPMd, BCJ2 and Deflate64.

.. _`lzma module`: https://docs.python.org/3/library/lzma.html
.. _`liblzma`: https://tukaani.org/xz/

Here is a table of algorithms.

+---+----------------------+------------+-----------------------------+
|  #|   Category           | Algorithm  | Note                        |
+===+======================+============+=============================+
|  1| - Compression        | LZMA2      |  default (LZMA2+BCJ)        |
+---+ - Decompression      +------------+-----------------------------+
|  2|                      | LZMA       |                             |
+---+                      +------------+-----------------------------+
|  3|                      | Bzip2      |                             |
+---+                      +------------+-----------------------------+
|  4|                      | Deflate    |                             |
+---+                      +------------+-----------------------------+
|  5|                      | COPY       |                             |
+---+                      +------------+-----------------------------+
|  6|                      | PPMd       | depend on pyppmd            |
+---+                      +------------+-----------------------------+
|  7|                      | ZStandard  | depend on backports.zstd    |
|   |                      |            | for Python before 3.14      |
+---+                      +------------+-----------------------------+
|  8|                      | Brotli     | depend on brotli,brotliCFFI |
+---+----------------------+------------+-----------------------------+
|  9| - Filter             | BCJ        |(X86, ARM, PPC, ARMT, SPARC, |
|   |                      |            | IA64)  depend on bcj-cffi   |
+---+                      +------------+-----------------------------+
| 10|                      | Delta      |                             |
+---+----------------------+------------+-----------------------------+
| 11| - Encryption         | 7zAES      | depend on pycryptodome      |
|   | - Decryption         |            |                             |
+---+----------------------+------------+-----------------------------+
| 12| - Unsupported        | BCJ2       |                             |
+---+                      +------------+-----------------------------+
| 13|                      | Deflate64  |                             |
+---+----------------------+------------+-----------------------------+

- A feature handling symbolic link is basically compatible with 'p7zip' implementation,
  but not work with original 7-zip because the original does not implement the feature.


Possible filters value
======================

Here is a list of examples for possible filters values.
You can use it when creating SevenZipFile object.

.. code-block:: python

    from py7zr import FILTER_LZMA, SevenZipFile

    filters = [{'id': FILTER_LZMA}]
    archive = SevenZipFile('target.7z', mode='w', filters=filters)


LZMA2 + Delta
    ``[{'id': FILTER_DELTA}, {'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}]``

LZMA2 + BCJ
    ``[{'id': FILTER_X86}, {'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}]``

LZMA2 + ARM
    ``[{'id': FILTER_ARM}, {'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}]``

LZMA + BCJ
    ``[{'id': FILTER_X86}, {'id': FILTER_LZMA}]``

LZMA2
    ``[{'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}]``

LZMA
    ``[{'id': FILTER_LZMA}]``

BZip2
    ``[{'id': FILTER_BZIP2}]``

Deflate
    ``[{'id': FILTER_DEFLATE}]``

ZStandard
    ``[{'id': FILTER_ZSTD, 'level': 3}]``

PPMd
    ``[{'id': FILTER_PPMD, 'order': 6, 'mem': 24}]``

    ``[{'id': FILTER_PPMD, 'order': 6, 'mem': "16m"}]``

Brolti
    ``[{'id': FILTER_BROTLI, 'level': 11}]``

7zAES + LZMA2 + Delta
    ``[{'id': FILTER_DELTA}, {'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

7zAES + LZMA2 + BCJ
    ``[{'id': FILTER_X86}, {'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

7zAES + LZMA
    ``[{'id': FILTER_LZMA}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

7zAES + Deflate
    ``[{'id': FILTER_DEFLATE}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

7zAES + BZip2
    ``[{'id': FILTER_BZIP2}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

7zAES + ZStandard
    ``[{'id': FILTER_ZSTD}, {'id': FILTER_CRYPTO_AES256_SHA256}]``


.. rubric:: Footnotes
