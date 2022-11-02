===============
Py7zr Changelog
===============

All notable changes to this project will be documented in this file.

`Unreleased`_
=============

`v0.20.2`_
==========

Fixed
-----

* Fix error with good path data, when detecting wrong path
  with new canonical_path(), and drop resolve() call on path.

`v0.20.1`_
==========

Security
--------

* Fix sanity check for path traversal attack(#480)
* Add path checker in writef() and writestr() methods that ignores evil pass.
  - When pass arcname as evil path such as "../../../../tmp/evil.sh"
  - it raises ValueError
* Check symlink and junction is under target folder when extraction

`v0.20.0`_
==========

Added
-----
* Support enhanced deflate compression.(#472)

Changed
-------
* Bump setuptools@63 and setuptools_scm@7 (#473)
* CI: update script (#473)
* Update tox config (#473)
* Actions: change pypy version to 3.7 (#473)
* Update readthedocs.yml (#473)

Deprecated
----------
* Deprecate Python 3.6 support (#473)


`v0.19.0`_
==========

Changed
-------

* Replace deflate64(tm) decompressor to inflate64(#459)
* test: improve checks of deflate64 case(#463)

`v0.18.10`_
===========

Fixed
-----

* Actions: fix release script to produce wheel.(#462)
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


.. History links
.. _Unreleased: https://github.com/miurahr/py7zr/compare/v0.20.2...HEAD
.. _v0.20.2: https://github.com/miurahr/py7zr/compare/v0.20.1...v0.20.2
.. _v0.20.1: https://github.com/miurahr/py7zr/compare/v0.20.0...v0.20.1
.. _v0.20.0: https://github.com/miurahr/py7zr/compare/v0.19.0...v0.20.0
.. _v0.19.0: https://github.com/miurahr/py7zr/compare/v0.18.10...v0.19.0
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
