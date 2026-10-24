Security Policy
===============

Supported Versions
------------------

+---------+---------------------+
| Version | Status              |
+=========+=====================+
| 1.1.x   | Stable version      |
+---------+---------------------+
| < 1.1.0 | not supported       |
+---------+---------------------+

Reporting a Vulnerability
-------------------------

Please disclose security vulnerabilities privately at miurahr@linux.com


Threat model
------------

py7zr parses an archive header in full when a ``SevenZipFile`` is opened, before the
caller has had any chance to inspect or accept the archive. Everything reached during
that parse runs on untrusted input, so the header parser in ``py7zr/archiveinfo.py`` is
treated as the primary attack surface.

Two classes of attack are in scope and are tested for:

Archive content escaping the destination
    A member name or symlink that resolves outside the directory passed to
    ``extractall()`` -- path traversal, zip-slip, symlink ladders, Windows device names
    and drive letters.

Archive metadata attacking the parser
    A header field that costs almost nothing to write but a great deal to process.
    Counts in a 7z header are variable-length integers up to ``2**64-1``, so nine bytes
    can declare an arbitrary number of files, folders, coders or streams. Any count used
    to size a list or drive a loop must be validated before it is used.

Out of scope: the decompressed *size* of archive members, which a caller bounds with the
``max_extract_size`` argument to ``SevenZipFile``; and archives the caller has already
chosen to trust.


Hardening in the header parser
------------------------------

Counts read from a header are checked before they are used to allocate, by
``check_count()`` in ``py7zr/archiveinfo.py``. Two bounds are applied:

* **Relative** -- a count may not exceed what the remaining input could possibly back.
  The header is fully read into memory before parsing, so the number of bytes left is
  known exactly. This adapts to the archive and does not impose a ceiling on
  legitimately large ones.

* **Absolute** -- a set of ``MAX_*`` constants caps counts whose entries cost far more
  memory to represent than the header bytes that declare them.

Both raise ``Bad7zFile``. The relative bound is counted in *bits* per entry, because a
bit vector legitimately spends one bit per entry; a byte-granular bound would reject
valid archives.


Security regression tests
-------------------------

Every fixed vulnerability has a regression test marked ``@pytest.mark.security``::

    pytest -m security

They live in ``tests/test_badfiles.py`` (content escaping the destination) and
``tests/test_badheaders.py`` (metadata attacking the parser), mirroring the two classes
above. See the "Security tests" section of the contributor guide for how they are
written and why they are organised that way.
