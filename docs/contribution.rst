.. _contributor_guide:

:tocdepth: 2

*****************
Contributor guide
*****************

Development environment
=======================

If you’re reading this, you’re probably interested in contributing to py7zr.
Thank you very much! The purpose of this guide is to get you to the point
where you can make improvements to the py7zr and share them with the rest of the team.

Setup Python
------------

The py7zr is written in the Python programming language. Python installation for
various platforms with various ways. You need to install Python environment which
support `pip` command. Venv/Virtualenv is recommended for development.

We have a test suite with python 3.10, 3.11, 3.12, 3.13, 3.14, 3.14t, 3.15-dev and pypy3.11.
If you want to run all the test with these versions and variant on your local,
you should install these versions. You can run test with CI environment on
Github actions.


Get Early Feedback
------------------

If you are contributing, do not feel the need to sit on your contribution
until it is perfectly polished and complete. It helps everyone involved
for you to seek feedback as early as you possibly can.
Submitting an early, unfinished version of your contribution
for feedback in no way prejudices your chances of getting that contribution accepted,
and can save you from putting a lot of work into a contribution that is not suitable for the project.


Code Contributions
==================

Steps submitting code
---------------------

When contributing code, you’ll want to follow this checklist:

1. Fork the repository on GitHub.

2. Run the tox tests to confirm they all pass on your system. If they don’t, you’ll need
   to investigate why they fail. If you’re unable to diagnose this yourself,
   raise it as a bug report.

3. Write tests that demonstrate your bug or feature. Ensure that they fail.

4. Make your change.

5. Run the entire test suite again using tox, confirming that all tests pass
   including the ones you just added.

6. Send a GitHub Pull Request to the main repository’s master branch.
   GitHub Pull Requests are the expected method of code collaboration on this project.

Code review
-----------

Contribution will not be merged until they have been code reviewed. There are limited
reviewer in the team, reviews from other contributors are also welcome.
You should implemented a review feedback unless you strongly object to it.


Code style
----------

The py7zr uses the PEP8 code style. In addition to the standard PEP8, we have an extended
guidelines

* line length should not exceed 125 characters.

* It also use MyPy static type check enforcement.


Security tests
==============

Every vulnerability fix should come with a regression test that fails before the fix
and passes after it. Mark it with ``@pytest.mark.security``, which is registered in
``pyproject.toml`` as "mark a test as a vulnerability regression test"::

    pytest -m security

The marker is the only thing that reliably identifies a security test. CI runs the whole
suite with no marker selection, so the marker is for humans and for ad-hoc runs, not for
gating. Choosing the right file therefore does not affect whether a test runs -- it
affects whether the next person can find it.

Where to put a security test
----------------------------

Security tests are split by **threat model**, one file per attacker goal:

``tests/test_badfiles.py``
    Hostile archive *content* that escapes the extraction directory: path traversal,
    zip-slip, symlink ladders, Windows device names and drive letters. These mostly
    drive ``SevenZipFile.extractall()`` against a temporary directory and assert that
    nothing is written outside it.

``tests/test_badheaders.py``
    Hostile archive *header metadata* that attacks the parser itself: unbacked counts
    that drive huge allocations, truncated fields, and decode loops that never
    terminate. These run entirely in memory and assert ``Bad7zFile``.

The distinction is what the attacker is trying to achieve, not which function is called.
If a new class of attack fits neither file, add a third file rather than stretching one
of these.

Why split by threat model
-------------------------

Two other groupings were considered and rejected:

*Split by test level* -- parser-internal tests next to the other unit tests in
``tests/test_unit.py``, whole-archive tests in a separate file. Rejected because
``tests/test_badfiles.py`` already contains both levels: ``test_check_archive_path``
calls a helper predicate directly, while ``test_extract_path_traversal_attack`` goes
through the public API. Test level is not the line the suite already draws, and
following it would scatter a single advisory's tests across two files.

*One file for everything marked* ``security`` -- rejected because extraction escapes and
parser exhaustion share nothing but the marker. They have different fixtures, different
assertions and different reviewers' interests, and merging them produces a long file
with no internal logic. The marker already provides the cross-cutting view
(``pytest -m security``), so the files are free to be organised by subject, which is how
the rest of the suite is organised.

How the tests are written
-------------------------

Fixtures are built **in memory from raw bytes**, not committed as binary ``.7z`` files.
A malformed archive is usually a few dozen bytes, and a literal byte string documents
precisely which field is hostile in a way an opaque binary fixture cannot. It also keeps
a deliberately malicious file out of the source tree, where virus scanners and
downstream packagers may object to it.

``tests/test_badheaders.py`` tests each fix at two levels, and both matter:

* **Parser level** -- a hand-built ``io.BytesIO`` passed straight to an
  ``py7zr.archiveinfo`` class, for example
  ``FilesInfo.retrieve(io.BytesIO(HUGE_UINT64 + b"\x00"))``. This pins the exact
  structure that is rejected, with no surrounding archive to obscure it.

* **Whole file level** -- a complete archive through ``SevenZipFile(...)``, built with
  the module's ``_craft_archive()`` helper, which fixes up the signature header CRC so
  the parser actually reaches the code under test. This proves the guard is reachable by
  a real attacker; a parser-level test alone does not.

Two helpers in that module are worth reusing: ``HUGE_UINT64`` is the nine-byte encoding
of ``2**64-1``, the cheapest way to request an enormous allocation, and
``_craft_archive(nextheader, packed)`` wraps a crafted next header in a valid signature
header. Promote either to ``tests/__init__.py`` if a second file needs it, alongside the
existing shared helpers there.

A test for a non-terminating loop should carry ``@pytest.mark.timeout(60)``. The timeout
*is* the assertion -- without the fix the test never returns.

Confirming the test fails first
-------------------------------

Step 3 of the checklist above applies with one practical caveat. An allocation bomb run
against unpatched code may consume all available memory before it fails, so cap the
address space when checking that the test is meaningful::

    (ulimit -v 2000000; pytest tests/test_badheaders.py -m security)

Unpatched, the test should fail with ``MemoryError`` or time out; patched, it passes with
``Bad7zFile``. A security test that passes against unpatched code is testing nothing.


Profiling
=========

CPU and memory profiling
------------------------

Run-time memory errors and leaks are among the most difficult
errors to locate and the most important to correct.
Memory profiling is used to detect memory leaks or unwanted memory usages.

It is also a difficult work to improve performance. CPU profiling
help us to understand where is a hot spot of execution of a program.

mprofile
--------

mprofile is a tool to do a memory profiling task for python.
py7zr project has a test configuration for the memory profiling.

.. code-block::

   env PYTEST_ADDOPTS=--run-slow tox -e mprof

This example run all the test cases includes conditions
which requires running duration.

After running test, you can find a chart in project root.
`memory-profiile.png` and raw data as `mprofile_yyyyMMddhhmmss.dat`


Class and module design
=======================

The py7zr take class design that categorized into several sub modules
to reflect its role.

The main class is py7zr.SevenZipFile() class which provide API
for library users. The main internal classes are in the submodule
py7zr.archiveinfo, which takes class structure as same as .7z file
format structure.

Another important submodule is py7zr.compressor module that hold
all related compression and encryption proxy classes for corresponding
libraries to convert various interfaces into common ISevenZipCompressor()
and ISevenZipDecompressor() interface.

All UI related classes and functions are separated from core modules.
cli submodule is a place for command line functions and pretty printings.


.. graphviz:: diagrams/packages.dot

Here is a whole classes diagram. There are part by part descriptions at Next sections.

.. graphviz:: diagrams/classes.dot


Header classes
--------------

Header related classes are in py7zr.archiveinfo submodule.

.. graphviz:: diagrams/header_classes.dot


Compressor classes
------------------

There are compression related classes in py7zr.compressor submodule.

.. graphviz:: diagrams/compressor_classes.dot


IO Abstraction classes
----------------------

There are two IO abstraction classes to provide Mem API and check method.

.. graphviz:: diagrams/abstractio.dot


Callback classes
----------------

Here is a callback interface class. ExtractCallback class is a concrete class used in CLI.

.. graphviz:: diagrams/callbacks.dot


.. _internal_classes:

Classes details
================

Here is a detailed interface documentation for implementer.

ArchiveFile Objects
-------------------

.. automodule:: py7zr.py7zr
   :members:


archiveinfo module
------------------

.. automodule:: py7zr.archiveinfo
   :members:


compressor module
------------------

.. automodule:: py7zr.compressor
   :members:


helpers module
--------------

.. automodule:: py7zr.helpers
   :members:
