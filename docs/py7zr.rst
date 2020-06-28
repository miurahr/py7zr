======================================
:mod:`py7zr` --- 7-Zip archive library
======================================

.. module:: py7zr
   :synopsis: Read and write 7Z-format archive files.

.. moduleauthor:: Hiroshi Miura <miurahr@linux.com>

--------------

The 7z file format is a popular archive and compression format in recent days.
This module provides tools to read and list 7z file. Features is not implemented
to create, write and append a 7z file. py7zr does not support self-extracting archive,
aka. SFX file, and only support plain 7z archive file.

See :download:`Introductory presentation(PDF) <presentations/Introduction_of_py7zr.pdf>`,
and :download:`Introductory presentation(ODP) <presentations/Introduction_of_py7zr.odp>`.

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

+---+----------------------+------------------------------------------+
|  #| Category             | Algorithm combination                    |
+===+======================+==========================================+
|  1| - Compression        | LZMA2 + Delta or BCJ(X86, ARM, PPC,      |
|   | - Decompression      | IA64, ARMT, SPARC)                       |
+---+                      +------------------------------------------+
|  2|                      | LZMA + BCJ                               |
+---+                      +------------------------------------------+
|  3|                      | LZMA2 or LZMA only                       |
+---+                      +------------------------------------------+
|  4|                      | Bzip2, Deflate, ZStandard                |
+---+----------------------+------------------------------------------+
|  5| - Encryption         | 7zAES + LZMA2 + Delta or BCJ             |
+---+ - Decryption         +------------------------------------------+
|  6|                      | 7zAES + LZMA                             |
+---+                      +------------------------------------------+
|  7|                      | 7zAES + Bzip2, Deflate or ZStandard      |
+---+----------------------+------------------------------------------+
|  8| - Unsupported        | PPMd, BCJ2, Deflate64                    |
+---+                      +------------------------------------------+
|  9|                      | Bzip2, Deflate, ZStandard + BCJ          |
+---+----------------------+------------------------------------------+


The module is built upon awesome development effort and knowledge of `pylzma` module
and its `py7zlib.py` program by Joachim Bauch. Great appreciation for Joachim!

The module defines the following items:

.. exception:: Bad7zFile

   The error raised for bad 7z files.


.. class:: SevenZipFile
   :noindex:

   The class for reading 7z files.  See section
   :ref:`sevenzipfile-object` for constructor details.


.. class:: ArchiveInfo

   Class used to represent information about an information of an archive file. See section
   :ref:`archiveinfo-object` for fields details.


.. class:: FileInfo

    Class used to represent information about a member of an archive file. See section
    :ref:`fileinfo-objects` for fields details.


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


.. method:: SevenZipFile.extractall(path=None)

   Extract all members from the archive to current working directory.  *path*
   specifies a different directory to extract to.


.. method:: SevenZipFile.extract(path=None, targets=None)

   Extract specified pathspec archived files to current working directory.
   'path' specifies a differenct directory to extract to.

   'targets' is a list of archived files to be extracted. py7zr looks for files
   and directories as same as specified in 'targets'.

   **CAUTION** when specifying files and not specifying parent directory,
   py7zr will fails with no such directory. When you want to extract file
   'somedir/somefile' then pass a list: ['somedirectory', 'somedir/somefile']
   as a target argument.

   Please see 'tests/test_basic.py: test_py7zr_extract_and_getnames()' for
   example code.


.. method:: SevenZipFile.readall()

   Extract all members from the archive to memory and returns dictionary object.
   Returned dictionary has a form of Dict[filename: str, BinaryIO: io.ByteIO object].
   So you can get extracted data from dictionary value as such

.. code-block:: python

   with SevenZipFile('archive.7z', 'r') as zip:
        archives = zip.readall()
        for fname in zip.readall():
            bio = archives[fname]
            data = bio.read()


.. method:: SevenZipFile.read(target=None)

   Extract specified pathspec archived files to dictionary object.
   'targets' is a list of archived files to be extracted. py7zr looks for files
   and directories as same as specified in 'targets'.


.. method:: SevenZipFile.list()

    Return a List[FileInfo].


.. method:: SevenZipFile.archiveinfo()

    Return a ArchiveInfo object.


.. method:: SevenZipFile.test()

   Read all the archive file and check a packed CRC.
   Return ``True`` if CRC check passed, and return ``False`` when detect defeat,
   or return ``None`` when the archive don't have a CRC record.


-.. method:: SevenZipFile.testzip()

    Read all the files in the archive and check their CRCs.
    Return the name of the first bad file, or else return ``None``.
    When the archive don't have a CRC record, it return ``None``.


.. method:: SevenZipFile.write(filename, arcname=None)

   Write the file named *filename* to the archive, giving it the archive name
   *arcname* (by default, this will be the same as *filename*, but without a drive
   letter and with leading path separators removed).
   The archive must be open with mode ``'w'``


Possible filters value
^^^^^^^^^^^^^^^^^^^^^^

Here is a list of examples for possible filters values.
You can use it when creating SevenZipFile object.

.. code-block::

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


.. _archiveinfo-object:

ArchiveInfo Object
--------------------

ArchiveInfo object represent archive information.



.. _fileinfo-objects:

FileInfo Objects
--------------------

FileInfo objects represent a file information of member of archive.



.. _py7zr-commandline:
.. program:: py7zr


Command-Line Interface
======================

The :mod:`py7zr` module provides a simple command-line interface to interact
with 7z archives.

If you want to extract a 7z archive into the specified directory, use
the :option:`x` subcommand:

.. code-block:: shell-session

    $ python -m py7zr x monty.7z target-dir/
    $ py7zr x monty.7z

For a list of the files in a 7z archive, use the :option:`l` subcommand:

.. code-block:: shell-session

    $ python -m py7zr l monty.7z
    $ py7zr l monty.7z


Command-line options
--------------------

.. option:: l <7z file>

   List files in a 7z file.

.. option:: x <7z file> [<output_dir>]

   Extract 7z file into target directory.

.. option:: c <7z file> <base_dir>

   Create 7zip archive from base_directory

.. option:: i <7z file>

   Show archive information of specified 7zip archive.

.. option:: t <7z file>

   Test whether the 7z file is valid or not.


Extract command options
-----------------------

.. option:: -P --password

   Extract password protected archive. py7zr will prompt user input.


.. option:: --verbose

   Show verbose debug log.


List command options
--------------------

.. option:: --verbose

   Show verbose debug log.


Create command options
----------------------

.. option:: -v | --volume {Size}[b|k|m|g]

   Create multi-volume archive with Size. Usable with 'c' sub-command.

.. option:: -P --password

   Create password protected archive. py7zr will prompt user input.


.. _shutil: https://docs.python.org/3/library/shutil.html


.. rubric:: Footnotes

.. [#f1] Modes other than ```'r'``` and ```'w'``` have not implemented yet. If given other than 'r'
        or 'w', it will generate :exc:`NotImplementedError`

.. [#f2] *filter* is always ignored in current version.

.. [#f3] Not implemented yet, the method will generate :exc:`NotImplementedError`
