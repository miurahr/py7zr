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

The module is built upon awesome development effort and knowledge of `pylzma` module
and its `py7zlib.py` program by Joachim Bauch. Great appreciation for Joachim!

The module defines the following items:

.. exception:: Bad7zFile

   The error raised for bad 7z files.


.. class:: SevenZipFile
   :noindex:

   The class for reading 7z files.  See section
   :ref:`sevenzipfile-objects` for constructor details.


.. class:: ArchiveFile

   Class used to represent information about a member of an archive. Instances
   of this class are returned by iteration of :attribute:`files_list` of :class:`SevenZipFile` objects.
   Most users of the :mod:`py7zr` module should not create these, but only use those created by this
   module.
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


.. method:: SevenZipFile.getnames()

   Return a list of archive files by name.


.. method:: SevenZipFile.extractall(path=None)

   Extract all members from the archive to the current working directory.  *path*
   specifies a different directory to extract to.


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

Instances of the :class:`ArchiveFile` class are returned by iterating :attribute:`files_list`
 of :class:`SevenZipFile` objects.
Each object stores information about a single member of the 7z archive.
Most of users don't use those directory, but use :method:`extractall()` instead.

Instances have the following methods and attributes:

.. method:: ArchiveFile.get_properties()

   Return file properties as a hash object. Following keys are included:
   'readonly', 'is_directory', 'posix_mode', 'archivable',
   'emptystream', 'filename', 'creationtime', 'lastaccesstime', 'lastwritetime',
   'attributes'


.. attribute:: ArchiveFile.posix_mode

   posix mode when a member has a unix extension property, or None


.. attribute:: ArchiveFile.id

   Reference identifier number of a member.


.. attribute:: ArchiveFile.filename

   Name of the file in the archive.


.. attribute:: ArchiveFile.lastwritetime

   Value of lastwritetime property of a member


.. attribute:: ArchiveFile.is_directory

   ``True`` if this archive member is a directory.

   This uses the entry's name: directories should always end with ``/``.


.. attribute:: ArchiveFile.is_symlink

   ``True`` if this archive member is a symbolic link.


.. attribute:: ArchiveFile.archivable

   ``True`` if `Archive` property of a member is enabled, otherwise ``False``.


.. attribute:: ArchiveFile.readonly

   ``True`` if `Readonly` property of a member is enabled, otherwise ``False``.


.. attribute:: ArchiveFile.emptystream

   ``True`` if a member don't have a data stream, otherwise ``False``.


.. attribute:: ArchiveFile.uncompressed_size

   Size of the uncompressed file.


.. attribute:: ArchiveFile.uncompressed

   Array data of uncompressed property of a member.


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
