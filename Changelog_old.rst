====================
Py7zr ChangeLog(old)
====================

All notable changes to this project before v0.8.0 was documented in this file.

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
    - change max_length type to int and defualt to -1.
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
* Drop handlers, NullHandler, BufferHnalder, and FileHander.

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
