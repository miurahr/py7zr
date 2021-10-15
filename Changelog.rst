===============
Py7zr ChangeLog
===============

All notable changes to this project will be documented in this file.

`Unreleased`_
=============

`v0.16.2`_
==========

Added
-----
* Bundle type hint data
* README: Add conda recipe(#342)

Changed
-------
* Use PyBCJ instead of bcj-cffi.(#368)
* Docs: change recommended python versions
* CI: benchmark on python 3.10
* Test expectation for python 3.10 change
* Improve exceptions and error messages
* Docs: add descriptionof ArchiveInfo class
* Docs: fix typo on shutil integration(#353)
* Bump pyzstd@0.15.0
* Bump pyppmd@0.17.0

Fixed
-----
* Docs: specification error of signature header data types.
* Fix infinite loop in extract(#354)

`v0.16.1`_
==========

Added
-----
* type hint for mypy

`v0.16.0`_
==========

Added
-----
* Add Brotli compression.
* CI: Test on AArch64.

Changed
-------
* CLI: support multi-volume archive without making temporary file(#311)
* Filter parameter: PPMd: mem is now accept int or "<val>{m|k|b}" as same as 7-zip command line option.
  int value is recognized as "1 << val" ie. 24 means 4MB.
* Dependency: PyPPMd v0.14.0+
* Dependency PyCryptodome to PyCryptodomex
  that changes package name from PyCrypto to PyCryptodome(#334)

`v0.15.2`_
==========

Added
-----
- CLI: create sub-command(c) has -P or --password option.(#332)

Fixed
-----
- Fix not to produce directory when memory extraction mode.(#323)

Changed
-------
- Use PyPPMd v0.12.1 or later for ppmd compression instead of ppmd-cffi(#322)
- Add minimum version requirement for PyCryptodome (#329)
- Bump setuptools_scm @6.0.1


`v0.15.1`_
==========

Changed
-------
- Update release automation script.
- Bump ppmd-cffi and bcj-cffi versions(#320)


`v0.15.0`_
==========

Added
-----
- Add option to specify multiprocessing instead of multi-threading. (#306)

Changed
-------
- Change Property Borg class to constant class(#319)
- Reformat whole code with black.
- Merge pyzstdfilter into compressor.py.
- Lint codes by flake8/black.

Fixed
-----
- README: description of dependencies.
- ZStandard decompression on PyPy3


`v0.14.1`_
==========

Fixed
-----

* Fix of empty file archive(#305,#310)


`v0.14.0`_
==========

Added
-----

* Introduce writed() method that accept dict[name, BinaryIO](#302)

Changed
-------

* READ_BLOCKSIZE configurable on constructor(#307)
* Use pyzstd for zstandard algorithm on CPython(#304)
* Use bcj-cffi library for lzma+bcj performance(#303)
* CLI: Fix getting module_name on 3.6.13(#308)



`v0.13.0`_
==========

Added
-----

* Add writestr() and writef() methods in SevenZipFile class.(#290,#293)
* Add benchmark tests for compression algorithms(#295)
* Track benchmark results on Github issue(#296)

Changed
-------

* Refactoring BCF Filter classes, and move to individual module.(#292)


`v0.12.0`_
==========

Changed
-------

* PPMd and ZStandard is now one of default algorithms(#289)
* Increment copyright year

Fixed
-----

* Crash when append files to an empty files archive(#286)


`v0.11.3`_
==========

Fixed
-----

* Fix test failure when running on pypi source(#279)

Security
--------

* Drop issue_218.7z test data wihch is reported a blackmoon trojan(#285)


`v0.11.1`_
==========

Changed
-------
* Improve BCJ filter performance with LZMA1, ZStd compressions.

Fixed
-----

* Fix to allow writing encrypted header(#280)
* Avoid crash when creationtime is wrong or Unix epoch. (#275,#276)


`v0.11.0`_
==========

Changed
-------

* PPMd: Use stream encoder/decoder instead of buffered one.
* PPMd: Use ppmd-cffi@v0.3.1 and later.(#268)

Added
-----

* PPMd compression/decompression support.(#255)
* New API to set methods to set header encode mode, encode or encrypted.(#259)
* Support Python 3.9.(#261)
* Support arm64/aarch64 architecture on Linux.(#262)

Fixed
-----

* Append mode cause error when target archive use LZMA2+BCJ.(#266)
* Fix zstandard compression/decompression.(#258)

Deprecated
----------

* Drop support for python 3.5 which become end-of-line in Sept. 2020.


.. History links
.. _Unreleased: https://github.com/miurahr/py7zr/compare/v0.16.2...HEAD
.. _v0.16.2: https://github.com/miurahr/py7zr/compare/v0.16.1...v0.16.2
.. _v0.16.1: https://github.com/miurahr/py7zr/compare/v0.16.0...v0.16.1
.. _v0.16.0: https://github.com/miurahr/py7zr/compare/v0.15.2...v0.16.0
.. _v0.15.2: https://github.com/miurahr/py7zr/compare/v0.15.1...v0.15.2
.. _v0.15.1: https://github.com/miurahr/py7zr/compare/v0.15.0...v0.15.1
.. _v0.15.0: https://github.com/miurahr/py7zr/compare/v0.14.1...v0.15.0
.. _v0.14.1: https://github.com/miurahr/py7zr/compare/v0.14.0...v0.14.1
.. _v0.14.0: https://github.com/miurahr/py7zr/compare/v0.13.0...v0.14.0
.. _v0.13.0: https://github.com/miurahr/py7zr/compare/v0.12.0...v0.13.0
.. _v0.12.0: https://github.com/miurahr/py7zr/compare/v0.11.3...v0.12.0
.. _v0.11.3: https://github.com/miurahr/py7zr/compare/v0.11.1...v0.11.3
.. _v0.11.1: https://github.com/miurahr/py7zr/compare/v0.11.0...v0.11.1
.. _v0.11.0: https://github.com/miurahr/py7zr/compare/v0.10.1...v0.11.0
