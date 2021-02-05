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

`v0.12.0`_
==========

Changed
-------

* PPMd and ZStandard is now one of default algorithms(#269)
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

`v0.10.1`_
==========

Fixed
-----

*  Fix exception when reading header which size is larger than buffer size (#252)


`v0.10.0`_
==========

Added
-----

* Compatibility test with python-libarchive-c/libarchive for compression(#247)
* Document: express how to handle multi-volume archive (#243)
* SevenZipFile.needs_password() method.(#208, #235)
* CLI: Support append mode command line.(#228)
* Support "APPEND" mode. User can open SevenZipFile() class with mode='a' (#227)

Changed
-------

* Calculate CRC32 of header without re-reading header from disk again.(#245)
* read(), extract(): improve performance when specifying parts of archived file,
  by skipping rest of arcvhive when target file has extracted.(#239,#242)
* read(), extract(): improve performance when specifying parts of archived file,
  by not running threads for unused compression blocks(folders).(#239,#242)
* docs: improve API documentation.(#244)
* setup: set minimum required python version as >=3.5
* Compression will be happened when call write() not close() (#222, #226)
* Handle file read/write in SevenZipCompressor/Decompressor class (#213)

Fixed
-----

* Fix BCJ(x86) filter code with a missing logic which cause extraction error
  for certain data. (#249, #250)
* Raise PasswordRequired when encrypted header without passing password (#234, #237)
* CLI: don't raise exception when password is wrong or not given.(#229)
* Fix specification typo.
* Catch exception in threading extraction(#218,#219)

`v0.9.2`_
=========

Changed
-------

* Utilize max_length argument for each decompressor.(#210, #211)
* Change READ_BUFFER_SIZE 32768 for python 3.7.5 and before.
* Extend Buffer size when necessary.(#209)


`v0.9.1`_
=========

Changed
-------

* Improve DecompressionChain.decompress() logics.(#207)

Fixed
-----

* Fix BCJ filter for decompression that can cause infinite loop or wrong output.(#204,#205,#206)

`v0.9.0`_
=========

Added
-----

* BCJ Decoder/Encoder written by python.(#198, #199)
* Support Bzip2, Defalte + BCJ(X86, PPC, ARM, ARMT, SPARC) (#199)
* Add Copy method as an extraction only support.(#184)

Changed
-------

* Use large(1MB) read blocksize for Python 3.7.5 and later and PyPy 7.2.0 and later.
* Set ZStandard compression as unsupported because of a bug with unknown reason.(#198)
* Manage compression methods to handle whether decompressor requires coder['property'] or not.

Fixed
-----

* Significantly improve decompress performance which is as same speed as v0.7.*.
  by updating buffer handling.
* Fix decompression max_size to pass lzma module. Now it is as same as out_remaining.
* Support LZMA+BCJ(X86, PPC, ARM, ARMT, SPARC) with alternative BCJ filter.(#198, #199)
* Fix packinfo crc  read and write (#187, #189)
* Accept archive which Method ID is NULL(size=0)(#181, #182)
* CLI: Does not crash when trying extract archive which use unsupported method(#183)


v0.8.0
======

Added
-----

* test: add test for #178 bug report the case of LZMA+BCJ as xfails.
* File format specification: add ISO/IEC standard style specification document.
* Support extra methods for archiveinfo() method.(#150)
* test: unit tests for Sparc, ARMT and IA64 filters.
* Support for PPC and ARM filters.
* Support encryption(#145)
* Export supported filter constants, such as FILTER_ZSTD(#145)

Changed
-------

* Improve README, documents and specifications.
* Update password handling and drop get_password() helper (#162)
* Enable encoded header and add more test with 7zip compatibility.(#164)
* Refactoring SevenZipFile class internals. (#160)
* Refactoring classes in compressor module. (#161)
* Add 'packinfo.crcs' field digests data when creating archive.(#157)
  It help checking archive integrity without extraction.
* CLI: help option to show py7zr version and python version.
* Use importlib for performance improvement instead of pkg_resources module.
* Documents: additional methods, filter examples.
* CI configurations: Manage coverage with Coveralls.
* Refactoring decompression classes to handle data precisely with folder.unpacksizes(#146)
* Default compression mode is LZMA2+BCJ which is as same as
  7zip and p7zip(#145)
* Enhance encryption strength, IV is now 16 bytes, and generated
  with cryptodom.random module.(#145)
* Refactoring compression algorythm related modules.

Fixed
-----

* Now return correct header size by archiveinfo() method.(#169)
* Disable adding CRC for encoded header packinfo.(#164)
* Fix password leak/overwrite among SevenZipFile objects in a process.(#159)
  This can cause decryption error or encryption with unintended password.
* Release password on close()
* SevenZipFile.test() method now working properly. (#155)
* Fix extraction error on python 3.5.(#151)
* Support combination of filters(#145)
* Compression of Delta, BZip2, ZStandard, and Deflate(#145)
* Fix archived head by multiple filter specified.
* Fix delta filter.
* Working with BCJ filter.
* Fix archiveinfo to provide proper names.

Removed
-------

* test: Drop some test case with large files.
* Drop ArchiveProperty class: A field has already deprecated or not used.(#170)
* Drop AntiFile property: a property has already deprecated or not used.
* remove final_header definition.



.. History links
.. _Unreleased: https://github.com/miurahr/py7zr/compare/v0.12.0...HEAD
.. _v0.12.0: https://github.com/miurahr/py7zr/compare/v0.11.3...v0.12.0
.. _v0.11.3: https://github.com/miurahr/py7zr/compare/v0.11.1...v0.11.3
.. _v0.11.1: https://github.com/miurahr/py7zr/compare/v0.11.0...v0.11.1
.. _v0.11.0: https://github.com/miurahr/py7zr/compare/v0.10.1...v0.11.0
.. _v0.10.1: https://github.com/miurahr/py7zr/compare/v0.10.0...v0.10.1
.. _v0.10.0: https://github.com/miurahr/py7zr/compare/v0.9.2...v0.10.0
.. _v0.9.2: https://github.com/miurahr/py7zr/compare/v0.9.1...v0.9.2
.. _v0.9.1: https://github.com/miurahr/py7zr/compare/v0.9.0...v0.9.1
.. _v0.9.0: https://github.com/miurahr/py7zr/compare/v0.8.0...v0.9.0
