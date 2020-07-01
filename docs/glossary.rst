.. _glossary:

Glossary
========

.. if you add new entries, keep the alphabetical sorting!

.. glossary::

   binary file
      A :term:`file object` able to read and write
      :term:`bytes-like objects <bytes-like object>`.
      Examples of binary files are files opened in binary mode (``'rb'``,
      ``'wb'`` or ``'rb+'``), :data:`sys.stdin.buffer`,
      :data:`sys.stdout.buffer`, and instances of :class:`io.BytesIO` and
      :class:`gzip.GzipFile`.

      See also :term:`text file` for a file object able to read and write
      :class:`str` objects.

   bytes-like object
      An object that supports the `bufferobjects` and can
      export a C-:term:`contiguous` buffer. This includes all :class:`bytes`,
      :class:`bytearray`, and :class:`array.array` objects, as well as many
      common :class:`memoryview` objects.  Bytes-like objects can
      be used for various operations that work with binary data; these include
      compression, saving to a binary file, and sending over a socket.

      Some operations need the binary data to be mutable.  The documentation
      often refers to these as "read-write bytes-like objects".  Example
      mutable buffer objects include :class:`bytearray` and a
      :class:`memoryview` of a :class:`bytearray`.
      Other operations require the binary data to be stored in
      immutable objects ("read-only bytes-like objects"); examples
      of these include :class:`bytes` and a :class:`memoryview`
      of a :class:`bytes` object.

   contiguous
      .. index:: C-contiguous, Fortran contiguous

      A buffer is considered contiguous exactly if it is either
      *C-contiguous* or *Fortran contiguous*.  Zero-dimensional buffers are
      C and Fortran contiguous.  In one-dimensional arrays, the items
      must be laid out in memory next to each other, in order of
      increasing indexes starting from zero.  In multidimensional
      C-contiguous arrays, the last index varies the fastest when
      visiting items in order of memory address.  However, in
      Fortran contiguous arrays, the first index varies the fastest.

   file object
      An object exposing a file-oriented API (with methods such as
      :meth:`read()` or :meth:`write()`) to an underlying resource.  Depending
      on the way it was created, a file object can mediate access to a real
      on-disk file or to another type of storage or communication device
      (for example standard input/output, in-memory buffers, sockets, pipes,
      etc.).  File objects are also called :dfn:`file-like objects` or
      :dfn:`streams`.

      There are actually three categories of file objects: raw
      :term:`binary files <binary file>`, buffered
      :term:`binary files <binary file>` and :term:`text files <text file>`.
      Their interfaces are defined in the :mod:`io` module.  The canonical
      way to create a file object is by using the :func:`open` function.

   file-like object
      A synonym for :term:`file object`.

   text file
      A :term:`file object` able to read and write :class:`str` objects.
      Often, a text file actually accesses a byte-oriented datastream
      and handles the text encoding automatically.
      Examples of text files are files opened in text mode (``'r'`` or ``'w'``),
      :data:`sys.stdin`, :data:`sys.stdout`, and instances of
      :class:`io.StringIO`.

      See also :term:`binary file` for a file object able to read and write
      :term:`bytes-like objects <bytes-like object>`.

   path-like object
      An object representing a file system path. A path-like object is either
      a :class:`str` or :class:`bytes` object representing a path, or an object
      implementing the :class:`os.PathLike` protocol. An object that supports
      the :class:`os.PathLike` protocol can be converted to a :class:`str` or
      :class:`bytes` file system path by calling the :func:`os.fspath` function;
      :func:`os.fsdecode` and :func:`os.fsencode` can be used to guarantee a
      :class:`str` or :class:`bytes` result instead, respectively. Introduced
      by :pep:`519`.
