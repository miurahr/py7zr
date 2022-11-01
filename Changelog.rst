===============
Py7zr Changelog
===============

All notable changes to this project will be documented in this file.

`Unreleased`_
=============

`v0.18.11`_
===========

Security
--------

* Fix sanity check for path traversal attack(#480)
* Add path checker in writef() and writestr() methods that ignores evil pass.
  - When pass arcname as evil path such as "../../../../tmp/evil.sh"
  - it raises ValueError
* Check symlink and junction is under target folder when extraction
* Add protection test against path traversal attack and symlink attack

`v0.18.10`_
===========

Fixed
-----

* Actions: fix release script to produce wheel.
  there is no wheel release for v0.18.5-v0.18.9

`v0.18.9`_
==========

Fixed
-----

* Closing a SevenZipFile opened for appending, without adding a new file, raises exception (#378, #395)
* Docs: fix URL link error (#450)
* Actions: fix document compilation by installing graphviz (#450)
* Docs: fix errors and warnings on documentation.

Changed
-------

* Add changelog into Documentation (#450)
* Test on python 3.11-beta (#450)
* Bump Sphinx@5.0 for Documentation (#450)
* Docs: update configuration to ignore changelog links for link check

`v0.18.7`_
==========

Fixed
-----

* Extraction wrongly renames unix hidden dot files/directories (#448)

`v0.18.6`_
==========

Fixed
-----

* Decompression of some LZMA+BCJ archive may abort with gegmentation fault
  because of a PyBCJ bug. Bump ``PyBCJ@0.6.0`` that fixed it. (#447)

Removed
-------

* Remove in-source BCJ filter pure python code.
  Now it have a place in a PyBCJ project. (#447)

`v0.18.5`_
==========

Fixed
-----
* Limit memory consumption for extraction(#430,#434,#440)
* Pyproject.toml: setuptools_scm configuration(#438)

Changed
-------
* Build package with ``pip wheel`` with python 3.9 on Ubuntu 20.04
* Check py3.8, 3.9 and 3.10 on Azure-Pipelines CI/CD.

`v0.18.4`_
==========

Fixed
-----
* Raise exception properly when threaded extraction(#431,#432)
* Actions: fix tox test(#433)

Changed
-------
* Change pyproject.toml:license table to be text key and SPDX license name(#435, #436)

`v0.18.3`_
==========

Fixed
-----
* ppmd: send extra byte b"\0" to pyppmd.Ppmd7Decompressor,
  when input is exhausted, but it indicate needs_input.
  This is a same behavior as p7zip decoder does. (#417)
* README: fix example code(#426)

Changed
-------
* Bump ``PyPPMd@0.18.1`` (#420,#427)
* pyproject.toml: Add project section(#428)

`v0.18.1`_
==========

Changed
-------
* Limit dependency pyppmd to v0.17.x

Fixed
-----
* Fix mypy error with mypy 0.940(#421)

`v0.18.0`_
==========

Added
-----
* Support DEFLATE64 decompression(#399)

Fixed
-----
* Docs: fix typo for readall method argument(#416)

Changed
-------
* Get status down for PPMd compression/decompression(#418)
  PPMd decompression has a bug easily to fail decompression.

`v0.17.4`_
==========

Fixed
-----
* When extracting and target archive compressed with unsupported LZMA2+BCJ2, py7zr raise unexpected exception. Fix to raise better exception message

Changed
-------
* docs: Add explanation of empty file specification

`v0.17.3`_
==========

Security
--------
* Check against directory traversal attack by file pathes in archive (#406,#407)

`v0.17.2`_
==========

Fixed
-----
* writef method detect wrong size of data(#397)

Changed
-------
* Improve callback object check and error message(#387)

`v0.17.1`_
==========

Fixed
-----
* Allow 7zAES+LZMA2+BCJ combination for compression(#392)
* Argument error when raising UnsupportedCompressionMethodError(#394)
* Detect memory leak in test and fix some leaks(#388)
* Fix filename and property decode in UTF-16(#391)

Changed
-------
* Azure: use ``macos@10.15`` for test(#389)

`v0.17.0`_
==========

Fixed
-----
* Extraction: overwrite a symbolic link sometimes failed(#383)
* Allow creation of archive without any write call(#369,#372)
* Type check configuration update (#384)
* Adjust for type check errors (#384)

`v0.16.4`_
==========

Fixed
-----
* Win32 file namespace convention doesn't work on Cygwin(#380,#381)
* Win32 file namespace convention doesn't work for network path(#380)

`v0.16.3`_
==========

Fixed
-----
* Reduce memory consumptions and fix memory_error on 32bit python (#370,#373,#374,#375)

Added
-----
* Add CI test for python 3.10 (#371)

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
* Docs: add description of ArchiveInfo class
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
.. _Unreleased: https://github.com/miurahr/py7zr/compare/v0.18.11...HEAD
.. _v0.18.11: https://github.com/miurahr/py7zr/compare/v0.18.10...v0.18.11
.. _v0.18.10: https://github.com/miurahr/py7zr/compare/v0.18.9...v0.18.10
.. _v0.18.9: https://github.com/miurahr/py7zr/compare/v0.18.7...v0.18.9
.. _v0.18.7: https://github.com/miurahr/py7zr/compare/v0.18.6...v0.18.7
.. _v0.18.6: https://github.com/miurahr/py7zr/compare/v0.18.5...v0.18.6
.. _v0.18.5: https://github.com/miurahr/py7zr/compare/v0.18.4...v0.18.5
.. _v0.18.4: https://github.com/miurahr/py7zr/compare/v0.18.3...v0.18.4
.. _v0.18.3: https://github.com/miurahr/py7zr/compare/v0.18.1...v0.18.3
.. _v0.18.1: https://github.com/miurahr/py7zr/compare/v0.18.0...v0.18.1
.. _v0.18.0: https://github.com/miurahr/py7zr/compare/v0.17.4...v0.18.0
.. _v0.17.4: https://github.com/miurahr/py7zr/compare/v0.17.3...v0.17.4
.. _v0.17.3: https://github.com/miurahr/py7zr/compare/v0.17.2...v0.17.3
.. _v0.17.2: https://github.com/miurahr/py7zr/compare/v0.17.1...v0.17.2
.. _v0.17.1: https://github.com/miurahr/py7zr/compare/v0.17.0...v0.17.1
.. _v0.17.0: https://github.com/miurahr/py7zr/compare/v0.16.4...v0.17.0
.. _v0.16.4: https://github.com/miurahr/py7zr/compare/v0.16.3...v0.16.4
.. _v0.16.3: https://github.com/miurahr/py7zr/compare/v0.16.2...v0.16.3
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
