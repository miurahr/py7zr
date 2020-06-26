
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

.. productionlist::
    FoldersInfo: 0x07
               : 0x0B, `NumFolders`
               : BYTE `External`
               : switch(External) {
               : case 0:
               :   `Folders[NumFolders]`
               : case 1:
               :   UINT64 `DataStreamIndex`
               : }
               : BYTE ID::kCodersUnPackSize : 0x0C
               : for(`Folders`)
               :   for(`Folder`.NumOutStreams)
               :      UINT64 `UnPackSize`
               : BYTE ID::kCRC : 0x0A
               : UINT64[`Folders`] UnPackDigests CRCs
               : BYTE NID::kEnd

.. productionlist::
    SubStreamsInfo: 0x08, 0x0D, `NumUnPackStreamsInFolders[NumFolders]`,
                  : 0x09, `UnPackSize[]`, 0x0A, `Digests[Number of streams with unknown CRC]`,
                  : 0x00

.. productionlist::
   Folder: `NumCoders`
         : for (`NumCoders`)
         : {
         :    BYTE
         :    {
         :      0:3 CodecIdSize
         :      4:  Is Complex Coder
         :      5:  There Are Attributes
         :      6:  Reserved
         :      7:  0
         :    }
         :    BYTE `CodecId[CodecIdSize]`
         :    if (Is Complex Coder)
         :    {
         :      UINT64 `NumInStreams`;
         :      UINT64 `NumOutStreams`;
         :    }
         :    if (There Are Attributes)
         :    {
         :      UINT64 `PropertiesSize`
         :      BYTE `Properties[PropertiesSize]`
         :    }
         :  }
         : NumBindPairs :  = `NumOutStreamsTotal` – 1;
         : for (`NumBindPairs`)
         :  {
         :    UINT64 `InIndex`;
         :    UINT64 `OutIndex`;
         :  }
         : NumPackedStreams : `NumInStreamsTotal` – `NumBindPairs`;
         :  if (`NumPackedStreams` > 1)
         :    for(`NumPackedStreams`)
         :    {
         :      UINT64 `Index`;
         :    };

.. productionlist::
   FilesInfo: BYTE NID::kFilesInfo : 0x05
            :   UINT64 `NumFiles`
            : for (;;){
            :    BYTE PropertyType;
            :    if (aType == 0)
            :      break;
            :    UINT64 Size;
            :    switch(PropertyType)    {
            :      kEmptyStream:   (0x0E)
            :        for(NumFiles)
            :          BIT IsEmptyStream
            :      kEmptyFile:     (0x0F)
            :        for(EmptyStreams)
            :          BIT IsEmptyFile
            :      kAnti:          (0x10)
            :        for(EmptyStreams)
            :          BIT IsAntiFile
            :      case kCTime: (0x12)
            :      case kATime: (0x13)
            :      case kMTime: (0x14)
            :        BYTE AllAreDefined
            :        if (AllAreDefined == 0)        {
            :          for(NumFiles)
            :            BIT TimeDefined
            :        }
            :        BYTE External;
            :        if(External != 0)
            :          UINT64 DataIndex
            :        []
            :        for(Definded Items)          REAL_UINT64 Time
            :        []
            :
            :      kNames:     (0x11)
            :        BYTE External;
            :        if(External != 0)
            :          UINT64 DataIndex
            :        []
            :        for(Files)
            :        {
            :          wchar_t Names[NameSize];
            :          wchar_t 0;
            :        }
            :        []
            :
            :      kAttributes:  (0x15)
            :        BYTE AllAreDefined
            :        if (AllAreDefined == 0)
            :        {
            :          for(NumFiles)
            :            BIT AttributesAreDefined
            :        }
            :        BYTE External;
            :        if(External != 0)
            :          UINT64 DataIndex
            :        []
            :        for(Definded Attributes)
            :          UINT32 Attributes
            :        []
            :    }

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

