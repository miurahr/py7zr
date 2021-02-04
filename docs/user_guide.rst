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

.. option:: a <7z file> <base_dir>

   Append files from base_dir to existent 7zip archive.

.. option:: i <7z file>

   Show archive information of specified 7zip archive.

.. option:: t <7z file>

   Test whether the 7z file is valid or not.


Common command options
----------------------

.. option:: -P --password

   Extract, list or create password protected archive. py7zr will prompt user input.


.. option:: --verbose

   Show verbose debug log.


Create command options
----------------------

.. option:: -v | --volume {Size}[b|k|m|g]

   Create multi-volume archive with Size. Usable with 'c' sub-command.


Programming APIs
================

Extraction
----------

Here is a several example for extraction from your python program.
You can write it with very clean syntax because py7zr supports context maanager.

.. code-block:: python

    import py7zr
    with py7zr.SevenZipFile("Archive.7z", 'r') as archive:
        archive.wxtractall(path="/tmp")


This example extract a 7-zip archive file "Archive.7z" into "/tmp" target directory.


Make archive
------------

Here is a simple example to make 7-zip archive.

.. code-block:: python

    import py7zr
    with py7zr.SevenZipFile("Archive.7z", 'w') as archive:
        archive.writeall("target/")


Append files to archive
-----------------------

Here is a simple example to append some files into existent
7-zip archive.

.. code-block:: python

    import py7zr
    with py7zr.SevenZipFile("Archive.7z", 'a') as archive:
        archive.write("additional_file.txt")


Extraction from multi-volume archive
------------------------------------

You should concatenate multi-volume archives into single archive file before
call py7zr, or consider using files wrapping class that handle multiple files
as a virtual single file, (ex. multivolumefile library)


.. code-block:: python

    import py7zr
    filenames = ['example.7z.0001', 'example.7z.0002']
    with open('result.7z', 'ab') as outfile:  # append in binary mode
        for fname in filenames:
            with open(fname, 'rb') as infile:        # open in binary mode also
                outfile.write(infile.read())
    with py7zr.SevenZipFile("result.7z", "r") as archive:
        archive.extractall()
    os.unlink("result.7z)

Here is another example. This example use multivolumefile library.
The multivolumefile library is in pre-alpha status, so it is not recommend to use
production system.

.. code-block:: bash

    pip install py7zr multivolumefile


When there are files named, 'example.7z.0001', 'example.7z.0002', and so on,
following code will extract multi-volume archive.

.. code-block:: python

    import multivolumefile
    import py7zr
    with multivolumefile.open('example.7z', mode='rb') as target_archive:
        with SevenZipFile(target_archive, 'r') as archive:
            archive.extractall()


If you want to create multi volume archive using multivolumefile library,
following example do it for you.

.. code-block:: python

    import multivolumefile
    import py7zr

    target = pathlib.Path('/target/directory/')
    with multivolumefile.open('example.7z', mode='wb', volume_size=10240) as target_archive:
        with SevenZipFile(target_archive, 'w') as archive:
            archive.writeall(target, 'target')


Presentation material
=====================

See :download:`Introductory presentation(PDF) <presentations/Introduction_of_py7zr.pdf>`,
and :download:`Introductory presentation(ODP) <presentations/Introduction_of_py7zr.odp>`.
