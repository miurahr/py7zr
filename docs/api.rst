.. _api_documentation:

*****************
API Documentation
*****************

:mod:`py7zr` --- 7-Zip archive library
======================================

.. module:: py7zr
   :synopsis: Read and write 7Z-format archive files.

.. moduleauthor:: Hiroshi Miura

The module is built upon awesome development effort and knowledge of `pylzma` module
and its `py7zlib.py` program by Joachim Bauch. Great appreciation for Joachim!

This page is generated from the docstrings of the public API exported by the
:mod:`py7zr` package. For tutorials see the :ref:`user_guide` and
:ref:`advanced_usage`; supported algorithms and filter chains are listed in
:ref:`compression_methods`.


.. _sevenzipfile-object:

SevenZipFile Object
===================

.. autoclass:: py7zr.SevenZipFile
   :members:
   :member-order: bysource
   :exclude-members: reporter

.. seealso::

   :ref:`advanced_usage` for extracting selected members and for writing
   member data to custom objects with a :class:`WriterFactory`.


.. _archiveinfo-object:

Information Objects
===================

.. autoclass:: py7zr.ArchiveInfo

.. autoclass:: py7zr.FileInfo


Functions
=========

.. autofunction:: py7zr.is_7zfile

.. autofunction:: py7zr.unpack_7zarchive

.. autofunction:: py7zr.pack_7zarchive

.. seealso::

   The :mod:`shutil` module offers a number of high-level operations on files
   and collections of files.


.. _io-interfaces:

I/O Interfaces
==============

.. autoclass:: py7zr.Py7zIO
   :members:
   :member-order: bysource

.. autoclass:: py7zr.WriterFactory
   :members:


Exceptions
==========

.. autoexception:: py7zr.Bad7zFile

.. autoexception:: py7zr.PasswordRequired

.. autoexception:: py7zr.UnsupportedCompressionMethodError

.. autoexception:: py7zr.DecompressionError

.. autoexception:: py7zr.DecompressionBombError


.. _api-constants:

Constants
=========

Filter IDs are used in the ``filters`` argument of :class:`SevenZipFile`.
See :ref:`compression_methods` for supported combinations.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Name
     - Meaning
   * - ``FILTER_LZMA``
     - LZMA compression
   * - ``FILTER_LZMA2``
     - LZMA2 compression
   * - ``FILTER_BZIP2``
     - BZip2 compression
   * - ``FILTER_DEFLATE``
     - Deflate compression
   * - ``FILTER_ZSTD``
     - ZStandard compression
   * - ``FILTER_PPMD``
     - PPMd compression
   * - ``FILTER_BROTLI``
     - Brotli compression
   * - ``FILTER_COPY``
     - No compression (store)
   * - ``FILTER_DELTA``
     - Delta filter
   * - ``FILTER_X86``, ``FILTER_ARM``, ``FILTER_ARMTHUMB``,
       ``FILTER_POWERPC``, ``FILTER_SPARC``, ``FILTER_IA64``
     - BCJ branch converters for executable code
   * - ``FILTER_CRYPTO_AES256_SHA256``
     - 7zAES encryption
   * - ``PRESET_DEFAULT``, ``PRESET_EXTREME``
     - LZMA/LZMA2 ``preset`` values, from :mod:`lzma`
   * - ``CHECK_NONE``, ``CHECK_CRC32``, ``CHECK_CRC64``, ``CHECK_SHA256``
     - Integrity check IDs, from :mod:`lzma`
