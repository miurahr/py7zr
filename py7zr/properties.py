#
# p7zr library
#
# Copyright (c) 2019-2021 Hiroshi Miura <miurahr@linux.com>
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
import platform
import sys
from typing import Final

MAGIC_7Z: Final = binascii.unhexlify("377abcaf271c")
FINISH_7Z: Final = binascii.unhexlify("377abcaf271d")

COMMAND_HELP_STRING: Final = """<Commands>
  c : Create archive with files
  i : Show information about supported formats
  l : List contents of archive
  t : Test integrity of archive
  x : eXtract files with full paths
"""


def get_default_blocksize():
    if platform.python_implementation() == "PyPy" and sys.version_info >= (3, 6, 9):
        return 1048576
    elif sys.version_info >= (3, 7, 5):
        return 1048576
    else:
        return 32768


# Exposed constants
FILTER_LZMA: Final = lzma.FILTER_LZMA1
FILTER_LZMA2: Final = lzma.FILTER_LZMA2
FILTER_DELTA: Final = lzma.FILTER_DELTA
FILTER_ARM: Final = lzma.FILTER_ARM
FILTER_ARMTHUMB: Final = lzma.FILTER_ARMTHUMB
FILTER_IA64: Final = lzma.FILTER_IA64
FILTER_POWERPC: Final = lzma.FILTER_POWERPC
FILTER_SPARC: Final = lzma.FILTER_SPARC
FILTER_X86: Final = lzma.FILTER_X86
CHECK_CRC32: Final = lzma.CHECK_CRC32
CHECK_CRC64: Final = lzma.CHECK_CRC64
CHECK_SHA256: Final = lzma.CHECK_SHA256
CHECK_NONE: Final = lzma.CHECK_NONE
CHECK_ID_MAX: Final = lzma.CHECK_ID_MAX
CHECK_UNKNOWN: Final = lzma.CHECK_UNKNOWN
PRESET_DEFAULT: Final = lzma.PRESET_DEFAULT
PRESET_EXTREME: Final = lzma.PRESET_EXTREME
FILTER_CRYPTO_AES256_SHA256: Final = 0x06F10701
FILTER_CRYPTO_ZIP: Final = 0x06F10101
FILTER_CRYPTO_RAR29: Final = 0x06F10303

FILTER_BZIP2: Final = 0x31
FILTER_DEFLATE: Final = 0x32
FILTER_COPY: Final = 0x33
FILTER_ZSTD: Final = 0x35
FILTER_PPMD: Final = 0x36


class DEFAULT_FILTERS:
    """Default filter values."""

    ARCHIVE_FILTER: Final = [{"id": FILTER_X86}, {"id": FILTER_LZMA2, "preset": 7 | PRESET_DEFAULT}]
    ENCODED_HEADER_FILTER: Final = [{"id": FILTER_LZMA2, "preset": 7 | PRESET_DEFAULT}]
    ENCRYPTED_ARCHIVE_FILTER: Final = [{"id": FILTER_LZMA2, "preset": 7 | PRESET_DEFAULT}, {"id": FILTER_CRYPTO_AES256_SHA256}]
    ENCRYPTED_HEADER_FILTER: Final = [{"id": FILTER_CRYPTO_AES256_SHA256}]


class PROPERTY:
    """Hold 7zip property fixed values."""

    END: Final = binascii.unhexlify("00")
    HEADER: Final = binascii.unhexlify("01")
    ARCHIVE_PROPERTIES: Final = binascii.unhexlify("02")
    ADDITIONAL_STREAMS_INFO: Final = binascii.unhexlify("03")
    MAIN_STREAMS_INFO: Final = binascii.unhexlify("04")
    FILES_INFO: Final = binascii.unhexlify("05")
    PACK_INFO: Final = binascii.unhexlify("06")
    UNPACK_INFO: Final = binascii.unhexlify("07")
    SUBSTREAMS_INFO: Final = binascii.unhexlify("08")
    SIZE: Final = binascii.unhexlify("09")
    CRC: Final = binascii.unhexlify("0a")
    FOLDER: Final = binascii.unhexlify("0b")
    CODERS_UNPACK_SIZE: Final = binascii.unhexlify("0c")
    NUM_UNPACK_STREAM: Final = binascii.unhexlify("0d")
    EMPTY_STREAM: Final = binascii.unhexlify("0e")
    EMPTY_FILE: Final = binascii.unhexlify("0f")
    ANTI: Final = binascii.unhexlify("10")
    NAME: Final = binascii.unhexlify("11")
    CREATION_TIME: Final = binascii.unhexlify("12")
    LAST_ACCESS_TIME: Final = binascii.unhexlify("13")
    LAST_WRITE_TIME: Final = binascii.unhexlify("14")
    ATTRIBUTES: Final = binascii.unhexlify("15")
    COMMENT: Final = binascii.unhexlify("16")
    ENCODED_HEADER: Final = binascii.unhexlify("17")
    START_POS: Final = binascii.unhexlify("18")
    DUMMY: Final = binascii.unhexlify("19")


class COMPRESSION_METHOD:
    """Hold fixed values for method parameter."""

    COPY: Final = binascii.unhexlify("00")
    DELTA: Final = binascii.unhexlify("03")
    BCJ: Final = binascii.unhexlify("04")
    PPC: Final = binascii.unhexlify("05")
    IA64: Final = binascii.unhexlify("06")
    ARM: Final = binascii.unhexlify("07")
    ARMT: Final = binascii.unhexlify("08")
    SPARC: Final = binascii.unhexlify("09")
    # SWAP = 02..
    SWAP2: Final = binascii.unhexlify("020302")
    SWAP4: Final = binascii.unhexlify("020304")
    # 7Z = 03..
    LZMA: Final = binascii.unhexlify("030101")
    PPMD: Final = binascii.unhexlify("030401")
    P7Z_BCJ: Final = binascii.unhexlify("03030103")
    P7Z_BCJ2: Final = binascii.unhexlify("0303011B")
    BCJ_PPC: Final = binascii.unhexlify("03030205")
    BCJ_IA64: Final = binascii.unhexlify("03030401")
    BCJ_ARM: Final = binascii.unhexlify("03030501")
    BCJ_ARMT: Final = binascii.unhexlify("03030701")
    BCJ_SPARC: Final = binascii.unhexlify("03030805")
    LZMA2: Final = binascii.unhexlify("21")
    # MISC : 04..
    MISC_ZIP: Final = binascii.unhexlify("0401")
    MISC_BZIP2: Final = binascii.unhexlify("040202")
    MISC_DEFLATE: Final = binascii.unhexlify("040108")
    MISC_DEFLATE64: Final = binascii.unhexlify("040109")
    MISC_Z: Final = binascii.unhexlify("0405")
    MISC_LZH: Final = binascii.unhexlify("0406")
    NSIS_DEFLATE: Final = binascii.unhexlify("040901")
    NSIS_BZIP2: Final = binascii.unhexlify("040902")
    #
    MISC_ZSTD: Final = binascii.unhexlify("04f71101")
    MISC_BROTLI: Final = binascii.unhexlify("04f71102")
    MISC_LZ4: Final = binascii.unhexlify("04f71104")
    MISC_LZS: Final = binascii.unhexlify("04f71105")
    MISC_LIZARD: Final = binascii.unhexlify("04f71106")
    # CRYPTO 06..
    CRYPT_ZIPCRYPT: Final = binascii.unhexlify("06f10101")
    CRYPT_RAR29AES: Final = binascii.unhexlify("06f10303")
    CRYPT_AES256_SHA256: Final = binascii.unhexlify("06f10701")
