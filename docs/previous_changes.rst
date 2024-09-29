:tocdepth: 1

.. _previous_changes:

================
Previous changes
================

`v0.21.0`_
==========
Changed
-------
* Speed up extraction when number of files is very large (#555)
* Replace deprecated functions on python 3.12 (#550)

Added
-----
* Add report_update() for logging large files extraction (#558)

Document
--------
* Add subsection of multi-volume creation (#568)

`v0.20.8`_
==========
Fixed
-----
* Detect brotli import error (#543)

Changed
-------
* refactor: hardening SevenZipFile constructor (#547)
* refactor: improve type safe functions (#545)
* chore: add git export configuration (#544)

`v0.20.7`_
==========
Changed
-------
* Support Python 3.12 (#541)

`v0.20.6`_
==========

Fixed
-----
* fix: sanitize path when write (#525)
* fix: allow specify target path in relative path (#530)
* Avoid AttributeError on OpenBSD (#521)
* Error appending file: KeyError: 'lastwritetime' (#517)

Document
--------
* Fixing a string quote in user_guide document(#524)

`v0.20.5`_
==========

Fixed
-----
* Remove root reference from file names (#513)

Document
--------
* fix typo in the readme (#510)

`v0.20.4`_
==========

Fixed
-----
* Installation error in Cygwin (#504)


`v0.20.3`_
==========

Fixed
-----

* Drop manual GC to improve performance when many files are handled. (#489, #490)
* CI: fix test configurations (#494)
  - Fix mypy error
  - Skip deflate64 compression/decompression test on pypy
  - There is an issue in dependency inflate64 library that causes SIGABORT and SIGSEGV on pypy

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
* Check against directory traversal attack by file paths in archive (#406,#407)

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

* Drop issue_218.7z test data which is reported a blackmoon trojan(#285)

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


`v0.8.0`_
=========

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
* Refactoring compression algorithm related modules.

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


`v0.7.3`_
=========

Added
-----

* Support for encrypted header (#139, #140)

Changed
-------

* Fix CRC32 check and introduce test and testzip methods (#138)

Fixed
-----

* Allow decryption of data which is encrypted without any compression.(#140)

`v0.7.2`_
=========

Added
-----

* CLI: '-v {size}[b|k|m|g]' multi volume creation option.

`v0.7.1`_
=========

Changed
-------

* Decryption: performance improvement.
  Introduce helpers.calculate_key3(), which utilize list comprehension expression, bytes generation
  with join(). It reduces a number of calls of hash library and improve decryption performance.

Fixed
-----

* Fix overwrite behavior of symbolic link which may break linked contents.

`v0.7.0`_
=========

Added
-----

* Support dereference option of SevenZipFile class. (#131)
  If dereference is False, add symbolic and hard links to the archive.
  If it is True, add the content of the target files to the archive.
  This has no effect on systems that do not support symbolic links.
* Introduce progress callback mechanism (#130)
* Support memory API.(#111, #119)
  Introduce read(filter) and readall() method for SevenZipFile class.
* Support ZStandard codec compression algorithm for extraction.(#124, #125)

Changed
-------

* Extraction: Unlink output file if exist when it become a symbolic link.
  When overwrite extracted files and there are symlinks, it may cause an unexpected result.
  Unlinking it may help it.
* CLI: add --verbose option for extraction
* win32: update win32compat
* Drop pywin32 dependency(#120)
* Introduce internal win32compat.py
* Archive: Looking for symbolic link object in the archived list,
  and if found, record as relative link.(#112, #113, #122)

Fixed
-----

* Fix archiveinfo() for 7zAES archives
* Release variables when close() (#129)
* Support extraction of file onto a place where path length is > 260 bytes on Windows 10, Windows Server 2016R2
  and later. (Windows Vista, 7 and Windows Server 2012 still have a limitation of path length as a OS spec)(#116, #126)

Removed
-------

* Revmoed requirements.txt. When you want to install dependencies for development
  you can do it with 'pip install -e path/to/py7zr_project'


`v0.6`_
=======

Added
-----

* Test: SevenZipFile.archiveinfo() for various archives.
* Test: extraction of LZMA+BCJ archive become fails as marked known issue.
* Support deflate decompression method.
* Introduce context manager for SevenZipFile (#95)
* Test: add benchmarking test.
* Add concurrent extraction test.
* Add remote data test for general application test.
* Add class for multi volume header.
* Add readlink helper function for windows.
* Test: download and extract test case as a show case.
* setup.cfg: add entry-point configuration.
* Support filtering  a target of  extracted files from archive (#64)
* Support decryption (#55)
* Add release note automation workflow with Github actions.
* COPY decompression method.(#61)

Changed
-------

* Update documents and README about supported algorithms.
* Re-enable coverage report.
* Refactoring SevenZipFile._write_archive() method to move
  core chunk into compression module Worker.archive() method.
* Update calculate_key helper to improve performance.
* Introduce zero-copy buffer helper.
* Change decompressor class interface
    - change max_length type to int and default to -1.
* Update decryption function to improve performance.
* SevenZipFile(file-object, 'r') now can run extract() well even unlink before extract().
* Concurrency strategy: change to threading instead of multiprocessing. (#92)
* Release process is done by Github Actions
* Temporary disable to measure coverage, which is not working with threading.
* Tox: now pass PYTEST_ADDOPTS environment variable.
* extract: decompression is done as another process in default.
* extract: default multiprocessing mode is spawn
* extract: single process mode for password protected archive.
* Use spawn multiprocessing mode for all platforms.
* Use self context for multiprocessing.
* Concurrency implementation changes to use multiprocessing.Process() instead of
  concurrency.futures to avoid freeze or deadlock with application usage of it.(#70)
* Stop checking coverage because coverage.py > 5.0.0 produce error when multiprocessing.Process() usage.
* Drop handlers, NullHandler, BufferHandler, and FileHandler.

Fixed
-----

* Fix SevenZipFIle.archiveinfo() crash for LZMA+BCJ archive.(#100)
* Fix SevenZipFile.test() method defeated from v0.6b2 (#103)
* Fix SevenZipFile.solid() method to return proper value. (#72,#97)
* Fix README example for extraction option.
* Some of decryption of encrypted archive fails.(#75)
* Make pywin32 a regular runtime dependency
* Build with pep517 utility.
* Fix race condition for changing current working directory of caller, which cause failures in multithreading.(#80,#82)
* extract: catch UnsupportedMethod exception properly when multiprocessing.
* Fixed extraction of 7zip file with BZip2 algorithm.(#66)
* Fix symbolic link extraction with relative path target directory.(#67)
* Fix retrieving Folder header information logics for codecs.(#62)

Security
--------

* CLI: Use 'getpass' standard library to input password.(#59)

Removed
-------

* Static py7zr binary. Now it is generated by python installer.
* Test symlink on windows.(#60)


`v0.5`_
=======

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

Changed
-------

* Update documents.

Fixed
-----

* Fix extraction of archive which has zero size files and directories(#54).
* Revert zero size file logic(#47).
* Revert zero size file logic which break extraction by 7zip.
* Support for making archive with zero size files(#47).
* Produced broken archive when target has many directorires(#48).
* Reduce test warnings, fix annotations.
* Fix coverage error on test.
* Support for making archive with symbolic links.
* Fix write logics (#42)
* Fix read FilesInfo block.
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
  - PyPy issue: `PyPy3-3088`_
* Drop padding logic introduced in v0.3.5 that may be caused by python core bug,
  when max_length > io.DEFAULT_BUFFER_SIZE.
  - PyPy Issue: `PyPy3-3090`_
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

.. _`PyPy3-3088`: https://github.com/pypy/pypy/issues/3088
.. _`PyPy3-3090`: https://github.com/pypy/pypy/issues/3090


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

* Add test for zerofile with multi-folder archive.

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
.. _v0.21.1: https://github.com/miurahr/py7zr/compare/v0.21.0...v0.21.1
.. _v0.21.0: https://github.com/miurahr/py7zr/compare/v0.20.8...v0.21.0
.. _v0.20.8: https://github.com/miurahr/py7zr/compare/v0.20.7...v0.20.8
.. _v0.20.7: https://github.com/miurahr/py7zr/compare/v0.20.6...v0.20.7
.. _v0.20.6: https://github.com/miurahr/py7zr/compare/v0.20.5...v0.20.6
.. _v0.20.5: https://github.com/miurahr/py7zr/compare/v0.20.4...v0.20.5
.. _v0.20.4: https://github.com/miurahr/py7zr/compare/v0.20.3...v0.20.4
.. _v0.20.3: https://github.com/miurahr/py7zr/compare/v0.20.2...v0.20.3
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
.. _v0.10.1: https://github.com/miurahr/py7zr/compare/v0.10.0...v0.10.1
.. _v0.10.0: https://github.com/miurahr/py7zr/compare/v0.9.2...v0.10.0
.. _v0.9.2: https://github.com/miurahr/py7zr/compare/v0.9.1...v0.9.2
.. _v0.9.1: https://github.com/miurahr/py7zr/compare/v0.9.0...v0.9.1
.. _v0.9.0: https://github.com/miurahr/py7zr/compare/v0.8.0...v0.9.0
.. _v0.8.0: https://github.com/miurahr/py7zr/compare/v0.7.3...v0.8.0
.. _v0.7.3: https://github.com/miurahr/py7zr/compare/v0.7.2...v0.7.3
.. _v0.7.2: https://github.com/miurahr/py7zr/compare/v0.7.1...v0.7.2
.. _v0.7.1: https://github.com/miurahr/py7zr/compare/v0.7.0...v0.7.1
.. _v0.7.0: https://github.com/miurahr/py7zr/compare/v0.6...v0.7.0
.. _v0.6: https://github.com/miurahr/py7zr/compare/v0.5...v0.6
.. _v0.5: https://github.com/miurahr/py7zr/compare/v0.4...v0.5
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
