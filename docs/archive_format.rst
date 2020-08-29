.. _sevenzip-specifications:

************************
.7z format specification
************************

Abstract
========

7-zip archive is one of popular files compression and archive formats. There has been
no well-defined file format because there is no precise specification document in 20 years
from its birth, so it has been considered as an application proprietary format.

There are some independent implementation of utility to handle 7-zip archives,
precise documentation of specification is mandatory to keep compatibility and
interoperability among implementations.

This specification defines an archive file format of .7z archive.
A purpose of this document is to provide a concrete documentation
to archive an interoperability among implementations.


Copyright Notice
================

Copyright (C) 2020 Hiroshi Miura


Introduction
============

Purpose
-------

This specification is intended to define a cross-platform, interoperable file storage and
transfer format. The information here is meant to be a concise guide for those wishing
to implement libraries and utility to handle 7-zip archive files.

This documentations is NOT a specification of any existed utilities and libraries.
This documentation does not have some features which is implemented in an existed utility.
It is because this document purpose is to keep interoperability.


Intended audience
-----------------

This specification is intended for use by implementors of software to compress files into 7-zip format and/or
decompress files from 7-zip format.

The text of the specification assumes a basic background in programming
at the level of bits and other primitive data representations.

Scope
-----

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
it has been known as one of long lived file format.

There are two effort to make .7z archives as well-documented, portable, and long life.
One is a documentation project here, and other is a software development project
to be compatible with original 7zip and p7zip utility such as py7zr.


Notations
=========

* Use of the term SHALL indicates a required element.

* MAY NOT or SHALL NOT indicates an element is prohibited from use.

* SHOULD indicates a RECOMMENDED element.

* SHOULD NOT indicates an element NOT RECOMMENDED for use.

* MAY indicates an OPTIONAL element.


Data Representations
====================

This chapter describes basic data representations used in 7-zip file.


BYTE
----

BYTE is a basic data type to store a char, Property ID or bitfield.


BYTEARRAY
---------

BYTEARRAY is a sequence of BYTE. Its length SHALL be defined in another place.


String
------

There are two type of string data is used in 7-zip archive format.

* UTF-16-LE

* UTF-8


Integers
--------

All integers that require more than one byte SHALL be in a little endian,
Least significant byte (LSB) comes first, then more significant bytes in
ascending order of significance (LSB MSB for two byte integers, B0 B1 B2 B3
for four bytes integers). The highest bit (value 128) of byte is number bit 7
and lowest bit (value 1) is number bit 0. Values are unsigned unless otherwise
noted.

+--------------+---------+------------------------------+
| name         | size    |  description                 |
+==============+=========+==============================+
| UINT32       | 4 bytes | | integer at little endian   |
|              |         | | represent 0 to             |
|              |         | | 4,294,967,295 (0xffffffff) |
+--------------+---------+------------------------------+
| UINT64       | 8 bytes | | integer at little endian   |
|              |         | | represent 0 to             |
|              |         | | 18,446,744,073,709,551,615 |
|              |         | | (0xffffffffffffffff)       |
+--------------+---------+------------------------------+
| NUMBER       | | 1-9   | | variable length integer    |
|              | | bytes | | value represent 0 to       |
|              |         | | 18,446,744,073,709,551,615 |
|              |         | | (0xffffffffffffffff)       |
+--------------+---------+------------------------------+

NUMBER SHALL be a integer value encoded with the following scheme.
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

BitField
--------

BitField represent eight boolean values in single BYTE.

The bit field is defined which order is from MSB to LSB,
i.e. bit 7 (MSB) of first byte indicate a boolean for first stream, object or file,
bit 6 of first byte indicate a boolean for second stream, object or file, and
bit 0(LSB) of second byte indicate a boolean for 16th stream, object or file.

A length is vary according to a number of items to indicate.
If a number of items is not multiple of eight, rest of bitfield SHOULD zero.

BooleanList
-----------

BooleanList is a list of boolean bit arrays.
It has two field. First it defines an existence of boolean values for each items of number of files or
objects. Then boolean bit fields continues.
There is an extension of expression that indicate all boolean values is True, and
skip boolean bit fields.

.. railroad-diagram::

   stack:
   - 'alldefined, BYTE'
   -
      zero_or_more:
      - 'boolean, BitField'


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

.. railroad-diagram::

   stack:
   - Signature Header
   -
      optional:
      - Packed Streams
   - choice:
      -
         - Packed Streams for Header
         - Header Encode Information
      - Header


.. _`SignatureHeader`:

Signature Header
----------------

Signature header SHALL consist in 32 bytes.
Signature header SHALL start with Signature then continues
with archive version. Start Header SHALL follow after archive version.

.. railroad-diagram::

   stack:
   - Signature
   -
      - Major Version, BYTE, '0x00'
      - Minor Version, BYTE, '0x04'
   - Start Header CRC, UINT32
   -
      - Next Header Offset, NUMBER
      - Next Header Size, NUMBER
      - Next Header CRC, UINT32

It can be observed as follows when taken hex dump.

+--------+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
| address| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | A | B | C | D | E | F |
+--------+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
| 0x0000 | Signature             | VN    | S.H. CRC      | N.H. offset   |
+--------+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
| 0x0010 | offset(cont)  | N.H. size                     | N.H. CRC      |
+--------+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+


Signature
^^^^^^^^^

The first six bytes of a 7-zip file SHALL always contain b'7z\\xbc\\xaf\\x27\\x1c'.

Version Number
^^^^^^^^^^^^^^

Version number SHALL consist with two bytes.
Major version is 0x00, and minor version is 0x04 for now.

.. _`StartHeaderCRC`:

Start Header CRC
^^^^^^^^^^^^^^^^

It SHALL be stored in form of UINT32.
This CRC value SHALL be calculated from Next Header Offset, Next Header size and
Next Header CRC.

.. _`NextHeaderOffset`:

Next Header offset
^^^^^^^^^^^^^^^^^^

Next header offset SHALL be an offset from end of signature header to header database.
Because signature header always consist with 32 bytes, the offset SHOULD be a value that
absolute position of header database in archive file - 32 bytes.
Next header offset SHALL be stored as UINT64.

.. _`NextHeaderSize`:

Next Header size
^^^^^^^^^^^^^^^^

Next header size SHALL be an size of a header database. Because a header database MAY be
encoded, Next header size SHALL consist of encoded(packed) size, not a raw size.
Next header size SHALL be stored as UINT64.

.. _`NextHeaderCRC`:

Next Header CRC
^^^^^^^^^^^^^^^

Next header CRC SHALL a CRC32 of Header that SHALL be stored in UINT32.


.. _`PorpertyIDs`:

Property IDs
------------

Information stored in Header SHALL be placed after Property ID.
For example, Header Info block start with 0x01, which means Header, then
continues data blocks, and 0x00, which is END, is placed at last.
This structure can be recursive but there is a rules where particular
ID can exist.

Property ID SHALL be a BYTE.

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
-------------------------

Header encode Information is a Streams Information data for Header data as
encoded data followed after ID 0x17, EncodedHeader Property.


.. railroad-diagram::

   stack:
   - EncodedHeader, Property ID
   - Streams Information for Header, StreamsInfo


.. _Header:

Header
------

Header SHALL be consist of Main Streams.
It  MAY be also consist of file list information.
It SHALL placed at a position where Start header offset pointed in archive file.
Header database MAY be encoded.

When raw header is located, it SHOULD become the following structure.
Raw header SHALL start with one byte ID 0x01.

.. railroad-diagram::

   stack:
   - Header, Property ID
   -
      - MainStreamsInfo, Property ID
      - Pack Information
      - Coders Information
      - optional:
         - Substream Information
   - END, Property ID
   -
      optional:
      - Files Information
   - END, Property ID


Pack Information
----------------

Pack Information SHALL start with one byte of id value; 0x06.
Pack Information SHALL be const with Pack Position, Number of Pack Streams,
a list of sizes of Pack Streams and a list of CRCs of pack streams.
Pack positon and Number of Pakc streams SHALL be stored as
variable length NUMBER form.
Sizes of packed Streams SHALL stored as a list of NUMBER.

.. railroad-diagram::

   stack:
   - PackInfo, Property ID
   - Pack Position, NUMBER
   - Count of Pack Streams, NUMBER
   -
      optional:
      - Sizes of Pack Streams
   -
      optional:
      - CRCs of Pack Streams
   - END, Property ID


Pack Position
^^^^^^^^^^^^^

Pack Position SHALL indicate a position of encoded streams that value SHALL be
an offset from the end of signature header.
It MAY be a next position of end of signature header.

Count of Pack Streams
^^^^^^^^^^^^^^^^^^^^^

Count of Pack Streams SHALL indicate a number of encoded streams.
LZMA and LZMA2 SHOULD have a single (one) stream.
7-zip CAN have encoding methods which produce multiple encoded streams.
When there are multiple streams, a value of Number of Pack Streams SHALL
indicate it.

Sizes of Pack Streams
^^^^^^^^^^^^^^^^^^^^^

Sizes of Pack Streams SHOULD be omitted when Number of Pack Streams is zero.
This is an array of NUMBER values which length is as same as Count of Pack Streams.
Size SHALL be positive integer and SHALL stored in NUMBER.

.. railroad-diagram::

   stack:
   - Size, Property ID
   -
      one_or_more:
      - size, NUMBER


CRCs of Pack Streams
^^^^^^^^^^^^^^^^^^^^

When Count of Pack Streams is zero, then CRCs of Pack Streams SHALL not exist.
CRC CAN be exist and indicated as DigestDefined BooleanList.
CRC SHALL be CRC32 and stored in UINT32.


.. railroad-diagram::

   stack:
   - CRC, Property ID
   - DigestDefined, BooleanList
   -
      one_or_more:
      - crc, UINT32


Coders Information
------------------

Coders Information SHALL located after Main Streams Information.
It SHALL provide encoding and encryption filter parameters.
It MAY be a single coder or multiple coders defined.
It SHALL NOT be more than five coders. (Maximum four)

.. railroad-diagram::

   stack:
   - UnpackInfo, Property ID
   -
      - Folder, Property ID
      - Number of Folders, NUMBER
   - choice:
      -
         - Not Ext(0x00), BYTE
         - Folder
      -
         - Ext(0x01), BYTE
         - Data Stream Index, NUMBER
   -
      optional:
      - 'CodersUnpackSize, Property ID'
      - one_or_more:
         - Unpacksize, NUMBER
   -
      optional:
      - 'UnpackDigest, Property ID'
      - one_or_more:
         - UnpackDigest, UINT32
   - END, Property ID


In default Folders information is placed inline, then External flag is 0x00.


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

It SHALL be a list of NUMBER and its length SHALL be as same as number of folders.
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


.. railroad-diagram::

   stack:
   - Number of Coders, NUMBER
   - one_or_more:
      - Coder Property


Number of coder SHALL be a NUMBER integer number.
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


.. railroad-diagram::

   stack:
   - Flag, BYTE
   - Coder ID, BYTEARRAY
   - optional:
      - NumInStreams, NUMBER
      - NumOutStreams, NUMBER
   - optional:
      - Property Size, NUMBER
      - Property, BYTEARRAY
   - optional:
      - one_or_more:
         - Input Index, NUMBER
         - Outout Index, NUMBER
   - one_or_more:
      - Packed Stream Index, NUMBER


BindPairs
^^^^^^^^^

BindPairs describe connection among coders when coder produce multiple output
or required multiple input.

A coder property format is vary with flag.
Following pseudo code indicate how each parameter located for informative purpose.

::

    if (Is Complex Coder)
     {
       NUMBER `NumInStreams`;
       NUMBER `NumOutStreams`;
     }
     if (There Are Attributes)
     {
       NUMBER `PropertiesSize`
       BYTE `Properties[PropertiesSize]`
     }
    }
    NumBindPairs :  = `NumOutStreamsTotal` – 1;
    for (`NumBindPairs`)
     {
       NUMBER `InIndex`;
       NUMBER `OutIndex`;
     }
    NumPackedStreams : `NumInStreamsTotal` – `NumBindPairs`;
     if (`NumPackedStreams` > 1)
       for(`NumPackedStreams`)
       {
         NUMBER `Index`;
       };


When using only simple codecs, which has one input stream and one output stream,
coder property become as simple as follows;


.. railroad-diagram::

   stack:
   - Flag, BYTE
   - Coder ID, BYTEARRAY
   - optional:
      - Property Size, NUMBER
      - Property, BYTEARRAY


Here is an example of bytes of coder property when specifying LZMA.

* b'\x23\x03\x01\x01\x05\x5D\x00\x10\x00\x00'

In this example, first byte 0x23 indicate that coder id size is three bytes, and
it is not complex codec and there is a codec property.
A coder ID is b'\x03\x01\x01' and property length is five and property is
b'\x5D\x00\x10\x00\x00'.


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

Substream Information is an optional field that indicate substreams from
each folder produces.

When the archive is not solid, there SHALL NOT be SubStreams information.
When SubStreams Information is omitted, extractor still know a unpack size information
as folder information.

Substreams Information hold an information about archived data blocks
as in extracted form. It SHALL exist that number of unpack streams,
size of each unpack streams, and CRC of each streams


.. railroad-diagram::

   stack:
   - SubStreamsInfo, Property ID
   - NumUnpackStream, Property ID
   - one_or_more:
      - Number of unpack streams, NUMBER
   - Size, Property ID
   - one_or_more:
      - Size of unpack streams, NUMBER
   - optional:
      - CRC, Property ID
      - one_or_more:
         - digest, UINT32
   - END, Property ID


Files Information
-----------------

Files Information SHOULD hold a list of files, directories and symbolic links.
Its order SHALL be as same as order of streams defined in packed information.
A type of file is stored in Attribute field.

.. railroad-diagram::

   stack:
   - FileInfo, Property ID
   - Number of Files, NUMBER
   - optional:
      - Empty Stream, Property ID
      - Size, NUMBER
      - Flag of Empty Streams, BitField
   - optional:
      - Empty Files, Property ID
      - Size, NUMBER
      - Flag of Empty Files, BitField
   - optional:
      - Dummy, Property ID
      - Size, NUMBER
      - one_or_more:
         - '0x00'
   - Name, Property ID
   - Size, NUMBER
   - FileNamesExist, BooleanList
   - choice:
      -
         - Not External(0x00), BYTE
         - zero_or_more:
            - FileName, UTF-16-LE
      -
         - Ext(0x01), BYTE
         - Data Index, NUMBER
   - MTime, Property ID
   - Size, NUMBER
   - TimeExist, BooleanList
   - choice:
      -
         - External, BYTE, 0x00
         - one_or_more:
            - FileTime, NUMBER
      -
         - External, BYTE, 0x01
         - Data Index, NUMBER
   - optional:
      - CTime, Property ID
      - Size, NUMBER
      - TimeExist, BooleanList
      - choice:
         -
            - External, BYTE, 0x00
            - one_or_more:
               - FileTime, NUMBER
         -
            - External, BYTE, 0x01
            - Data Index, NUMBER
   - optional:
      - ATime, Property ID
      - Size, NUMBER
      - TimeExist, BooleanList
      - choice:
         -
            - External, BYTE, 0x00
            - one_or_more:
               - FileTime, NUMBER
         -
            - External, BYTE, 0x01
            - Data Index, NUMBER
   - Attribute, Property ID
   - Size, NUMBER
   - AttributeExist, BooleanList
   - choice:
      -
         - Not External(0x00), BYTE
         - zero_or_more:
            - Attribute, UINT32
      -
         - Ext(0x01), BYTE
         - Data Index, NUMBER
   - END, Property ID


Size
^^^^

Size field indicate a size of next data. For example, Name size means,
a size in byte from a start of FileNamesExist field and an end of file names.


Empty Streams
^^^^^^^^^^^^^

Empty streams has a number of emptystreams and a boolean list to indicate which
file entry does not have a packed stream.

Dummy
^^^^^

Dummy MAY be placed for alignment. When processing File Names, which is UTF-16-LE,
it is better to be aligned in word barrier.

FileName
^^^^^^^^

FileNam SHALL be a wide character string encoded with UTF-16-LE and
follows wchar_t NULL character, i.e. 0x0000.

Path separator SHALL be normalized as '/', which is as POSIX standard.
FileName SHOULD be relative path notation.


Attribute
^^^^^^^^^

Attribute is a UINT32 integer value. From bit 0 to 15 are as same as
Windows attributes. Bit 16 to 31 is used for storing unix attributes.
When file is a symbolic link, it SHOULD has an attribute that
UNIX_EXTENSION flag enabled, and link bit of unix attributes.


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
      - UNIX file permissions and attributes.  16bit shift to left of permissions and attributes.
    * - UNIX_EXTENSION (0x8000)
      - Indicate a unix permissions and file attributes are bundled when 1.


FileTime
^^^^^^^^^

FileTime are NUMBER values in 100-nanosecond intervals since 1601/01/01 (UTC)


File type and a way
===================

Normal files
------------

Normal files are stored with packed streams and ordinal file information.
Its contents are stored into packed stream.
It SHOULD have an attribute of Windows such as FILE_ATTRIBUTE_ARCHIVE.
It MAY also have an attribute of UNIX such as rwxrwxrwx permissions.

Directories
-----------

Directories are stored without packed streams. It have entries in file information.
It SHALL have an attribute which is FILE_ATTRIBUTE_DIRECTORY.
It MAY also have an attribute of UNIX such as rwxrwxrwx permissions.

Special Files
-------------

There is an extension to handle special files such as sockets, device files, and symbolic links.
A type of special files is indicated as file attribute.
Further attribute of special file is stored as a content.

Compliant client CAN skip record of special files on extraction.


Symbolic links
^^^^^^^^^^^^^^

Symbolic links are stored as packed streams and file information.
Its target file path, in relative, are recorded into packed streams
in UTF-8 character encoding.
It SHALL have a UNIX attribute which is S_IFLNK.


REPARSE_POINT on Windows
^^^^^^^^^^^^^^^^^^^^^^^^

Reparse point on windows SHOULD be stored with packed stream and file information.
Its target link path, in absolute, are recorded into packed stream
in UTF-8 character encoding.
It SHALL have an attribute which is FILE_ATTRIBUTE_REPARSE_POINT.


Appendix: BNF expression (Informative)
======================================


This clause shows extended BNF expression of 7-zip file format.

.. productionlist::
   7-zip archive: SignatureHeader, [PackedStreams],
                : [PackedStreamsForHeaders], Header | HeaderInfo
   SignatureHeader: Signature, ArchiveVersion, StartHeader
   Signature: b'7z\xBC\xAF\x27\x1C'
   ArchiveVersion : b'\x00\x04'
   StartHeader: StartHeaderCRC, NextHeaderOffset,
              : NextHeaderSize, NextHeaderCRC
   StreamsInfo: PackInfo, CodersInfo, SubStreamsInfo
   PackInfo: 0x06, PackPos, NumPackStreams,
           : SizesOfPackStream, CRCsOfPackStreams
   CodersInfo: 0x07, FoldersInfo
   Folders Information: 0x0B, NumFolders, FolderInfo,
                      : CoderUnpackSizes, UnpackDigests, 0x00
   FoldersInfo: 0x0B, NumFolders, (0x00, Folders) | (0x01, DataStreamIndex)
              : [0x0C, UnPackSizes, [0x0A, UnpackDigests]], 0x00
   Folders: Folder{ Number of Folders }
   UnpackSizes: UnPackSize { Sum of NumOutStreams for each Folders }
   UnpackSize: NUMBER
   UnpackDigests: CRC32 { Number of folders }
   SubStreamsInfo: 0x08, 0x0D, NumUnPackStreamsInFolders{Num of Folders],
                 : 0x09, UnPackSize, 0x0A,
                 : Digests{Number of streams with unknown CRC}, 0x00
   Folder: NumCoders, CoderData { NumCoders }
   CoderData: CoderFlag, CoderID, NumCoderStreamInOut, Properties,
            : BinPairs, PackedStreamIndex
   CoderFlag: BYTE(bit 0:3 CodecIdSize, 4: Is Complex Coder,
            : 5: There Are Attributes, 6: Reserved, 7: 0)
   CoderId: BYTE{CodecIdSize}
   FilesInfo: 0x05, NumFiles, FileInfo, [FileInfo]
   FileInfo: NumFiles, [0x0E, bit array of IsEmptyStream],
           : [0x0F, bit array of IsEmptyFile],
           : [0x11, FileNames],
           : [0x12, FileTime], [0x13, FileTime], [0x14, FileTime],
           : [0x15, Attributes]
   FileTime: (0x00, bit array of TimeDefined |  0x01),
           : (0x00, list of Time | 0x01, DataIndex)
   FileNames: (0x00, list of each filename | 0x01, DataIndex)
   filename: Name, 0x0000
   Name: UTF16-LE Char, [Name]
   Attributes: (0x00, bit array of AttributesAreDefined |  0x01),
             : (0x00, list of Attribute | 0x01, DataIndex)


A Coder flag affect a following CoderData existence as following algorithm;

::

    if (Is Complex Coder)
     {
       NUMBER `NumInStreams`;
       NUMBER `NumOutStreams`;
     }
     if (There Are Attributes)
     {
       NUMBER `PropertiesSize`
       BYTE `Properties[PropertiesSize]`
     }
    }
    NumBindPairs :  = `NumOutStreamsTotal` – 1;
    for (`NumBindPairs`)
     {
       NUMBER `InIndex`;
       NUMBER `OutIndex`;
     }
    NumPackedStreams : `NumInStreamsTotal` – `NumBindPairs`;
     if (`NumPackedStreams` > 1)
       for(`NumPackedStreams`)
       {
         NUMBER `Index`;
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

Unicode UTF-16 encoding uses 2 bytes or 4 bytes to represent Unicode characters.
Because it is not one byte ordering, we need to consider endian, byte order.
UTF-16-LE is a variant of UTF-16 definition which use Little-Endian for store data.


UTF-8
-----

Unicode UTF-8 encoding uses a sequence of bytes, from 1 bytes to 4 bytes to represent
Unicode characters. ISO 10646 defines it as 1 byts to 8 bytes encoding, so compliant
implementation SHALL be able to handle 8bytes sequence and mark it as invalid.
