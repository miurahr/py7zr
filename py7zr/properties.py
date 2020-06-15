#
# p7zr library
#
# Copyright (c) 2019,2020 Hiroshi Miura <miurahr@linux.com>
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
import lzma
from enum import Enum
from typing import List

MAGIC_7Z = binascii.unhexlify('377abcaf271c')
FINISH_7Z = binascii.unhexlify('377abcaf271d')
READ_BLOCKSIZE: int = 32248
QUEUELEN = READ_BLOCKSIZE * 2

# Esposed constants
FILTER_LZMA = lzma.FILTER_LZMA1
FILTER_LZMA2 = lzma.FILTER_LZMA2
FILTER_DELTA = lzma.FILTER_DELTA
FILTER_ARM = lzma.FILTER_ARM
FILTER_ARMTHUMB = lzma.FILTER_ARMTHUMB
FILTER_IA64 = lzma.FILTER_IA64
FILTER_POWERPC = lzma.FILTER_POWERPC
FILTER_SPARC = lzma.FILTER_SPARC
FILTER_X86 = lzma.FILTER_X86
CHECK_CRC32 = lzma.CHECK_CRC32
CHECK_CRC64 = lzma.CHECK_CRC64
CHECK_SHA256 = lzma.CHECK_SHA256
CHECK_NONE = lzma.CHECK_NONE
CHECK_ID_MAX = lzma.CHECK_ID_MAX
CHECK_UNKNOWN = lzma.CHECK_UNKNOWN
PRESET_DEFAULT = lzma.PRESET_DEFAULT
PRESET_EXTREME = lzma.PRESET_EXTREME
FILTER_CRYPTO_AES256_SHA256 = 0x06F10701
FILTER_CRYPTO_ZIP = 0x06F10101
FILTER_CRYPTO_RAR29 = 0x06F10303

FILTER_BZIP2 = 0x31
FILTER_DEFLATE = 0x32
FILTER_COPY = 0x33
FILTER_ZSTD = 0x35

ARCHIVE_DEFAULT = [{'id': FILTER_X86}, {'id': FILTER_LZMA2, 'preset': 7 | PRESET_DEFAULT}]
ENCODED_HEADER_DEFAULT = [{"id": FILTER_LZMA2, "preset": 7 | PRESET_DEFAULT}]
ENCRYPTED_ARCHIVE_DEFAULT = [{'id': FILTER_LZMA2, 'preset': 7 | PRESET_DEFAULT}, {'id': FILTER_CRYPTO_AES256_SHA256}]
ENCRYPTED_HEADER_DEFAULT = [{'id': FILTER_CRYPTO_AES256_SHA256}]


class ByteEnum(bytes, Enum):
    pass


class Property(ByteEnum):
    """Hold 7zip property fixed values."""
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
    """Hold fixed values for method parameter."""
    COPY = binascii.unhexlify('00')
    DELTA = binascii.unhexlify('03')
    BCJ = binascii.unhexlify('04')
    PPC = binascii.unhexlify('05')
    IA64 = binascii.unhexlify('06')
    ARM = binascii.unhexlify('07')
    ARMT = binascii.unhexlify('08')
    SPARC = binascii.unhexlify('09')
    # SWAP = 02..
    SWAP2 = binascii.unhexlify('020302')
    SWAP4 = binascii.unhexlify('020304')
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
    #
    MISC_ZSTD = binascii.unhexlify('04f71101')
    MISC_BROTLI = binascii.unhexlify('04f71102')
    MISC_LZ4 = binascii.unhexlify('04f71104')
    MISC_LZS = binascii.unhexlify('04f71105')
    MISC_LIZARD = binascii.unhexlify('04f71106')
    # CRYPTO 06..
    CRYPT_ZIPCRYPT = binascii.unhexlify('06f10101')
    CRYPT_RAR29AES = binascii.unhexlify('06f10303')
    CRYPT_AES256_SHA256 = binascii.unhexlify('06f10701')


class SupportedMethods:
    """Hold list of methods."""
    formats = [{'name': "7z", 'magic': MAGIC_7Z}]
    methods = [{'id': CompressionMethod.COPY, 'name': 'COPY'},
               {'id': CompressionMethod.LZMA2, 'name': "LZMA2"},
               {'id': CompressionMethod.DELTA, 'name': "DELTA"},
               {'id': CompressionMethod.LZMA, 'name': "LZMA"},
               {'id': CompressionMethod.P7Z_BCJ, 'name': "BCJ"},
               {'id': CompressionMethod.BCJ_PPC, 'name': 'PPC'},
               {'id': CompressionMethod.BCJ_IA64, 'name': 'IA64'},
               {'id': CompressionMethod.BCJ_ARM, 'name': "ARM"},
               {'id': CompressionMethod.BCJ_ARMT, 'name': "ARMT"},
               {'id': CompressionMethod.BCJ_SPARC, 'name': 'SPARC'},
               {'id': CompressionMethod.MISC_DEFLATE, 'name': 'DEFLATE'},
               {'id': CompressionMethod.MISC_BZIP2, 'name': 'BZip2'},
               {'id': CompressionMethod.MISC_ZSTD, 'name': 'ZStandard'},
               {'id': CompressionMethod.CRYPT_AES256_SHA256, 'name': '7zAES'},
               ]


lzma_methods_map = {
    CompressionMethod.LZMA: lzma.FILTER_LZMA1,
    CompressionMethod.LZMA2: lzma.FILTER_LZMA2,
    CompressionMethod.DELTA: lzma.FILTER_DELTA,
    CompressionMethod.P7Z_BCJ: lzma.FILTER_X86,
    CompressionMethod.BCJ_ARM: lzma.FILTER_ARM,
    CompressionMethod.BCJ_ARMT: lzma.FILTER_ARMTHUMB,
    CompressionMethod.BCJ_IA64: lzma.FILTER_IA64,
    CompressionMethod.BCJ_PPC: lzma.FILTER_POWERPC,
    CompressionMethod.BCJ_SPARC: lzma.FILTER_SPARC,
}

lzma_methods_map_r = {
    lzma.FILTER_LZMA1: CompressionMethod.LZMA,
    lzma.FILTER_LZMA2: CompressionMethod.LZMA2,
    lzma.FILTER_DELTA: CompressionMethod.DELTA,
    lzma.FILTER_X86: CompressionMethod.P7Z_BCJ,
    lzma.FILTER_ARM: CompressionMethod.BCJ_ARM,
    lzma.FILTER_POWERPC: CompressionMethod.BCJ_PPC,
    lzma.FILTER_ARMTHUMB: CompressionMethod.BCJ_ARMT,
    lzma.FILTER_SPARC: CompressionMethod.BCJ_SPARC,
    lzma.FILTER_IA64: CompressionMethod.BCJ_IA64,
}

lzma_native_compressors = [FILTER_LZMA, FILTER_LZMA2]
lzma_native_filters = [FILTER_X86, FILTER_ARM, FILTER_DELTA, FILTER_ARMTHUMB, FILTER_POWERPC, FILTER_SPARC]
crypto_methods = [FILTER_CRYPTO_AES256_SHA256]
extra_compressors = [FILTER_ZSTD, FILTER_BZIP2, FILTER_DEFLATE]

alt_methods_map = {
    CompressionMethod.MISC_BZIP2: FILTER_BZIP2,
    CompressionMethod.MISC_DEFLATE: FILTER_DEFLATE,
    CompressionMethod.COPY: FILTER_COPY,
    CompressionMethod.CRYPT_AES256_SHA256: FILTER_CRYPTO_AES256_SHA256,
    CompressionMethod.MISC_ZSTD: FILTER_ZSTD,
}

alt_methods_map_r = {
    FILTER_BZIP2: CompressionMethod.MISC_BZIP2,
    FILTER_DEFLATE: CompressionMethod.MISC_DEFLATE,
    FILTER_COPY: CompressionMethod.COPY,
    FILTER_CRYPTO_AES256_SHA256: CompressionMethod.CRYPT_AES256_SHA256,
    FILTER_ZSTD: CompressionMethod.MISC_ZSTD,
}


def get_methods_names_string(coders_lists: List[List[dict]]) -> str:
    # list of known method names with a display priority order
    methods_namelist = ['LZMA2', 'LZMA', 'BZip2', 'DEFLATE', 'DEFLATE64*', 'delta', 'COPY', 'ZStandard', 'LZ4*', 'BCJ2*',
                        'BCJ', 'ARM', 'ARMT', 'IA64', 'PPC', 'SPARC', '7zAES']
    unsupported_methods = {CompressionMethod.P7Z_BCJ2: 'BCJ2*',
                           CompressionMethod.MISC_LZ4: 'LZ4*',
                           CompressionMethod.MISC_DEFLATE64: 'DEFLATE64*'}
    methods_names = []
    for coders in coders_lists:
        for coder in coders:
            for m in SupportedMethods.methods:
                if coder['method'] == m['id']:
                    methods_names.append(m['name'])
            if coder['method'] in unsupported_methods:
                methods_names.append(unsupported_methods[coder['method']])
    return ', '.join(filter(lambda x: x in methods_names, methods_namelist))
