===============
Py7zr ChangeLog
===============

All notable changes to this project will be documented in this file.

`Unreleased`_
=============

Added
-----

Changed
-------

Fixed
-----

Deprecated
----------

Removed
-------

Security
--------

`v0.5rc3`_
==========

Fixed
-----

* Fix symbolic link extraction with relative path target directory.

`v0.5rc2`_
==========

Added
-----

* Support COPY method for decompression.

Changed
-------

* When archive has an archive which is same name, then write
  with postfix '_0'.

`v0.5rc1`_
==========

Added
-----

* Add release note automation workflow with Github actions.

`v0.5b6`_
=========

Fixed
-----

* Fix extraction of archive which has zero size files and directories(#54).
* Revert zero size file logic(#47).

`v0.5b5`_
=========

Fixed
-----

* Revert zero size file logic which break extraction by 7zip.

`v0.5b4`_
=========

Fixed
-----

* Support for making archive with zero size files(#47).
* Produced broken archive when target has many directorires(#48).
* Reduce test warnings, fix annotations.
* Fix coverage error on test.


`v0.5b3`_
=========

Fixed
-----

* Support for making archive with symbolic links.


`v0.5b2`_
=========

Changed
-------

* Update documents.

Fixed
-----

* Fix write logics (#42)
* Fix read FilesInfo block.


`v0.5b1`_
=========

Support making a 7zip archive.

Added
-----

* Support for compression and archiving.
* Support encoded(compressed) header and set as default.(#39)
* SevenZipFile: accept pathlib.Path as a file argument.
* Unit test: read and write UTF-16LE string for filename.
* Support for shutil.register_archive_format() and
  shutil.make_archive() by exposing pack_7zarchive()
* Support custom filters for compression.

Fixed
-----

* Skip rare case when directory already exist, that can happen multiple process working
  in same working directory.
* Write: Produce a good archive file for multiple target files.
* SignatureHeader function: write nextheaderofs and nextheadersize as real_uint64.
* docs: description of start header structure.

Removed
-------

* Drop py7zr.properties.FileAttributes; please use stat.FILE_ATTRIBUTES_*

Changed
-------

* Test: Use tmp_path fixture which is pytest default one.
* Move setuptools configurations in setup.py into setup.cfg.


`v0.4`_
=======

Added
-----

* Support for pypy3 (pypy3.5-7.0) and later(pypy3.6-7.1 or later).
* unit test for NullHandler, BufferHandler, FileHandler.
* Update document to add 7zformat descriptions.

Changed
-------

* NullHandler, BufferHandler, FileHandler: open() now takes mode argument.
* Upper limit of max_length of decompress() call is now io.DEFAULT_BUFFER_SIZE.
  - PyPy issue: https://bitbucket.org/pypy/pypy/issues/3088/lzmalzmadecompressordecompress-data
* Drop padding logic introduced in v0.3.5 that may be cuased by python core bug,
  when max_length > io.DEFAULT_BUFFER_SIZE.
  - PyPy Issue: https://bitbucket.org/pypy/pypy/issues/3090/lzma-sometimes-decompresses-data
  - bpo-21872: https://bugs.python.org/issue21872
  - Fix: https://github.com/python/cpython/pull/14048
* Remove print functions from API and moves CLI
    - API should not output anything other than error message.
      * Introduce FileInfo class to represent file attributes inside
      archive.
      * Introduce ArchiveInfo class to represent archive attributes.
      * provide archiveinfo() method to provide ArchiveInfo object.
      * now list() method returns List[FileInfo]
    - Every print things moves to Cli class.
* Update tests according to API change.
* Update documents to refrect API changes.

Fixed
-----

* Update README to indicate supported python version as 3.5 and later, pypy3 7.1 and later.



`v0.3.5`_
=========

Changed
-------

* Use seek&truncate for padding trailer if needed.


`v0.3.4`_
=========

Added
-----

* Docs: class diagram, design note, 7z formats and presentations.
* Test for a target includes padding file.

Changed
-------

* Test file package naming.

Fixed
-----

* Fix infinite loop when archive file need padding data for extraction.


`v0.3.3`_
=========

Added
-----

* Add test for zerofile with multi-foler archive.

Fixed
-----

* Fix zerofile extraction error with multithread mode(#24, thanks @Arten013)

`v0.3.2`_
=========

Added
-----

* typing hints
* CI test with mypy
* Unit test: SignatureHeader.write() method.
* Unit test: unknown mode for SevenZipFile constructor.
* Unit test: SevenZipFile.write() method.

Changed
-------

* Conditional priority not likely to be external in header.
* Refactoring read_uint64().

Fixed
-----

* SignatureHeader.write(): fix exception to write 7zip version.


`v0.3.1`_
=========

Added
-----

* CLI i subcommand: show codec information.
* Decompression performance test as regression test.
* Add more unit test for helper functions.

Changed
-------

* List subcommand now do not show compressed file size in solid compression.
  This is as same behavior as p7zip command.
* Merge io.py into archiveinfo.py
* Drop internal intermediate queue, which is not used.

Fixed
-----

* Always overwrite when archive has multiple file with same name.


`v0.3`_
=======

Added
-----

* Add some code related to support write feature(wip).
* Static check for import order in python sources and MANIFEST.in

Changed
-------

* Concurrent decompression with threading when an archive is in multi folder compression.
* Pytest configurations are set in tox.ini

Fixed
-----

* Package now has test code and data.


`v0.2.0`_
=========

Fixed
-----

* Detect race condition on os.mkdir

`v0.1.6`_
=========

Fixed
-----

* Wrong file size when lzma+bcj compression.

`v0.1.5`_
=========

Fixed
-----

* Suppress warning: not dequeue from queue length 0

`v0.1.4`_
=========

Changed
-------

* When a directory exist for target, do not raise error, and when out of it raise exception
* Refactoring FileArchivesList and FileArchive classes.

`v0.1.3`_
=========

Changed
-------

* When a directory exist for target, do not raise error, and when out of it raise exception


`v0.1.2`_
=========

Changed
-------

* Refactoring CLI with cli package and class.

Fixed
-----

* Archive with zero size file cause exception with file not found error(#4).

Removed
-------

* Drop unused code chunks.
* Drop Digests class and related unit test.


`v0.1.1`_
=========

Added
-----

* Add write(), close() and testzip() dummy methods which raises NotImplementedError.
* Add more unit tests for write functions.

Fixed
-----

* Fix Sphinx error in documentation.
* SevenZipFile: Check mode before touch file.
* Fix write_boolean() when array size is over 8.
* Fix write_uint64() and read_uint64().


`v0.1.0`_
=========

Added
-----

* Introduce compression package.
* Introduce SevenZipCompressor class.
* Add write() method for each header class.
* Add tests for write methods.
* Add method for registering shutil.

Changed
-------

* Each header classes has __slots__ definitions for speed and memory optimization.
* Rename to 'io' package from 'archiveio'
* Each header classes has classmethod 'retrieve' and constructor does not reading a archive file anymore.
* Change to internalize _read() method for each header classes.
* get_decompressor() method now become SevenZipDecompressor class.
* Each header classes initializes members to None in constructor.
* Method definitions map become an internal member of SevenZipDecompressor or SevenZipCompressor class.
* Add test package compress

Fixed
-----

* Fix ArchiveProperties read function.


`v0.0.8`_
=========

Added
-----

* Test for CLI.

Changed
-------

* Improve main function.
* Improve tests, checks outputs with sha256


`v0.0.7`_
=========

Added
-----

* CI test on AppVeyor.

Changed
-------

* Worker class refactoring.

Fixed
-----

* Fix test cases: bugzilla_16 and github_14.
* Test: set timezone to UTC on Unix and do nothing on Windows.



`v0.0.6`_
=========

Fixed
-----

* Fix too many file descriptors opened error.


`v0.0.5`_
=========

Changed
-------

* Test: check sha256 for extracted files

Fixed
-----

* Fix decompressiong archive with LZMA2 and BCJ method
* Fix decompressing multi block archive
* Fix file mode on unix/linux.


`v0.0.4`_
=========

Added
-----

* Set file modes for extracted files.
* More unit test.

Changed
-------

* Travis-CI test on python 3.7.

Fixed
-----

* Fix to set extracted files timestamp as same as archived.


`v0.0.3`_
=========

Added
-----

* PyPi package index.

Fixed
-----

* setup: set universal = 0 because only python 3 is supported.


`v0.0.2`_
=========

Changed
-------

* refactoring all the code.


.. History links
.. _Unreleased: https://github.com/miurahr/py7zr/compare/v0.5rc2...HEAD
.. _v0.5rc2: https://github.com/miurahr/py7zr/compare/v0.5rc1...v0.5rc2
.. _v0.5rc1: https://github.com/miurahr/py7zr/compare/v0.5b6...v0.5rc1
.. _v0.5b6: https://github.com/miurahr/py7zr/compare/v0.5b5...v0.5b6
.. _v0.5b5: https://github.com/miurahr/py7zr/compare/v0.5b4...v0.5b5
.. _v0.5b4: https://github.com/miurahr/py7zr/compare/v0.5b3...v0.5b4
.. _v0.5b3: https://github.com/miurahr/py7zr/compare/v0.5b2...v0.5b3
.. _v0.5b2: https://github.com/miurahr/py7zr/compare/v0.5b1...v0.5b2
.. _v0.5b1: https://github.com/miurahr/py7zr/compare/v0.4...v0.5b1
.. _v0.4: https://github.com/miurahr/py7zr/compare/v0.3.5...v0.4
.. _v0.3.5: https://github.com/miurahr/py7zr/compare/v0.3.4...v0.3.5
.. _v0.3.4: https://github.com/miurahr/py7zr/compare/v0.3.3...v0.3.4
.. _v0.3.3: https://github.com/miurahr/py7zr/compare/v0.3.2...v0.3.3
.. _v0.3.2: https://github.com/miurahr/py7zr/compare/v0.3.1...v0.3.2
.. _v0.3.1: https://github.com/miurahr/py7zr/compare/v0.3...v0.3.1
.. _v0.3: https://github.com/miurahr/py7zr/compare/v0.2.0...v0.3
.. _v0.2.0: https://github.com/miurahr/py7zr/compare/v0.1.6...v0.2.0
.. _v0.1.6: https://github.com/miurahr/py7zr/compare/v0.1.5...v0.1.6
.. _v0.1.5: https://github.com/miurahr/py7zr/compare/v0.1.4...v0.1.5
.. _v0.1.4: https://github.com/miurahr/py7zr/compare/v0.1.3...v0.1.4
.. _v0.1.3: https://github.com/miurahr/py7zr/compare/v0.1.2...v0.1.3
.. _v0.1.2: https://github.com/miurahr/py7zr/compare/v0.1.1...v0.1.2
.. _v0.1.1: https://github.com/miurahr/py7zr/compare/v0.1.0...v0.1.1
.. _v0.1.0: https://github.com/miurahr/py7zr/compare/v0.0.8...v0.1.0
.. _v0.0.8: https://github.com/miurahr/py7zr/compare/v0.0.7...v0.0.8
.. _v0.0.7: https://github.com/miurahr/py7zr/compare/v0.0.6...v0.0.7
.. _v0.0.6: https://github.com/miurahr/py7zr/compare/v0.0.5...v0.0.6
.. _v0.0.5: https://github.com/miurahr/py7zr/compare/v0.0.4...v0.0.5
.. _v0.0.4: https://github.com/miurahr/py7zr/compare/v0.0.3...v0.0.4
.. _v0.0.3: https://github.com/miurahr/py7zr/compare/v0.0.2...v0.0.3
.. _v0.0.2: https://github.com/miurahr/py7zr/compare/v0.0.1...v0.0.2
