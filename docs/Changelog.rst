.. _changelog:

===============
Py7zr Changelog
===============

All notable changes to this project will be documented in this file.

`Unreleased`_
=============

Changed
-------
- Switch the 7zAES crypto dependency from ``pycryptodomex`` (``Cryptodome``
  namespace) to ``pycryptodome`` (``Crypto`` namespace). Upstream stopped
  regular releases of ``pycryptodomex`` at 3.x with pycryptodome 4.0, and
  it lacks wheels for PyPy 3.11 on Windows.

`v1.1.4`_
=========

Security
--------
- Fix arbitrary file write above the extraction directory via a symlink
  chain (incomplete fix of CVE-2026-23879, GHSA-jwx8-hv8g-gjjq).
  - ``canonical_path()`` cancelled ``..`` lexically before any symlink was
    resolved, so ``link/..`` was treated as the directory holding ``link``
    instead of the parent of its target. A chain of symlink members
    extracted from the same archive could therefore redirect a later write
    an archive-chosen number of levels above the extraction directory,
    while the member name still reduced to something apparently inside it.
  - Containment is now decided on the real path: symlink components are
    followed first and ``..`` is normalized only afterwards. This also
    covers symlink targets, which may legitimately contain ``..`` and so
    cannot be rejected by name.
  - Archive member names containing a ``..`` component are now rejected
    outright.
- Fix memory exhaustion when opening a crafted archive header (GHSA-6pr6-cqpq-x889).
- Fix extraction hang on a crafted COPY stream (GHSA-v999-q5cj-95jg).

Users are encouraged to upgrade. Details will be published in the
corresponding security advisories.

Fixed
-----

* Raise ``PasswordRequired`` when an archive is opened in write or append
  mode with a crypto filter (e.g. ``FILTER_CRYPTO_AES256_SHA256``) but no
  password, instead of failing later with an ``AttributeError``. The check
  also covers direct use of ``SevenZipCompressor``. (#723, #739)
* Limit concurrent extraction workers for non-solid archives to
  ``os.cpu_count()``, instead of starting one thread or process per
  folder. When the limit is reached, the oldest task is joined before a
  new one starts. (#630, #740)
* Fix ``AttributeError`` in ``archiveinfo()`` for archives with no
  compressed content, such as an empty archive or one containing only
  empty files or directories. ``_get_method_names()``, ``_is_solid()``
  and ``archiveinfo()`` now handle ``header.main_streams`` being
  ``None``. (#665, #741)
* Fix intermittent false negatives in the relative-path check on Windows.
  ``Path.resolve()`` may or may not return the extended-length prefix
  (``\\?\``), and when only one of the compared paths had it, the
  ``relative_to`` check always failed. The prefix is now stripped before
  comparison. (#714, #743)
* Fix ``io.UnsupportedOperation`` in ``extract()`` and ``extractall()``
  when a ``WriterFactory`` returns a non-seekable handle, such as one
  from ``zipfile.ZipFile.open``. The unnecessary ``seek(0)`` after
  decompression is removed, and ``MemIO.close()`` now rewinds only
  seekable handles, so behaviour with seekable destinations such as
  ``BytesIOFactory`` is unchanged. (#703, #744)
* Raise ``Bad7zFile`` instead of ``struct.error`` when a header is
  truncated in the middle of an integer field. ``read_real_uint64()``
  and ``read_uint32()`` now check the length of the data read before
  unpacking it. (#749)
* Honor ``dry_run`` in ``pack_7zarchive()``. When registered with
  ``shutil.register_archive_format()``, ``shutil.make_archive(...,
  dry_run=True)`` now returns the target filename without writing the
  archive, consistent with the standard library's zip and tar
  archivers. (#413, #750)
* Fix ``CrcError`` during extraction when available memory drops below
  256 MiB, for example under many parallel extractions. The buffer size
  calculated from available memory could become negative; it now has a
  minimum of 1 MiB. (#751, #629)

Changed
-------

* CI: Bump ``libarchive`` to 3.8.8.

`v1.1.3`_
=========

Security
--------

- CVE-2026-23879: Arbitrary File Write Vulnerability in py7zr (high severity)
    - Harden check of path traversal and enhance test cases to reproduce many attack scenarios.
- CVE-2026-55206: O(n^2) algorithmic complexity DoS in PackInfo._read() in py7zr
    - Enforced variation of the parameter with a limit and optimized calculation algorithm to prevent excessive CPU consumption.
- CVE-2026-55195: py7zr <= 1.1.2: Decompression bomb (zip bomb) denial of service via unchecked extraction size
    - Added check of extraction size and introduced `max_extract_size` as constructor parameter to guard against excessive decompression.

Notes:
- Fixed three security vulnerabilities in the py7zr library.
- Improvements made include path traversal hardening, optimization of CPU-intensive algorithms, and protection against zip bombs.

Fixed
-----
- BufferError when calling Py7zBytesIO.size() (#736,#737)
- fix: extractall() raises TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType' (#734,#735)

Changed
-------
- feat(io): add Py7zIO.close() lifecycle hook called once per extracted file (#699,#732)
- test: Bump dependency libarchive@3.8.7
- ci: bump numerous actions with SHA256 hash and newer versions (#729,#730)

`v1.1.2`_
=========

Security
--------
- security: fix Zip-Slip vulnerability by symlink

Removed
-------
- Remove Code of Conduct from repository.

Changed
-------
- remove unused _lzma imports

`v1.1.1`_
=========

Fixed
-----
- fix: default unix file attributes with proper permissions (#705)

Changed
-------
- test: Bump dependency libarchive@3.8.5

`v1.1.0`_
=========

- Same as v1.1.0rc4

v1.1.0rc4
=========

Changed
-------
- CI: Ensure nearest tag is fetched in `publish-to-pypi` workflow
- Streamlined pypi source package by pruning docs, tests and utils

v1.1.0rc2
=========

Changed
-------
- CI: update workflows (#695,#696,#697,#698,#692)
- Update tox configuration with TOML native (#689)
- Type hint syntax for Python 3.10 and later (#690)

Document
--------
- README: Minimum & Recommended Python/PyPY versions (#700)

v1.1.0rc1
=========

Security
--------
- Bump Brotli@1.2.0 and limit output memory size (#686)

Added
-----
- Support Python 3.14

Changed
-------
- CI: update target Python versions, GitHub Actions configurations
- dependency: pyppmd@1.3.0, pybcj@1.0.6, inflate64@1.0.4
- use stdlib for Zstandard support instead of pyzstd (#682)
- fix(is_7zfile): accept any path-like instead of just pathlib.Path (#663)
- Accept IO[bytes] instead of BinaryIO (#661)
- Document: Fix WriterFactory example (#660)
- getInfo() returns FileInfo object (#676)
- make FileInfo and ArchiveInfo dataclasses (#678)

Removed
-------
- Drop support for Python 3.9 (#691)

`v1.0.0`_
=========

- Celebrating the official 1.0.0 release!

Changed
-------
- CI: check on Linux on ARM64 with GitHub hosted ARM64 runner.
- Improve issue report template
- Remove Travis-CI button from Documentation

`v1.0.0rc3`_
============

Fixed
-----
- Adjust MANIFEST.in
- Fix installation on python 3.13 by allowing pyppmd 1.2.0

Changed
-------
- CI: update aarch64 tests on Ubuntu 24.04

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
.. _Unreleased: https://github.com/miurahr/py7zr/compare/v1.1.4...HEAD
.. _v1.1.4: https://github.com/miurahr/py7zr/compare/v1.1.3..v1.1.4
.. _v1.1.3: https://github.com/miurahr/py7zr/compare/v1.1.2..v1.1.3
.. _v1.1.2: https://github.com/miurahr/py7zr/compare/v1.1.1..v1.1.2
.. _v1.1.1: https://github.com/miurahr/py7zr/compare/v1.1.0..v1.1.1
.. _v1.1.0: https://github.com/miurahr/py7zr/compare/v1.0.0..v1.1.0
.. _v1.0.0: https://github.com/miurahr/py7zr/compare/v1.0.0-rc3...v1.0.0
.. _v1.0.0rc3: https://github.com/miurahr/py7zr/compare/v1.0.0-rc2...v1.0.0rc3
.. _v1.0.0rc2: https://github.com/miurahr/py7zr/compare/v1.0.0-rc1...v1.0.0rc2
.. _v1.0.0-rc1: https://github.com/miurahr/py7zr/compare/v0.22.0...v1.0.0-rc1
.. _v0.22.0: https://github.com/miurahr/py7zr/compare/v0.21.1...v0.22.0
.. _v0.21.1: https://github.com/miurahr/py7zr/compare/v0.21.0...v0.21.1
