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

   The class for reading 7z files.  See section


.. class:: ArchiveInfo

   The class used to represent information about an information of an archive file. See section


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


.. _sevenzipfile-object:

SevenZipFile Object
-------------------


.. class:: SevenZipFile(file, mode='r', filters=None, dereference=False, password=None)

   Open a 7z file, where *file* can be a path to a file (a string), a
   file-like object or a :term:`path-like object`.

   The *mode* parameter should be ``'r'`` to read an existing
   file, ``'w'`` to truncate and write a new file, ``'a'`` to append to an
   existing file, or ``'x'`` to exclusively create and write a new file.
   If *mode* is ``'x'`` and *file* refers to an existing file,
   a :exc:`FileExistsError` will be raised.
   If *mode* is ``'r'`` or ``'a'``, the file should be seekable. [#f1]_

   The *filters* parameter controls the compression algorithms to use when
   writing files to the archive. [#f2]_

   SevenZipFile class has a capability as context manager. It can handle
   'with' statement.

   If dereference is False, add symbolic and hard links to the archive.
   If it is True, add the content of the target files to the archive.
   This has no effect on systems that do not support symbolic links.

   When password given, py7zr handles an archive as an encrypted one.

.. method:: SevenZipFile.close()

   Close the archive file and release internal buffers.  You must
   call :meth:`close` before exiting your program or most records will
   not be written.


.. method:: SevenZipFile.getnames()

   Return a list of archive files by name.


.. method:: SevenZipFile.needs_password()

   Return `True` if the archive is encrypted, or is going to create
   encrypted archive. Otherwise return `False`


.. method:: SevenZipFile.extractall(path=None)

   Extract all members from the archive to current working directory.  *path*
   specifies a different directory to extract to.


.. method:: SevenZipFile.extract(path=None, targets=None)

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


.. method:: SevenZipFile.readall()

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


.. method:: SevenZipFile.read(targets=None)

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
        targets = [f if filter_pattern.match(f) for f in allfiles]
   with SevenZipFile('archive.7z', 'r') as zip:
        for fname, bio in zip.read(targets).items():
            print('{:s}: {:X}...'.format(name, bio.read(10))


.. method:: SevenZipFile.list()

    Return a List[FileInfo].


.. method:: SevenZipFile.archiveinfo()

    Return a ArchiveInfo object.


.. method:: SevenZipFile.test()

   Read all the archive file and check a packed CRC.
   Return ``True`` if CRC check passed, and return ``False`` when detect defeat,
   or return ``None`` when the archive don't have a CRC record.


.. method:: SevenZipFile.testzip()

    Read all the files in the archive and check their CRCs.
    Return the name of the first bad file, or else return ``None``.
    When the archive don't have a CRC record, it return ``None``.


.. method:: SevenZipFile.write(filename, arcname=None)

   Write the file named *filename* to the archive, giving it the archive name
   *arcname* (by default, this will be the same as *filename*, but without a drive
   letter and with leading path separators removed).
   The archive must be open with mode ``'w'``


.. method:: SevenZipFile.writeall(filename, arcname=None)

   Write the directory and its sub items recursively into the archive, giving
   the archive name *arcname* (by default, this will be the same as *filename*,
   but without a drive letter and with leading path seaprator removed).

   If you want to store directories and files, putting *arcname* is good idea.
   When filename is 'C:/a/b/c' and arcname is 'c', with a file exist as 'C:/a/b/c/d.txt',
   then archive listed as ['c', 'c/d.txt'], the former as directory.


.. method:: SevenZipFile.set_encrypted_header(mode)

   Set header encryption mode. When encrypt header, set mode to `True`, otherwise `False`.
   Default is `False`.


.. method:: SevenZipFile.set_encoded_header_mode(mode)

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

+---+----------------------+------------|-----------------------------+
|  #| Category             | Algorithm  | Note                        |
+===+======================+============|=============================+
|  1| - Compression        | LZMA2      |                             |
+---+ - Decompression      +------------------------------------------+
|  2|                      | LZMA       |                             |
+---+                      +------------------------------------------+
|  3|                      | Bzip2      |                             |
+---+                      +------------------------------------------+
|  4|                      | Deflate    |                             |
+---+                      +------------------------------------------+
|  5|                      | COPY       |                             |
+---+                      +------------------------------------------+
|  6|                      | PPMd       | require extra [ppmd]        |
+---+                      +------------------------------------------+
|  7|                      | ZStandard  | require extra [zstd]        |
+---+----------------------+------------------------------------------+
|  8| - Filter             | BCJ(X86, ARM, PPC, ARMT, SPARC, IA64)    |
+---+                      +------------------------------------------+
|  9|                      | Delta      |                             |
+---+----------------------+------------------------------------------+
| 10| - Encryption         | 7zAES      | depend on pycryptodome      |
|   | - Decryption         |            |                             |
+---+----------------------+------------------------------------------+
| 11| - Unsupported        | BCJ2, Deflate64                          |
+---+----------------------+------------------------------------------+

- A feature handling symbolic link is basically compatible with 'p7zip' implementation,
  but not work with original 7-zip because the original does not implement the feature.

- Decryption of filename encrypted archive is supported.

- ZStandard is supported when install with pip [zstd] option.



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
    ``[{'id': FILTER_ZSTD}]``

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

.. [#f1] Modes other than ```'r'``` and ```'w'``` have not implemented yet. If given other than 'r'
        or 'w', it will generate :exc:`NotImplementedError`

.. [#f2] *filter* is always ignored in current version.
