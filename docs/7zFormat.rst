:tocdepth: 2

.. _7zformat:

========================
7-zip format description
========================

Data Types
==========


REAL_UINT64
-----------

real uint64 integer in 8byte little endian.


UINT64
------

UINT64 means real UINT64 encoded with the following scheme

Size of encoding sequence depends from first byte

+-----------+------------+----------------------------+
| First_Byte| Extra_Bytes|       Value                |
| (binary)  | (Little E.)| (y is as little endian)    |
+===========+============+============================+
|0xxxxxxx   |            | ( xxxxxxx           )      |
+-----------+------------+----------------------------+
|10xxxxxx   | BYTE y[1]  | (  xxxxxx << (8 * 1)) + y  |
+-----------+------------+----------------------------+
|110xxxxx   | BYTE y[2]  | (   xxxxx << (8 * 2)) + y  |
+-----------+------------+----------------------------+
|1111110x   | BYTE y[6]  | (       x << (8 * 6)) + y  |
+-----------+------------+----------------------------+
|11111110   | BYTE y[7]  |                         y  |
+-----------+------------+----------------------------+
|11111111   | BYTE y[8]  |                         y  |
+-----------+------------+----------------------------+


Property IDs
------------

.. productionlist::
    kEnd: 0x00
    kHeader: 0x01
    kArchiveProperties: 0x02
    kAdditionalStreamsInfo: 0x03
    kMainStreamsInfo: 0x04
    kFilesInfo: 0x05
    kPackInfo: 0x06
    kUnPackInfo: 0x07
    kSubStreamsInfo: 0x08
    kSize: 0x09
    kCRC: 0x0A
    kFolder: 0x0B
    kCodersUnPackSize: 0x0C
    kNumUnPackStream: 0x0D
    kEmptyStream: 0x0E
    kEmptyFile: 0x0F
    kAnti: 0x10
    kName: 0x11
    kCTime: 0x12
    kATime: 0x13
    kMTime: 0x14
    kWinAttributes: 0x15
    kComment: 0x16
    kEncodedHeader: 0x17
    kStartPos: 0x18
    kDummy: 0x19

Archive Structure
=================

.. productionlist::
   ARCHIVE: `SignatureHeader`:
          : [`PackedStreams`] [`PackedStreamsForHeaders`]
          : `Header` | `PackedHeader`, `HeaderInfo`

_`Signatureheader`
==================

.. productionlist::
   SignatureHeader: `Signature` : BYTE kSignature[6] : b'7z\xBC\xAF\x27\x1C'
                  : `ArchiveVersion` : BYTE Major, Minor : 0x00, 0x04
                  : `StartHeaderCRC` : UINT32
                  : `StartHeader` : `NextHeaderOffset`
                                  : `NextHeaderSize`
                                  : `NextHeaderCRC`
   NextHeaderOffset: REAL_UINT64
   NextHeaderSize: REAL_UINT64
   NextHeaderCRC: UINT32

_`Header`
=========

.. productionlist::
   PackedStreamsForHeaders: `Headers Block`
   Headers Block: `PackedHeader` | `HeaderInfo`

   PackedHeader: BYTE `kHeader`, `ArchiveProperties`
               : BYTE `kAdditionalStreamsInfo`, `StreamsInfo`
               : BYTE `kMainStreamsInfo`, `StreamsInfo`, `FilesInfo`
               : BYTE `kEnd`
   HeaderInfo  : BYTE `kEncodedHeader`, `HeaderStreamsInfo`

.. productionlist::
   StreamsInfo: PackInfo    : BYTE NID::kPackInfo : 0x06
                            :   UINT64 `PackPos`
                            :   UINT64 `NumPackStreams`
              : CodersInfo  : BYTE NID::kUnpackInfo : 0x07
                            : BYTE NID::kFolder : 0x0B
                            :   UINT64 `NumFolders`
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
                            : UINT64[`Folders`] CRCs
              : SubStreamsInfo   : BYTE NID::kSubStreamsInfo : 0x08
                                 : BYTE NID::kNumUnPackStream : 0x0D
                                 :   UINT64 `NumUnPackStreamsInFolders[NumFolders]`
                                 : BYTE NID::kSize : 0x09
                                 :   UINT64 `UnPackSize[]`
                                 : BYTE NID::kCRC : 0x0A
                                 :   `Digests[Number of streams with unknown CRC]`
                                 : BYTE NID::kEnd

.. productionlist::
   Folder: UINT64 `NumCoders`
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

