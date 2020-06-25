=============================
.7z file format specification
=============================

Abstract
========

7-zip archive is one of popular files compression and archive formats. There has been
no well-defined file format specification document in 20 years from its birth, so
it is not considered application defined format.

There are some independent implementation of utility to handle 7-zip archives, it is necessary
to prepare a precise format specification documentation to keep compatibility and interoperability.

This specification defines an archive file format of 7-zip archive.
This specification is derived from 7zFormat.txt bundled with p7zip utility which is portable
7-zip implementation. Its details are retrieved from knowledge got by reverse engineering effort
of p7zip implementation.


Copyright Notice
================

Copyright (C) 2020 Hiroshi Miura


Introduction
================

Purpose
-----------

This specification is intended to define a cross-platform, interoperable file storage and
transfer format  The information here is meant to be a concise guide for those wishing
to implement libraries and utility to handle 7-zip archive files.

Intended audience
-----------------

This specification is intended for use by implementors of software to compress files into 7-zip format and/or
decompress files from 7-zip format.

The text of the specification assumes a basic background in programming
at the level of bits and other primitive data representations.

Scope
---------

"7-zip archive" is one of popular files compression and archive formats.
It is universally used to aggregate, compress, and encrypt files into a single
interoperable container. No specific use or application need is
defined by this format and no specific implementation guidance is
provided. This document provides details on the storage format for
creating 7-zip files.  Information is provided on the records and
fields that describe what a .7z file is.

Trademarks
----------

7-zip is a public-domain utility on Microsoft Windows platforms written by Igor Pavlov.
7-zip archive file format was originally produced and defined by 7-zip utility.
p7zip is a cross-platform utility to handle 7zip archive file, which is a port of 7-zip to posix.
py7zr is a library and utility written with pure python3 to handle 7zip archive,
that is distributed under GNU Lessaer General Public License version 2.1 and later.
xzutils is an file compression/decompression utility.
liblzma is a library to provide LZMA and LZMA2 compression algorithm provided by xzutils project.
Python is one of popular computer language and running platform copyrighted and licensed by Python Foundation.
Python 3 provide lzma API deppend on liblzma.


Motivation
==========

There are several file archive format and utilities.  Many of them are born as proprietary format
of archive utility software, because of its nature, only standardized formats are now alived
as portable, stable for long time and freely usable specification.
PKWare ZIP, GNU Tar and GZip are examples for it.
Since 7-zip, its format and algorithm LZMA/LZMA2 are born as public-domain in 1999,
it is known as one of long lived file format.

There are two effort to make 7zip as a well-documented and portable format.
One is a documentation project here, and other is a software development project
to be independent and compatible with original 7zip and p7zip utility such as py7zr.


Notations
=========

* Use of the term SHALL indicates a required element.

* MAY NOT or SHALL NOT indicates an element is prohibited from use.

* SHOULD indicates a RECOMMENDED element.

* SHOULD NOT indicates an element NOT RECOMMENDED for use.

* MAY indicates an OPTIONAL element.


Specification
=============

Conventions
-----------

Diagram conventions
^^^^^^^^^^^^^^^^^^^

In the diagrams below, a box like this:

::

    +---+
    |   | <-- the vertical bars might be missing
    +---+

represents one byte.

When specified with character with single quote, it means a constant
value of specified character.

An example bellow means a data '7' ie. 0x37  is placed as one byte.

::

    +---+
    |'7'|
    +---+


When two digit of hexadecimal alphabet and number(0-9A-F) is placed,
it means a constant of specified value.

An example bellow means a constant 0xFF is placed as one byte.

::

    +---+
    | FF|
    +---+

A box like this:

::

    +==============+
    |              |
    +==============+

represents a variable number of bytes.

When label is placed, it refers other field defined in this document.

::

    +=============================+
    | Signature Header            |
    +=============================+

When label is placed inside () bracket, it express the field is optional.

::

    +=============================+
    | (Packed Streams)            |
    +=============================+


When two or more labels are placed inside ( ) bracket separeted with bartical bar |,
it express the field is selectable.

::

    +=============================+
    | (A | B)                     |
    +=============================+

This example means a field is mandatory but it can be A or B.

When adding a block bracket [] at end of label, it means the field is a list of
values or repeatable.

::

    +=============================+
    | CRCs of packed stream[]     |
    +=============================+

When label is placed at a block bracket, it means a length of a list.

::

    +===========================================+
    | CRCs of packed stream[Num of folders]     |
    +===========================================+




Data Representations
====================

This chapter describes basic data representations used in 7-zip file.

Integers and byte order
-----------------------

All integers that require more than one byte SHALL be in a little endian,
Least significant byte (LSB) comes first, then more significant bytes in
ascending order of significance (LSB MSB for two byte integers, B0 B1 B2 B3
for four bytes integers). The highest bit (value 128) of byte is number bit 7
and lowest bit (value 1) is number bit 0. Values are unsigned unless otherwise
noted.


UINT32
^^^^^^

UINT32 SHALL be an integer value stored in 4 bytes at little endian,
representing a integer rage from 0 to 4,294,967,295 (0xffffffff).

::

      0   1   2   3
    +---+---+---+---+
    |               |
    +---+---+---+---+


REAL_UINT64
^^^^^^^^^^^

REAL_UINT64 SHALL be an integer value stored in 8 bytes at little endian,
representing a integer range from 0 to 18446744073709551615 (0xffffffffffffffff)
It may also known as unsigned long long.

::

      0   1   2   3   4   5   6   7
    +---+---+---+---+---+---+---+---+
    |                               |
    +---+---+---+---+---+---+---+---+



UINT64
^^^^^^

UINT64 SHALL be a integer value encoded with the following scheme.
It SHALL represent an integer from 0 to 18446744073709551615 (0xffffffffffffffff)
in byte length between one byte to nine bytes.

Size of encoding sequence SHALL indicated at first byte.
The rest bits of first byte represent a bits from MSB of value.
Following bytes SHOULD be an integer as little endian.

+-------------+--------------+------------------------------+
| |First_Byte | |Extra_Bytes | |Value                       |
| |(binary)   |              | |(y: little endian integer)  |
+=============+==============+==============================+
|0xxxxxxx     |              | (0b0xxxxxxx           )      |
+-------------+--------------+------------------------------+
|10xxxxxx     | BYTE y[1]    | (0b00xxxxxx << (8 * 1)) + y  |
+-------------+--------------+------------------------------+
|110xxxxx     | BYTE y[2]    | (0b000xxxxx << (8 * 2)) + y  |
+-------------+--------------+------------------------------+
|1110xxxx     | BYTE y[3]    | (0b0000xxxx << (8 * 3)) + y  |
+-------------+--------------+------------------------------+
|11110xxx     | BYTE y[4]    | (0b00000xxx << (8 * 4)) + y  |
+-------------+--------------+------------------------------+
|111110xx     | BYTE y[5]    | (0b000000xx << (8 * 5)) + y  |
+-------------+--------------+------------------------------+
|1111110x     | BYTE y[6]    | (0b0000000x << (8 * 6)) + y  |
+-------------+--------------+------------------------------+
|11111110     | BYTE y[7]    | y                            |
+-------------+--------------+------------------------------+
|11111111     | BYTE y[8]    | y                            |
+-------------+--------------+------------------------------+


.. _`7-zip archive`:
File format
===========

7-zip archive file format SHALL consist of three part.
7-zip archive file SHALL start with signature header.
The data block SHOULD placed after the signature header.
The data block is shown as Packed Streams.

A header database SHOULD be placed after the data block.
The data block MAY be empty when no archived contents exists.
So Packed Streams is optional.

Since Header database CAN be encoded then it SHOULD place
after data block, that is Packed Streams for Headers.
When Header database is encoded, Header encode Information
SHALL placed instead of Header.

When Header database is placed as plain form,
Packed Streams for Headers SHALL NOT exist.

::

    +======================================+
    | Signature Header                     |
    +======================================+
    | (Packed Streams)                     |
    +======================================+
    | (Packed Streams for Headers)         |
    +======================================+
    | (Header | Header encode Information) |
    +======================================+


.. _`SignatureHeader`:
Signature Header
----------------

Signature header SHALL consist in 32 bytes.
Signature header SHALL start with Signature then continues
with archive version. Start Header SHALL follow after archive version.

::

      0   1   2   3   4   5   6   7
    +---+---+---+---+---+---+---+---+
    | Signature             | Archive Version
    +---+---+---+---+---+---+---+---+
    | Start Header                  |
    +---+---+---+---+---+---+---+---+
    | Start Header (cont)           |
    +---+---+---+---+---+---+---+---+
    | Start Header (cont)           |
    +---+---+---+---+---+---+---+---+



Signature
---------

The first six bytes of a 7-zip file SHALL always contain the following values as Signature header:

::

      0    1    2   3   4   5
    +----+----+---+---+---+---+
    |'7' |'z' |BC |AF |27 |1C |
    +----+----+---+---+---+---+



Archive Version
---------------

Archive version SHALL consist with two bytes.

::

            0               1
    +---------------+---------------+
    | Major version | Minor version |
    +---------------+---------------+

Major version MAY be 0x00, and minor version MAY be 0x04.

_`StartHeader`
Start Header
------------

Start header SHALL be a metadata of header database.
Start header shall consist with Start header CRC, Next Header Offset, Next Header Size,
and Next Header CRC.

::

      0   1   2   3   4   5   6   7
    +---+---+---+---+---+---+---+---+
    | Start H. CRC  | N.H. offset   |
    +---+---+---+---+---+---+---+---+
    | offset(cont)  | N.H. size     |
    +---+---+---+---+---+---+---+---+
    | size(cont)    | N.H. crc      |
    +---+---+---+---+---+---+---+---+


_`StartHeaderCRC`
Start Header CRC
^^^^^^^^^^^^^^^^

Start header CRC SHALL be a CRC32 of `Start Header`_ It SHALL be stored in form of UINT32.
This CRC value SHALL be calculated from Next Header Offset, Next Header size and
Next Header CRC.


_`NextHeaderOffset`
Next Header offset
^^^^^^^^^^^^^^^^^^

Next header offset SHALL be an offset from end of signature header to header database.
Because signature header always consist with 32 bytes, the offset SHOULD be a value that
absolute position of header database in archive file - 32 bytes.
Next header offset SHALL be stored as REAL_UINT64.

_`NextHeaderOffset`
Next Header size
^^^^^^^^^^^^^^^^

Next header size SHALL be an size of a header database. Because a header database MAY be
encoded, Next header size SHALL consist of encoded(packed) size, not a raw size.
Next header size SHALL be stored as REAL_UINT64.

_`NextHeaderCRC`
Next Header CRC
^^^^^^^^^^^^^^^

Next header CRC SHALL a CRC32 of `Header database`_ that SHALL be stored in UINT32.


_`HeaderInfo`
Header encode Information
---------------------------

Header encode Information is a Streams Information data for Header data as
encoded data followed after ID 0x17.

::

    +---+======================+
    |17 | Streams Information  |
    +---+======================+



Header
------

Header SHALL be consist of archive properties that is required to extract it.
It  MAY be also consist of file list information.
It SHALL placed at a position where Start header offset pointed in archive file.
Header database MAY be encoded.

When raw header is located, it SHOULD become the following structure.
Raw header SHALL start with one byte ID 0x01.

::

    +---+=========================+
    |01 | Archive Properties      |
    +---+=========================+

Archive Properties
------------------

Archive properties MAY consist of Additional Streams and Main Streams.
Additional Streams MAY NOT exist.
Main Streams MAY NOT exist if archive contents is empty.

::

    +====================+
    | Additional Streams |
    +====================+
    | Main Streams       |
    +====================+


Additional Streams
------------------

Additional Streams SHALL consist with StreamsInfo.
Structure of Additional Streams SHALL be as same as Main Streams.

::

    +----+==============================+
    | 03 | Streams Information          |
    +----+==============================+


Main Streams
------------

Main Streams SHALL consist with StreamsInfo.

::

    +----+==============================+
    | 04 | Streams Information          |
    +----+==============================+


Streams Information
-------------------

Streams Info SHALL contain with Pack Info, Coders Info and SubStreamsInfo.


::

    +===============================+
    | Pack Information              |
    +===============================+
    | Coders Information            |
    +===============================+
    | Substreams Information        |
    +===============================+



Pack Information
----------------

Pack Information SHALL start with one byte of id value; 0x06.
Pack Information SHALL be const with Pack Position, Number of Pack Streams,
a list of sizes of Pack Streams and a list of CRCs of pack streams.
Pack positon and Number of Pakc streams SHALL be stored as
variable length UINT64 form.
Sizes of packed Streams SHALL stored as list of UINT64.

::

    +----+==========================================================================+
    | 06 | Pack Position                                                            |
    +----+==========================================================================+
    | Number of Pack Streams                                                        |
    +===============================================================================+
    | (Sizes of Pack Streams[Num of folders][Num of outstreams for each folder])    |
    +===============================================================================+
    | (CRCs of Packed Streams[Num of folders])                                      |
    +===============================================================================+


Pack Position
^^^^^^^^^^^^^

Pack Position SHALL indicate a position of encoded streams that value SHALL be
an offset from the end of signature header.
It MAY be a next position of end of signature header.

Number of Pack Streams
^^^^^^^^^^^^^^^^^^^^^^

Number of Pack Streams SHALL indicate a number of encoded streams.
LZMA and LZMA2 SHOULD have a single (one) stream.
7-zip CAN have encoding methods which produce multiple encoded streams.
When there are multiple streams, a value of Number of Pack Streams SHALL
indicate it.

Sizes of Pack Streams
^^^^^^^^^^^^^^^^^^^^^

Sizes of Pack Streams SHOULD be omitted when Number of Pack Streams is zero.
This is an array of UINT64 values which length is as same as Number of Pack Streams.
Size SHALL be positive integer and SHALL stored in UINT64.

::

     0   1
    +---+---+---+---+---+---+---+---+
    | 09 | Sizes of Pack Streams    |
    +---+---+---+---+---+---+---+---+


CRCs of Pack Streams
^^^^^^^^^^^^^^^^^^^^

When Number of Pack Streams is zero, then CRCs of Pack Streams SHALL not exist.
It also MAY NOT be placed. CRC SHALL be CRC32 and stored in UINT32.

::

     0   1
    +---+---+---+---+---+---+---+---+
    | 0A | CRCs of Pack Streams     |
    +---+---+---+---+---+---+---+---+


Coders Information
------------------

Coders Information SHALL located after Main Streams Information.
It SHALL provide encoding and encryption filter parameters.
It MAY be a single coder or multiple coders defined.
It SHALL NOT be more than five coders. (Maximum four)

::

     0   1
    +---+---+---+---+---+---+---+------+
    | 07 |  Folders Information ...    |
    +---+---+---+---+---+---+---+------+--------------+
    | Coders Unpack Sizes   | Unpack Digests          |
    +---+---+---+---+---+---+---+---+------------+----+



Folders Information
^^^^^^^^^^^^^^^^^^^

Folders information MAY be placed external of header block, otherwise it CAN be at
Packed Streams for Headers. When Folders information is located at Packed Streams
for Headers, header block SHALL become

::

    +---+---+---+---+---+---+---+---+------------+----+
    | 0B | Number of Folders| 01| Data Stream Index   |
    +---+---+---+---+---+---+---+---+------------+----+

These each numbers,  other than BYTE ID such as 0x0B 0x00, SHALL be presented
as UINT64 integer number.
When Folder information

::

     0   1
    +---+---+---+---+---+---+---+---+------------+----+
    | 00| Folder
    +---+---+---+---+---+---+---+---+------------+----+



Appendix: BNF expression (Informative)
======================================


This clause shows extended BNF expression of 7-zip file format.

.. productionlist::
   7-zip archive: SignatureHeader, [PackedStreams],
                   : [PackedStreamsForHeaders], Header | HeaderInfo

.. productionlist::
   SignatureHeader: Signature, ArchiveVersion, StartHeader

.. productionlist::
   Signature: b'7z\xBC\xAF\x27\x1C'


.. productionlist::
    ArchiveVersion : b'\x00\x04'

.. productionlist::
    StartHeader: StartHeaderCRC, NextHeaderOffset, NextHeaderSize, NextHeaderCRC

.. productionlist::
   StreamsInfo: PackInfo
              : CodersInfo
              : SubStreamsInfo

.. productionlist::
    PackInfo: 0x06, PackPos, NumPackStreams, SizesOfPackStream, CRCsOfPackStreams

.. productionlist::
    CodersInfo: 0x07, FoldersInfo


.. productionlist::
    Folders Information: 0x0B, NumFolders, Folder definitions, CoderUnpackSizes, UnpackDigests, 0x00

.. productionlist::
    Folder definitions: 0x00, Folders, [Folders] | 0x01, DataStreamIndex

.. productionlist::
    CoderUnpackSizes: 0x0C, UnPackSize, [UnpackSize], ...

.. productionlist::
    UnpackDigests: 0x0A, UnPackDigests CRC, [UnpackDigests CRC], ...


Appendix: Rationale
===================

Byte order
----------

It has been asked why 7-zip uses little endian byte order. It is a historical reason,
that 7-zip was born as Microsoft Windows application in 1999, and its file format was
a windows application format, when only little endian was used on target platform.

CRC32
-----

CRC32 is a checksum.

Encode
------

Encode in this document express compressed, encrypted and/or filter data. When encoding,
it should lead encoding metadata.

Extract
-------

Extract in this document express decompress, decryption and/or filter data from archive.


UTF-16-LE
---------

Unicode UTF-16 encoding uses 2 bytes or 4 bytes to represent Unicode character.
Because it is not one byte ordering, we need to consider endian, byte order.
UTF-16-LE is a variant of UTF-16 definition which use Little-Endian for store data.


Appendix: 7zFormat.txt (Informative)
====================================

This clause quote 7zFormat.txt distributed with 7-zip application.

.. literalinclude:: 7zFormat.txt

Appendix: CRC algorithm (informative)
=====================================

Chunk CRCs are calculated using standard CRC methods with pre and post conditioning,
as defined by ISO 3309 [ISO-3309] or ITU-T V.42 [ITU-T-V42]. The CRC polynomial employed is

::

   x^32+x^26+x^23+x^22+x^16+x^12+x^11+x^10+x^8+x^7+x^5+x^4+x^2+x+1

The 32-bit CRC register is initialized to all 1's, and then the data from each byte
is processed from the least significant bit (1) to the most significant bit (128).
After all the data bytes are processed, the CRC register is inverted
(its ones complement is taken).
This value is transmitted (stored in the file) MSB first.
For the purpose of separating into bytes and ordering, the least significant bit of
the 32-bit CRC is defined to be the coefficient of the x31 term.

Practical calculation of the CRC always employs a precalculated table to greatly
accelerate the computation


Full Copyright Statement
========================

Intellectual Property
=====================

Acknowledgement
===============