.. _sevenzip-specifications:

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
7-zip implementation.

A purpose of this document is to provide a concrete documentation to realize compatibility
between implementations.


Copyright Notice
================

Copyright (C) 2020 Hiroshi Miura


Introduction
================

Purpose
-----------

This specification is intended to define a cross-platform, interoperable file storage and
transfer format. The information here is meant to be a concise guide for those wishing
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

This specification does not provide technical specification of compression methods
such as LZMA, LZMA2, Delta, BCJ and every other methods.
It also does not provide technical specification of encryption and hash methods
such as AES and SHA256.

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


Conventions
===========

Diagram conventions
-------------------

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


When label is placed inside '( )' bracket, it express the field is optional.

::

    +=============================+
    | (Packed Streams)            |
    +=============================+


When two or more labels are placed inside '( )' bracket separeted with bartical bar '|',
it express the field is selectable.

::

    +=============================+
    | (A | B)                     |
    +=============================+


This example means a field is mandatory but it can be A or B.

When adding a block bracket '[]' at end of label, it means the field is a list of
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
| First_Byte  | Extra_Bytes  | Value                        |
| (binary )   |              | (y: little endian integer)   |
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


BooleanList
^^^^^^^^^^^

BooleanList is a list of boolean bit arrays.
It has two field. First it defines an existence of boolean values for each items of number of files or
objects. Then boolean bit fields continues.
There is an extension of expression that indicate all boolean values is True, and
skip boolean bit fields.

::

    +----+===========================================+
    | 00 | bit field of booleans                     |
    +----+===========================================+

The bit field is defined which order is from MSB to LSB,
i.e. bit 7 (MSB) of first byte indicate a boolean for first stream, object or file,
bit 6 of first byte indicate a boolean for second stream, object or file, and
bit 0(LSB) of second byte indicate a boolean for 16th stream, object or file.

A length is vary according to a number of items to indicate.
If a number of items is not multiple of eight, rest of bitfield SHOULD zero.


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
    | Signature             | VN    |
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



VN (version number, 2 byte)
---------------------------

Version number SHALL consist with two bytes.
Just in case something needs to be modified in the future.

::

            0               1
    +---------------+---------------+
    | Major version | Minor version |
    +---------------+---------------+

Major version is 0x00, and minor version is 0x04 for now.

.. _`StartHeader`:

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


.. _`StartHeaderCRC`:

Start Header CRC
^^^^^^^^^^^^^^^^

Start header CRC SHALL be a CRC32 of `Start Header`_ It SHALL be stored in form of UINT32.
This CRC value SHALL be calculated from Next Header Offset, Next Header size and
Next Header CRC.


.. _`NextHeaderOffset`:

Next Header offset
^^^^^^^^^^^^^^^^^^

Next header offset SHALL be an offset from end of signature header to header database.
Because signature header always consist with 32 bytes, the offset SHOULD be a value that
absolute position of header database in archive file - 32 bytes.
Next header offset SHALL be stored as REAL_UINT64.

.. _`NextHeaderSize`:

Next Header size
^^^^^^^^^^^^^^^^

Next header size SHALL be an size of a header database. Because a header database MAY be
encoded, Next header size SHALL consist of encoded(packed) size, not a raw size.
Next header size SHALL be stored as REAL_UINT64.

.. _`NextHeaderCRC`:

Next Header CRC
^^^^^^^^^^^^^^^

Next header CRC SHALL a CRC32 of Header that SHALL be stored in UINT32.


.. _`PorpertyIDs`:

Property IDs
------------

Information stored in Header MAY be placed after Property ID.
For example, Header Info block start with 0x01, which means Header, then
continues data blocks, and 0x00, which is END, is placed at last.
This structure can be recursive but there is a rules where paticular
ID can exist.

==== ==========
ID   Property
==== ==========
0x00 END
0x01 Header
0x02 ArchiveProperties
0x03 AdditionalStreamsInfo
0x04 MainStreamsInfo
0x05 FilesInfo
0x06 PackInfo
0x07 UnPackInfo
0x08 SubStreamsInfo
0x09 Size
0x0A CRC
0x0B Folder
0x0C CodersUnPackSize
0x0D NumUnPackStream
0x0E EmptyStream
0x0F EmptyFile
0x10 Anti
0x11 Name
0x12 CTime
0x13 ATime
0x14 MTime
0x15 Attributes
0x16 Comment
0x17 EncodedHeader
0x18 StartPos
0x19 Dummy
==== ==========


.. _`HeaderInfo`:

Header encode Information
---------------------------

Header encode Information is a Streams Information data for Header data as
encoded data followed after ID 0x17.

::

    +---+======================+
    |17 | Streams Information  |
    +---+======================+


.. _Header:

Header
------

Header SHALL be consist of archive properties that is required to extract it.
It  MAY be also consist of file list information.
It SHALL placed at a position where Start header offset pointed in archive file.
Header database MAY be encoded.

When raw header is located, it SHOULD become the following structure.
Raw header SHALL start with one byte ID 0x01.

::

    +---+
    | 01|
    +---+====================+
    | 03| Additional Streams |
    +---+====================+
    | 04| Main Streams       |
    +---+====================+
    | 05| Files Information  |
    +---+====================+


Additional Streams and Main Streams has a same structure as Streams Information.

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

    +----+===================================================================+
    | 06 | Pack Position                                                     |
    +----+===================================================================+
    | Number of Pack Streams                                                 |
    +========================================================================+
    | (Sizes of Pack Streams[Num of folders][Num of outstreams of folders])  |
    +========================================================================+
    | (CRCs of Packed Streams[Num of folders])                               |
    +========================================================================+


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

    +---+==========================+
    | 09| Sizes of Pack Streams    |
    +---+==========================+


CRCs of Pack Streams
^^^^^^^^^^^^^^^^^^^^

When Number of Pack Streams is zero, then CRCs of Pack Streams SHALL not exist.
It also MAY NOT be placed. CRC SHALL be CRC32 and stored in UINT32.

::

    +---+==========================+
    | 0A| CRCs of Pack Streams     |
    +---+==========================+


Coders Information
------------------

Coders Information SHALL located after Main Streams Information.
It SHALL provide encoding and encryption filter parameters.
It MAY be a single coder or multiple coders defined.
It SHALL NOT be more than five coders. (Maximum four)

::

    +---+
    | 07|
    +---+=============================+---------+
    | 0B| Number of folders           | External|
    +---+=============================+---------+

Folders information MAY be placed external of header block at Packed
Streams for Headers. When it is placed external, External flag is 0x01.
For this configuration, Coders Information becomes as follows;

::

    +---+
    | 07|
    +---+===========================================+
    | 0B| Number of Folders                         |
    +---+===========================================+
    | 01| Data Stream Index                         |
    +---+===========================================+
    | 0C| UnpackSizes[ total number of outstreams ] |
    +---+===========================================+
    | 0A| UnPackDigests[ Number of folders ]        |
    +---+===========================================+


In default Folders information is placed inline, then External flag is 0x00.

::

    +---+
    | 07|
    +---+===========================================+
    | 0B| Number of Folders                         |
    +---+===========================================+
    | 00| Folders[Number of Folders]                |
    +---+===========================================+
    | 0C| UnpackSizes[ total number of outstreams ] |
    +---+===========================================+
    | 0A| UnPackDigests[ Number of folders ]        |
    +---+===========================================+


UnpackSizes
^^^^^^^^^^^

UnpackSizes is a list of decompress sizes for each archived file data.
When extract data from the archive, it SHALL be distilled from unpack streams
and split chunk into defined sizes.

Filenames are defined in File Information block. An order of data chunks and
a order of filenames SHALL be same, except for filenames which is defined as
empty stream.


UnpackDigests
^^^^^^^^^^^^^

UnpackDigests is a list of CRC32 of decompress deta digests for each folders.
When extract data from the archive, it CAN check an integrity of data.

It SHALL be a list of UINT64 and its length SHALL be as same as number of folders.
It MAY be skipped when Substreams Information defined.


Folders
-------

Folder in 7-zip archive means a basic container unit for encoded data.
It brings encoded data. The data chunk Packed Streams is defined as
series of Folders.

Each Folder has coder information. CoderInfo is consist of flag,
number of streams and properties.

Flag indicate the coder is simple i.e. single input and single output,
or comprex i.e. multiple input, multiple output.

When simple coder, number of streams is always one for input,
and one for output, so it SHALL be skipped.

::

    +===================+======================================+
    | Number of coder   |  Coder Properties[ Number of coder ] |
    +===================+======================================+

Number of coder SHALL be a UINT64 integer number.
Coder Properties SHALL be a list of Coder Property with length SHALL be
as same as Number of coder.

Coder Property
^^^^^^^^^^^^^^

Coder Property is defined with flag which indicate coder types.
According to flag that indicate coder is complex, the Coder Property
MAY have a number of input and output streams of coder.

Flag is defined in one byte as following bit definitions.

* bit 3-0: Codec ID size
* bit 4: Is complex codec
* bit 5: There are attributes
* bit 6-7: Reserved, it SHOULD always be zero.

::

    +------+==========================+
    | flag | coder ID [Codec ID size] |
    +------+==========================+
    +================+================+
    | [NumInStreams] | [NumOutStreams]|
    +================+================+
    | [Property Size]| [Properties]   |
    +================+================+
    | [Input Index]  | [Output Index] |
    +================+================+
    | [Packed Stream Indexes ]        |
    +=================================+

A coder property format is vary with flag.
Following pseudo code indicate how each parameter located for informative purpose.

::

    if (Is Complex Coder)
     {
       UINT64 `NumInStreams`;
       UINT64 `NumOutStreams`;
     }
     if (There Are Attributes)
     {
       UINT64 `PropertiesSize`
       BYTE `Properties[PropertiesSize]`
     }
    }
    NumBindPairs :  = `NumOutStreamsTotal` – 1;
    for (`NumBindPairs`)
     {
       UINT64 `InIndex`;
       UINT64 `OutIndex`;
     }
    NumPackedStreams : `NumInStreamsTotal` – `NumBindPairs`;
     if (`NumPackedStreams` > 1)
       for(`NumPackedStreams`)
       {
         UINT64 `Index`;
       };



When using only simple codecs, which has one input stream and one output stream,
coder property become as simple as follows;

::

    +------+==========================+=================+==============+
    | flag | coder ID [Codec ID size] | [Property Size] | [Properties] |
    +------+==========================+=================+==============+


Here is an example of bytes of coder property when specifying LZMA.
In this example, first byte 0x23 indicate that coder id size is three bytes, and
it is not complex codec and there is a codec property.
A coder ID is b'\x03\x01\x01' and property length is five and property is
b'\x5D\x00\x10\x00\x00'.

::

    +---+---+---+---+---+---+---+---+---+---+
    | 23| 03| 01| 01| 05| 5D| 00| 10| 00| 00|
    +---+---+---+---+---+---+---+---+---+---+




Codec IDs
---------

Conformant implementations SHALL support mandatory codecs that are COPY, LZMA, LZMA2, BCJ, and Delta.
There are a variant of BCJ that are X86, PowerPC, SPARC, ARM, ARMTHUMB, and IA64.
Conformant implementations SHOULD also support optional codecs that are AES, BZIP2, DEFLATE, BCJ2, and PPMd.
Implementations MAY support additional codecs that are ZStandard, and LZ4.
It MAY also support proprietary codec such as DEFLATE64.

Conformant implementations SHALL accept these codec IDs and when it does not support it,
it SHOULD report it as not supported.

Here is a list of famous codec IDs.

========= ===========
NAME      ID
========= ===========
COPY      0x00
DELTA     0x03
BCJ       0x04
LZMA      0x030101
P7Z_BCJ   0x03030103
BCJ_PPC   0x03030205
BCJ_IA64  0x03030301
BCJ_ARM   0x03030501
BCJ_ARMT  0x03030701
BCJ_SPARC 0x03030805
LZMA2     0x21
BZIP2     0x040202
DEFLATE   0x040108
DEFLATE64 0x040109
ZSTD      0x04f71101
LZ4       0x04f71104
AES       0x06f10701
========= ===========


Substreams Information
----------------------

Substreams Information hold an information about archived data blocks
as in extracted form. It SHALL exist that number of unpack streams,
size of each unpack streams, and CRC of each streams.

::

    +---+
    | 08|
    +---+==========================================================+
    | 0D| Number of unpack streams for Folders [Number of Folders] |
    +---+==========================================================+
    | 09| Sizes of unpack streams[total number of unpack streams]  |
    +---+==========================================================+
    | 0A| CRC of unpack streams[total number of unpack streams ]   |
    +---+==========================================================+


Files Information
-----------------

Files Information SHOULD hold a list of files, directories and symbolic links.
Its order SHALL be as same as order of streams defined in packed information.

::

    +=================+=================+================+
    | Number of files | [Empty Streams] | [ Empty Files] |
    +---+====================+===========================+
    | 11| BooleanList        |  list of FileNames        |
    +---+====================+===========================+
    | 15| BooleanList        |  list of Attributes       |
    +---+====================+===========================+
    | [ CTime ]       | [ ATime ]       | [ Mtime ]      |
    +=================+=================+================+



list of FileNames
^^^^^^^^^^^^^^^^^

list of FileNames data can be externally encoded, then

::

    +--------------+=============+
    |external=0x01 | [DataIndex] |
    +--------------+=============+

Otherwise, filenames is inline,


::

    +----+===============================+
    | 00 |  FileNames[number of files]   |
    +----+===============================+


FileName SHALL be a wide character string encoded with UTF16-LE and
follows wchar_t NULL character, i.e. 0x0000.


list of Attributes
^^^^^^^^^^^^^^^^^^

list of attributes SHALL start ID 0x15 then follows BooeanList
which defines whether property is defined or not for each files.

::

    +---+=============+==========================+
    | 15| BooleanList |  list of property        |
    +---+=============+==========================+


 list of property can be external then it defines data index.


Attribute
^^^^^^^^^

Attribute is a UINT32 integer value.

.. list-table:: Attribute values
    :widths: 10 50
    :header-rows: 1
    :stub-columns: 1

    * - ID/Value
      - Description
    * - FILE_ATTRIBUTE_READONLY 1 (0x1)
      - A file that is read-only.
    * - FILE_ATTRIBUTE_HIDDEN 2 (0x2)
      - The file or directory is hidden.
    * - FILE_ATTRIBUTE_DIRECTORY 16 (0x10)
      - It identifies a directory.
    * - FILE_ATTRIBUTE_ARCHIVE 32 (0x20)
      - A file or directory that is an archive file or directory.
    * - FILE_ATTRIBUTE_REPARSE_POINT 1024 (0x400)
      - file or directory that has an associated reparse point, or a file that is a symbolic link.
    * - bit 16-31
      - UNIX file permissions and attributes.
    * - UNIX_EXTENSION (0x8000)
      - Indicate a unix permissions and file attributes are bundled when 1.

CTime
^^^^^

::

    +---+===============+
    | 12|  FileTimes    |
    +---+===============+

ATime
^^^^^

::

    +---+===============+
    | 13|  FileTimes    |
    +---+===============+


MTime
^^^^^

::

    +---+===============+
    | 14|  FileTimes    |
    +---+===============+


FileTimes
^^^^^^^^^

FileTimes SHALL be a list of file time specs. It SHALL be a bit array of defined flag
and then continues a list of Time spec for each files.

When it defines time spec for all of files, it SHALL place 0x01 which means all-defined.
then it SHALL continue a list of time spec, that length is as same as number of files.

::

    +=============+==========================================+
    | BooleanList |   list of Time spec                      |
    +=============+==========================================+

If it defines time spec of a part of files, it SHALL place 0x00 which means boolean


list of Time spec
^^^^^^^^^^^^^^^^^

::

    +----------+================================================+
    | external |  Time spec[Number of files]                     |
    +----------+================================================+

Time spec
^^^^^^^^^

Time spec is a UINT64 value. FILETIME is 100-nanosecond intervals since 1601/01/01 (UTC)


========
Appendix
========

Appendix: BNF expression (Informative)
======================================


This clause shows extended BNF expression of 7-zip file format.

.. productionlist::
   7-zip archive: SignatureHeader, [PackedStreams],
                : [PackedStreamsForHeaders], Header | HeaderInfo
   SignatureHeader: Signature, ArchiveVersion, StartHeader
   Signature: b'7z\xBC\xAF\x27\x1C'
   ArchiveVersion : b'\x00\x04'
   StartHeader: StartHeaderCRC, NextHeaderOffset, NextHeaderSize, NextHeaderCRC
   StreamsInfo: PackInfo, CodersInfo, SubStreamsInfo
   PackInfo: 0x06, PackPos, NumPackStreams, SizesOfPackStream, CRCsOfPackStreams
   CodersInfo: 0x07, FoldersInfo
   Folders Information: 0x0B, NumFolders, FolderInfo, CoderUnpackSizes, UnpackDigests, 0x00
   FoldersInfo: 0x0B, NumFolders, (0x00, Folders) | (0x01, DataStreamIndex)
              : [0x0C, UnPackSizes, [0x0A, UnpackDigests]], 0x00
   Folders: Folder{ Number of Folders }
   UnpackSizes: UnPackSize { Sum of NumOutStreams for each Folders }
   UnpackSize: UINT64
   UnpackDigests: CRC32 { Number of folders }
   SubStreamsInfo: 0x08, 0x0D, NumUnPackStreamsInFolders{Num of Folders],
                 : 0x09, UnPackSize, 0x0A, Digests{Number of streams with unknown CRC}, 0x00
   Folder: NumCoders, CoderData { NumCoders }
   CoderData: CoderFlag, CoderID, NumCoderStreamInOut, Properties, BinPairs, PackedStreamIndex
   CoderFlag: BYTE(bit 0:3 CodecIdSize, 4: Is Complex Coder, 5: There Are Attributes, 6: Reserved, 7: 0)
   CoderId: BYTE{CodecIdSize}
   FilesInfo: 0x05, NumFiles, FileInfo, [FileInfo]
   FileInfo: NumFiles, [0x0E, bit array of IsEmptyStream], [0x0F, bit array of IsEmptyFile],
           : [0x12, FileTime], [0x13, FileTime], [0x14, FileTime], [0x11, FileNames], [0x15, Attributes]
   FileTime: (0x00, bit array of TimeDefined |  0x01),
           : (0x00, list of Time | 0x01, DataIndex)
   FileNames: (0x00, list of each filename | 0x01, DataIndex)
   filename: Name, 0x0000
   Name: UTF16-LE Char, [Name]
   Attributes: (0x00, bit array of AttributesAreDefined |  0x01),
             : (0x00, list of Attribute | 0x01, DataIndex)


::

    if (Is Complex Coder)
     {
       UINT64 `NumInStreams`;
       UINT64 `NumOutStreams`;
     }
     if (There Are Attributes)
     {
       UINT64 `PropertiesSize`
       BYTE `Properties[PropertiesSize]`
     }
    }
    NumBindPairs :  = `NumOutStreamsTotal` – 1;
    for (`NumBindPairs`)
     {
       UINT64 `InIndex`;
       UINT64 `OutIndex`;
     }
    NumPackedStreams : `NumInStreamsTotal` – `NumBindPairs`;
     if (`NumPackedStreams` > 1)
       for(`NumPackedStreams`)
       {
         UINT64 `Index`;
       };


Appendix: CRC algorithm (normative)
===================================

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

.. literalinclude:: reference/7zFormat.txt

