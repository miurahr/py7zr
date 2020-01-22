:mod:`py7zr` --- Work with 7Z archives (restricted version)
===========================================================

.. module:: py7zr
   :synopsis: Read and write 7Z-format archive files.

.. moduleauthor:: Hiroshi Miura <miurahr@linux.com>

--------------

The 7z file format is a popular archive and compression format in recent days.
This module provides tools to read and list 7z file. Features is not implemented
to create, write and append a 7z file.  Any advanced use of this module will
require an understanding of the format, as defined in `7z_format`_.

'py7zr' supports extraction and compression. Both features have limitations;

- There are unsupported compression algorithms, because Python core does not support it. it support

    * lzma
    * lzma2
    * BCJ

and not support

    * ppmd
    * bcj2

/home/miurahr/projects/py7zr/venvpy/bin/pypy3 /home/miurahr/lib/apps/PyCharm-P/ch-0/193.5662.61/plugins/python/helpers/pycharm/_jb_tox_runner.py -e docs
GLOB sdist-make: /home/miurahr/projects/py7zr/setup.py
docs inst-nodeps: /home/miurahr/projects/py7zr/.tox/.tm
- A feature handling symbolic link is basically compatible with 'p7zip' implementation,
  but not work with original 7-zip because the original does not implement the feature.


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

   (external link) `7z_format`_ Documentation of the 7z file format by Igor Pavlov who craete algorithms and 7z archive format.

.. seealso::

   (external link) `shutil`_  :mod:`shutil` module offers a number of high-level operations on files and collections of files.


.. _sevenzipfile-object:

SevenZipFile Object
-------------------


.. class:: SevenZipFile(file, mode='r', filters=None)

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


.. method:: SevenZipFile.close()

   Close the archive file.  You must call :meth:`close` before exiting your program
   or most records will not be written.


.. method:: SevenZipFile.getnames()

   Return a list of archive files by name.


.. method:: SevenZipFile.extractall(path=None)

   Extract all members from the archive to the current working directory.  *path*
   specifies a different directory to extract to.


.. method:: SevenZipFile.list()

    Return a List[FileInfo].


.. method:: SevenZipFile.archiveinfo()

    Return a ArchiveInfo object.


.. method:: SevenZipFile.testzip()

   Read all the files in the archive and check their CRC's and file headers.
   Return the name of the first bad file, or else return ``None``. [#f3]_


.. method:: SevenZipFile.write(filename, arcname=None)

   Write the file named *filename* to the archive, giving it the archive name
   *arcname* (by default, this will be the same as *filename*, but without a drive
   letter and with leading path separators removed).
   The archive must be open with mode ``'w'``


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
----------------------

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
~~~~~~~~~~~~~~~~~~~~

.. cmdoption:: l <7z file>

   List files in a 7z file.

.. cmdoption:: x <7z file> [<output_dir>]

   Extract 7z file into target directory.

.. cmdoption:: t <7z file>

   Test whether the 7z file is valid or not.

.. cmdoption:: w <7z file> <base_dir>

   Create 7zip archive from base_directory


.. _7z_format: https://www.7-zip.org/7z.html

.. _shutil: https://docs.python.org/3/library/shutil.html


.. rubric:: Footnotes

.. [#f1] Modes other than ```'r'``` and ```'w'``` have not implemented yet. If given other than 'r'
        or 'w', it will generate :exc:`NotImplementedError`

.. [#f2] *filter* is always ignored in current version.

.. [#f3] Not implemented yet, the method will generate :exc:`NotImplementedError`
