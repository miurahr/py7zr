#
# p7zr library
#
# Copyright (c) 2019 Hiroshi Miura <miurahr@linux.com>
# Copyright (c) 2004-2015 by Joachim Bauch, mail@joachim-bauch.de
# 7-Zip Copyright (C) 1999-2010 Igor Pavlov
# LZMA SDK Copyright (C) 1999-2010 Igor Pavlov
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import binascii
from enum import Enum, IntEnum


MAGIC_7Z = binascii.unhexlify('377abcaf271c')
READ_BLOCKSIZE = 32248
QUEUELEN = READ_BLOCKSIZE * 2


class ByteEnum(bytes, Enum):
    pass


class Property(ByteEnum):
    END = binascii.unhexlify('00')
    HEADER = binascii.unhexlify('01')
    ARCHIVE_PROPERTIES = binascii.unhexlify('02')
    ADDITIONAL_STREAMS_INFO = binascii.unhexlify('03')
    MAIN_STREAMS_INFO = binascii.unhexlify('04')
    FILES_INFO = binascii.unhexlify('05')
    PACK_INFO = binascii.unhexlify('06')
    UNPACK_INFO = binascii.unhexlify('07')
    SUBSTREAMS_INFO = binascii.unhexlify('08')
    SIZE = binascii.unhexlify('09')
    CRC = binascii.unhexlify('0a')
    FOLDER = binascii.unhexlify('0b')
    CODERS_UNPACK_SIZE = binascii.unhexlify('0c')
    NUM_UNPACK_STREAM = binascii.unhexlify('0d')
    EMPTY_STREAM = binascii.unhexlify('0e')
    EMPTY_FILE = binascii.unhexlify('0f')
    ANTI = binascii.unhexlify('10')
    NAME = binascii.unhexlify('11')
    CREATION_TIME = binascii.unhexlify('12')
    LAST_ACCESS_TIME = binascii.unhexlify('13')
    LAST_WRITE_TIME = binascii.unhexlify('14')
    ATTRIBUTES = binascii.unhexlify('15')
    COMMENT = binascii.unhexlify('16')
    ENCODED_HEADER = binascii.unhexlify('17')
    START_POS = binascii.unhexlify('18')
    DUMMY = binascii.unhexlify('19')


class CompressionMethod(ByteEnum):
    COPY = binascii.unhexlify('00')
    DELTA = binascii.unhexlify('03')
    BCJ = binascii.unhexlify('04')
    PPC = binascii.unhexlify('05')
    IA64 = binascii.unhexlify('06')
    ARM = binascii.unhexlify('07')
    ARMT = binascii.unhexlify('08')
    SPARC = binascii.unhexlify('09')
    # 7Z = 03..
    LZMA = binascii.unhexlify('030101')
    PPMD = binascii.unhexlify('030401')
    P7Z_BCJ = binascii.unhexlify('03030103')
    P7Z_BCJ2 = binascii.unhexlify('0303011B')
    BCJ_PPC = binascii.unhexlify('03030205')
    BCJ_IA64 = binascii.unhexlify('03030401')
    BCJ_ARM = binascii.unhexlify('03030501')
    BCJ_ARMT = binascii.unhexlify('03030701')
    BCJ_SPARC = binascii.unhexlify('03030805')
    LZMA2 = binascii.unhexlify('21')
    # MISC : 04..
    MISC_ZIP = binascii.unhexlify('0401')
    MISC_BZIP2 = binascii.unhexlify('040202')
    MISC_DEFLATE = binascii.unhexlify('040108')
    MISC_DEFLATE64 = binascii.unhexlify('040109')
    MISC_Z = binascii.unhexlify('0405')
    MISC_LZH = binascii.unhexlify('0406')
    NSIS_DEFLATE = binascii.unhexlify('040901')
    NSIS_BZIP2 = binascii.unhexlify('040902')
    # CRYPTO 06..
    CRYPT_ZIPCRYPT = binascii.unhexlify('06f10101')
    CRYPT_RAR29AES = binascii.unhexlify('06f10303')
    CRYPT_AES256_SHA256 = binascii.unhexlify('06f10701')


class FileAttribute(IntEnum):
    DIRECTORY = 0x10
    READONLY = 0x01
    HIDDEN = 0x02
    SYSTEM = 0x04
    ARCHIVE = 0x20
    DEVICE = 0x40
    NORMAL = 0x80
    TEMPORARY = 0x100
    SPARSE_FILE = 0x200
    REPARSE_POINT = 0x400
    COMPRESSED = 0x800
    OFFLINE = 0x1000
    ENCRYPTED = 0x4000
    UNIX_EXTENSION = 0x8000
