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
| (binary)  |            |                            |
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
    0x00 : kEnd
    0x01 : kHeader
    0x02 : kArchiveProperties
    0x03 : kAdditionalStreamsInfo
    0x04 : kMainStreamsInfo
    0x05 : kFilesInfo
    0x06 : kPackInfo
    0x07 : kUnPackInfo
    0x08 : kSubStreamsInfo
    0x09 : kSize
    0x0A : kCRC
    0x0B : kFolder
    0x0C : kCodersUnPackSize
    0x0D : kNumUnPackStream
    0x0E : kEmptyStream
    0x0F : kEmptyFile
    0x10 : kAnti
    0x11 : kName
    0x12 : kCTime
    0x13 : kATime
    0x14 : kMTime
    0x15 : kWinAttributes
    0x16 : kComment
    0x17 : kEncodedHeader
    0x18 : kStartPos
    0x19 : kDummy


Headers
=======

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

.. productionlist::
   PackedStreamsForHeaders: `Headers Block`
   Headers Block: PackedHeader: BYTE NID::kHeader : 0x01
                                :   `ArchiveProperties`
                                : BYTE NID::kAdditionalStreamsInfo : 0x03
                                :   `StreamsInfo`
                                : `BYTE NID::kMainStreamsInfo : 0x04
                                :   `StreamsInfo`
                                : `FilesInfo`
                                : BYTE NID::kEnd
                : HeaderInfo  : BYTE NID::kEncodedHeader : 0x17
                                : `StreamsInfo` for encoded header

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

