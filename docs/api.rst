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


.. class:: ArchiveInfo

   The class used to represent information about an information of an archive file. See section archiveinfo-object_


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
    shutil.unpack_archive(filename, [, extract_dir])


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

.. py:class:: ArchiveInfo(filename, stat, header_size, method_names, solid, blocks, uncompressed)

   Data only python object to hold information of archive.
   The object can be retrieved by `archiveinfo()` method of `SevenZipFile` object.

.. py:attribute:: filename
   :type: str

   filename of 7zip archive. If SevenZipFile object is created from BinaryIO object,
   it becomes None.

.. py:attribute:: stat
   :type: stat_result

   fstat object of 7zip archive. If SevenZipFile object is created from BinaryIO object,
   it becomes None.

.. py:attribute:: header_size
   :type: int

   header size of 7zip archive.

.. py:attribute:: method_names
   :type: List[str]

   list of method names used in 7zip archive. If method is not supported by py7zr,
   name has a postfix asterisk(`*`) mark.

.. py:attribute:: solid
   :type: bool

   Whether is 7zip archive a solid compression or not.

.. py:attribute:: blocks
   :type: int

   number of compression block(s)

.. py:attribute:: uncompressed
   :type: int

   total uncompressed size of files in 7zip archive


.. _sevenzipfile-object:

SevenZipFile Object
-------------------


.. py:class:: SevenZipFile(file, mode='r', filters=None, dereference=False, password=None)

   Open a 7z file, where *file* can be a path to a file (a string), a
   file-like object or a :term:`path-like object`.

   The *mode* parameter should be ``'r'`` to read an existing
   file, ``'w'`` to truncate and write a new file, ``'a'`` to append to an
   existing file, or ``'x'`` to exclusively create and write a new file.
   If *mode* is ``'x'`` and *file* refers to an existing file,
   a :exc:`FileExistsError` will be raised.
   If *mode* is ``'r'`` or ``'a'``, the file should be seekable.

   The *filters* parameter controls the compression algorithms to use when
   writing files to the archive.

   SevenZipFile class has a capability as context manager. It can handle
   'with' statement.

   If dereference is False, add symbolic and hard links to the archive.
   If it is True, add the content of the target files to the archive.
   This has no effect on systems that do not support symbolic links.

   When password given, py7zr handles an archive as an encrypted one.

.. py:method:: SevenZipFile.close()

   Close the archive file and release internal buffers.  You must
   call :meth:`close` before exiting your program or most records will
   not be written.


.. py:method:: SevenZipFile.getnames()

   Return a list of archive files by name.


.. py:method:: SevenZipFile.needs_password()

   Return `True` if the archive is encrypted, or is going to create
   encrypted archive. Otherwise return `False`


.. py:method:: SevenZipFile.extractall(path=None)

   Extract all members from the archive to current working directory.  *path*
   specifies a different directory to extract to.


.. py:method:: SevenZipFile.extract(path=None, targets=None)

   Extract specified pathspec archived files to current working directory.
   'path' specifies a differenct directory to extract to.

   'targets' is a list of archived files to be extracted. py7zr looks for files
   and directories as same as specified in 'targets'.

   Once extract() called, the SevenZipFIle object become exhausted and EOF state.
   If you want to call read(), readall(), extract(), extractall() again,
   you should call reset() before it.

   **CAUTION** when specifying files and not specifying parent directory,
   py7zr will fails with no such directory. When you want to extract file
   'somedir/somefile' then pass a list: ['somedirectory', 'somedir/somefile']
   as a target argument.

   Please see 'tests/test_basic.py: test_py7zr_extract_and_getnames()' for
   example code.

.. code-block:: python

   filter_pattern = re.compile(r'scripts.*')
   with SevenZipFile('archive.7z', 'r') as zip:
        allfiles = zip.getnames()
        targets = [f if filter_pattern.match(f) for f in allfiles]
   with SevenZipFile('archive.7z', 'r') as zip:
        zip.extract(targets=targets)


.. py:method:: SevenZipFile.readall()

   Extract all members from the archive to memory and returns dictionary object.
   Returned dictionary has a form of Dict[filename: str, BinaryIO: io.ByteIO object].
   Once readall() called, the SevenZipFIle object become exhausted and EOF state.
   If you want to call read(), readall(), extract(), extractall() again,
   you should call reset() before it.
   You can get extracted data from dictionary value as such

.. code-block:: python

   with SevenZipFile('archive.7z', 'r') as zip:
       for fname, bio in zip.readall().items():
           print('{:s}: {:X}...'.format(name, bio.read(10))


.. py:method:: SevenZipFile.read(targets=None)

   Extract specified list of target archived files to dictionary object.
   'targets' is a list of archived files to be extracted. py7zr looks for files
   and directories as same as specified in 'targets'.
   When targets is None, it behave as same as readall().
   Once read() called, the SevenZipFIle object become exhausted and EOF state.
   If you want to call read(), readall(), extract(), extractall() again,
   you should call reset() before it.

.. code-block:: python

   filter_pattern = re.compile(r'scripts.*')
   with SevenZipFile('archive.7z', 'r') as zip:
        allfiles = zip.getnames()
        targets = [f for f in allfiles if filter_pattern.match(f)]
   with SevenZipFile('archive.7z', 'r') as zip:
        for fname, bio in zip.read(targets).items():
            print('{:s}: {:X}...'.format(name, bio.read(10))


.. py:method:: SevenZipFile.list()

    Return a List[FileInfo].


.. py:method:: SevenZipFile.archiveinfo()

    Return a ArchiveInfo object.


.. py:method:: SevenZipFile.test()

   Read all the archive file and check a packed CRC.
   Return ``True`` if CRC check passed, and return ``False`` when detect defeat,
   or return ``None`` when the archive don't have a CRC record.


.. py:method:: SevenZipFile.testzip()

    Read all the files in the archive and check their CRCs.
    Return the name of the first bad file, or else return ``None``.
    When the archive don't have a CRC record, it return ``None``.


.. py:method:: SevenZipFile.write(filename, arcname=None)

   Write the file named *filename* to the archive, giving it the archive name
   *arcname* (by default, this will be the same as *filename*, but without a drive
   letter and with leading path separators removed).
   The archive must be open with mode ``'w'``


.. py:method:: SevenZipFile.writeall(filename, arcname=None)

   Write the directory and its sub items recursively into the archive, giving
   the archive name *arcname* (by default, this will be the same as *filename*,
   but without a drive letter and with leading path seaprator removed).

   If you want to store directories and files, putting *arcname* is good idea.
   When filename is 'C:/a/b/c' and arcname is 'c', with a file exist as 'C:/a/b/c/d.txt',
   then archive listed as ['c', 'c/d.txt'], the former as directory.


.. py:method:: SevenZipFile.set_encrypted_header(mode)

   Set header encryption mode. When encrypt header, set mode to `True`, otherwise `False`.
   Default is `False`.


.. py:method:: SevenZipFile.set_encoded_header_mode(mode)

   Set header encode mode. When encode header data, set mode to `True`, otherwise `False`.
   Default is `True`.


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
|  7|                      | ZStandard  | depend on pyzstd            |
+---+                      +------------+-----------------------------+
|  8|                      | Brotli     | depend on brotli,brotliCFFI |
+---+----------------------+------------+-----------------------------+
|  9| - Filter             | BCJ        |(X86, ARM, PPC, ARMT, SPARC, |
|   |                      |            | IA64)  depend on bcj-cffi   |
+---+                      +------------+-----------------------------+
| 10|                      | Delta      |                             |
+---+----------------------+------------+-----------------------------+
| 11| - Encryption         | 7zAES      | depend on pycryptodomex     |
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
