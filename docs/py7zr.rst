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

The module is built upon awesome development effort and knowlege of `pylzma` module
and its `py7zlib.py` program by Joachim Bauch. Great appreciation for Joachim!

The module defines the following items:

.. exception:: Bad7zFile

   The error raised for bad 7z files.


.. class:: SevenZipFile
   :noindex:

   The class for reading 7z files.  See section
   :ref:`sevenzipfile-objects` for constructor details.


.. class:: ArchiveFile(filename='NoName', date_time=(1980,1,1,0,0,0))

   Class used to represent information about a member of an archive. Instances
   of this class are returned by the :meth:`.getinfo` and :meth:`.infolist`
   methods of :class:`SevenZipFile` objects.  Most users of the :mod:`py4zr` module
   will not need to create these, but only use those created by this
   module. *filename* should be the full name of the archive member, and
   *date_time* should be a tuple containing six fields which describe the time
   of the last modification to the file; the fields are described in section
   :ref:`archivefile-objects`.


.. function:: is_7zfile(filename)

   Returns ``True`` if *filename* is a valid 7z file based on its magic number,
   otherwise returns ``False``.  *filename* may be a file or file-like object too.


.. seealso::

   `7z_format`_
      Documentation on the 7z file format by Igor Pavlov who craete algorithms
      and 7z archive format.


.. _sevenzipfile-objects:

SevenZipFile Objects
---------------


.. class:: SevenZipFile(file, mode='r', compressionlevel=None)

   Open a 7z file, where *file* can be a path to a file (a string), a
   file-like object or a :term:`path-like object`.

   The *mode* parameter should be ``'r'`` to read an existing
   file, ``'w'`` to truncate and write a new file, ``'a'`` to append to an
   existing file, or ``'x'`` to exclusively create and write a new file.
   If *mode* is ``'x'`` and *file* refers to an existing file,
   a :exc:`FileExistsError` will be raised.
   If *mode* is ``'r'`` or ``'a'``, the file should be seekable. [#]_

   The *compresslevel* parameter controls the compression level to use when
   writing files to the archive. Integers ``0`` through ``9`` are accepted. [#]_

.. [#]: Modes other than ```'r'``` has not implemented yet. If given other than 'r',
        it will generate :exc:`NotImplementedError`
.. [#]: *compresslevel* is always ignored in current version.

.. method:: SevenZipFile.close()

   Close the archive file.  You must call :meth:`close` before exiting your program
   or essential records will not be written. [#]_

.. [#]: Not implemented yet, the method will generate :exc:`NotImplementedError`

.. method:: SevenZipFile.getmember(name)

   Return a :class:`ArchiveFile` object with information about the archive member
   *name*.  Calling :meth:`getmember` for a name not currently contained in the
   archive will raise a :exc:`KeyError`.


.. method:: SevenZipFile.members()

   Return a list containing a :class:`ArchiveFile` object for each member of the
   archive.  The objects are in the same order as their entries in the actual 7z
   file on disk if an existing archive was opened.


.. method:: SevenZipFile.getnames()

   Return a list of archive members by name.



.. method:: SevenZipFile.extract(member, path=None)

   Extract a member from the archive to the current working directory; *member*
   must be its full name or a :class:`ArchiveFile` object.  Its file information is
   extracted as accurately as possible.  *path* specifies a different directory
   to extract to.  *member* can be a filename or a :class:`ArchiveFile` object. [#]_


.. method:: SevenZipFile.extractall(path=None)

   Extract all members from the archive to the current working directory.  *path*
   specifies a different directory to extract to. [#]_


.. method:: SevenZipFile.list()

   Print a table of contents for the archive to ``sys.stdout``.


.. method:: ZipFile.testzip()

   Read all the files in the archive and check their CRC's and file headers.
   Return the name of the first bad file, or else return ``None``. [#]_

.. [#]: Not implemented yet, the method will generate :exc:`NotImplementedError`


.. method:: SevenZipFile.write(filename, arcname=None)

   Write the file named *filename* to the archive, giving it the archive name
   *arcname* (by default, this will be the same as *filename*, but without a drive
   letter and with leading path separators removed).
   The archive must be open with mode ``'w'``, ``'x'`` or ``'a'``. [#]_

.. [#]: Not implemented yet, the method will generate :exc:`NotImplementedError`


.. _archivefile-objects:

ArchiveFile Objects
-------------------

Instances of the :class:`ArchiveFile` class are returned by the :meth:`.getmember` and
:meth:`.getmembers` methods of :class:`SevenZipFile` objects.  Each object stores
information about a single member of the 7z archive.

Instances have the following methods and attributes:

.. method:: ArchiveFile.is_dir()

   Return ``True`` if this archive member is a directory.

   This uses the entry's name: directories should always end with ``/``.


.. attribute:: ArchiveFile.filename

   Name of the file in the archive.


.. attribute:: ArchiveFile.CRC

   CRC-32 of the uncompressed file.


.. attribute:: ArchiveFile.compress_size

   Size of the compressed data.


.. attribute:: ArchiveFile.file_size

   Size of the uncompressed file.


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


.. _7z_format: https://www.7-zip.org/7z.html
