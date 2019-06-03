===============
Py7zr ChangeLog
===============

All notable changes to this project will be documented in this file.

***************
Current changes
***************

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

`v0.2.0`_
=============

Fixed
-----

* Detect race condition on os.mkdir

`v0.1.6`_
=============

Fixed
-----

* Wrong file size when lzma+bcj compression.

`v0.1.5`_
=============

Fixed
-----

* Suppress warning: not dequeue from queue length 0

`v0.1.4`_
=============

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
.. _Unreleased: https://github.com/miurahr/py7zr/compare/v0.2.0...HEAD
.. _v0.1.5: https://github.com/miurahr/py7zr/compare/v0.1.6...v0.2.0
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
