.. _changelog:

===============
Py7zr Changelog
===============

All notable changes to this project will be documented in this file.

`Unreleased`_
=============

`v1.0.0rc2`_
============

There is big incompatible change after -rc1 version.

Removed
-------
* Remove SevenZipFile.read() and SevenZipFile.readall() (#620)
  This confuse users to use as same as ZipFile method, but not the same.
  Using this method can easily exhaust a machine memory.

Added
-----
* Add ``factory`` parameter that takes ``WriterFactory`` object which provides
  an object that implements ``Py7zIO`` interface. (#620)
  This allow user to interact with Py7zr for large archives. (#620)

Deprecated
----------
* deprecation for ``writed`` method

Changed
-------
* Minimum required Python version to be Python 3.9 (#619)
* Support Python 3.13 (#619)
    - Remove code paths that checked for python versions less than 3.9
* Update CI/GitHub Actions(#619)
    - Drops 3.8 and adds 3.13 to the test matrix
    - Update all the GitHub actions to their latest versions
    - Upgrade aarch64 from ubuntu20.04+py39 to ubuntu22.04+py310.
* Replace old style strings with f-strings(#619)
* Replace typing.List (and similar) with their standard equivalent(#619)

`v1.0.0-rc1`_
=============

Changed
-------
* Bump dependencies versions
    - pycryptodomex@3.32.0
    - pyzstd@0.16.1
    - sphinx@7.0.0
    - mypy@1.10.0
    - mypy_extensions@1.0.0
    - isort@5.13.2
    - black@24.8.0

`v0.22.0`_
==========

Added
-----
* Add mode "x" for SevenZipFile (#588)
* Add SevenZipFile#namelist method (#600)

Fixed
-----
* Append mode on non-existent files (#604)
* Fix NUMBER encoding of integer when 8 bytes(#591)

Changed
-------
* Minimum required Python version to be Python 3.8 (#601)
* Remove pyannotate from pyproject.toml (#598)

Document
--------
* Update user guide (#596)

`v0.21.1`_
==========
Fixed
-----
* Follow shutil.register_unpack_format() convention of raising a ReadError
  when the library cannot handle a file (#583)
* ensure unpack_7zarchive closes the archive (#584)
* 64bit OS detection (#580)

Added
-----
* Add recursive sub-directories and files extraction (#585)

Changed
-------
* check targets argument type for read and extract method (#577)
* Treat zero byte stream as a file (#551)


.. History links
.. _Unreleased: https://github.com/miurahr/py7zr/compare/v1.0.0rc2...HEAD
.. _v1.0.0rc2: https://github.com/miurahr/py7zr/compare/v1.0.0-rc1...v1.0.0rc2
.. _v1.0.0-rc1: https://github.com/miurahr/py7zr/compare/v0.22.0...v1.0.0-rc1
.. _v0.22.0: https://github.com/miurahr/py7zr/compare/v0.21.1...v0.22.0
.. _v0.21.1: https://github.com/miurahr/py7zr/compare/v0.21.0...v0.21.1
