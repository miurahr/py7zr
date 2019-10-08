:tocdepth: 2

.. _internal_classes:

================
Internal classes
================

.. _archivefile-objects:

ArchiveFile Objects
-------------------

Instances of the :class:`ArchiveFile` class are returned by iterating :attr:`files_list` of :class:`SevenZipFile` objects.
Each object stores information about a single member of the 7z archive. Most of users use :meth:`extractall()`.

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

