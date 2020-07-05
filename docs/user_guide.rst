.. _user_guide:

**********
User Guide
**********

The 7z file format is a popular archive and compression format in recent days.
This module provides tools to read, write and list 7z file. Features is not implemented
to update and append a 7z file. py7zr does not support self-extracting archive,
aka. SFX file, and only support plain 7z archive file.


Getting started
===============

Install
-------

The py7zr is written by Python and can be downloaded from PyPI(aka. Python Package Index)
using standard 'pip' command as like follows;

.. code-block:: bash

    $ pip install py7zr


When you want to use an extension that support ZStandard, please use following command line.

.. code-block:: bash

    $ pip install py7zr[zstd]


Run Command
-----------

'py7zr' is a command script. You can run extracting a target file target.7z
then command line become as such as follows;

.. code-block:: bash

    $ py7zr x target.7z

When you want to create an archive from a files and directory under the current
directory 'd', command line become as such as follows;

.. code-block:: bash

    $ py7zr c target.7z  d/


.. _py7zr-commandline:
.. program:: py7zr


Command-Line Interfaces
=======================

The :mod:`py7zr` module provides a simple command-line interface to interact
with 7z archives.

If you want to extract a 7z archive into the specified directory, use
the :option:`x` subcommand:

.. code-block:: shell-session

    $ python -m py7zr x monty.7z target-dir/
    $ py7zr x monty.7z

For a list of the files in a 7z archive, use the :option:`l` subcommand:

.. code-block:: shell-session

    $ python -m py7zr l monty.7z
    $ py7zr l monty.7z


Command-line options
--------------------

.. option:: l <7z file>

   List files in a 7z file.

.. option:: x <7z file> [<output_dir>]

   Extract 7z file into target directory.

.. option:: c <7z file> <base_dir>

   Create 7zip archive from base_directory

.. option:: i <7z file>

   Show archive information of specified 7zip archive.

.. option:: t <7z file>

   Test whether the 7z file is valid or not.


Common command options
-------------------------

.. option:: -P --password

   Extract, list or create password protected archive. py7zr will prompt user input.


.. option:: --verbose

   Show verbose debug log.


Create command options
----------------------

.. option:: -v | --volume {Size}[b|k|m|g]

   Create multi-volume archive with Size. Usable with 'c' sub-command.


Presentation material
=====================

See :download:`Introductory presentation(PDF) <presentations/Introduction_of_py7zr.pdf>`,
and :download:`Introductory presentation(ODP) <presentations/Introduction_of_py7zr.odp>`.
