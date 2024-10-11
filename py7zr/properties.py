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

MAGIC_7Z = binascii.unhexlify("377abcaf271c")
FINISH_7Z = binascii.unhexlify("377abcaf271d")

COMMAND_HELP_STRING = """<Commands>
  c : Create archive with files
  i : Show information about supported formats
  l : List contents of archive
  t : Test integrity of archive
  x : eXtract files with full paths
"""


def is_64bit() -> bool:
    """check if running platform is 64bit python."""
    return sys.maxsize > (1 << 32)


def is_pypy369later() -> bool:
    """check if running platform is PyPY and python 3.6.9 and later"""
    return platform.python_implementation() == "PyPy" and sys.version_info >= (3, 6, 9)


def get_default_blocksize() -> int:
    """
    Return a safe buffer size for pass to decompress/compress modules.
    We check several conditions;

    1. 32bit python
      It sometimes fails with memory_error
      when decompress/compress large file (hundreds of MiB) on 32bit python.
      We reduce buffer size smaller to avoid memory_error.
      @see issue https://github.com/miurahr/py7zr/issues/370

    2. CPython
      CPython implementation of 3.7.5 fixed a lzma module bug
      that is not respect max_length parameter.
      When buffer size is larger than default of the module,
      max_length can be a value to lead the bug, so we set it
      lzma module default = 32768 bytes.
      @see BPO-21872: LZMA library sometimes fails to decompress a file
           https://bugs.python.org/issue21872
      @see https://github.com/miurahr/py7zr/issues/272

    3. PyPy
      PyPy 7.2 (python 3.6.9) fixed a lzma module's bug as same as
      CPython above.
      We set buffer size is as default size of the module to avoid the bugs.
      @see PyPy3-3090: lzma.LZMADecomporessor.decompress does not respect max_length
           https://foss.heptapod.net/pypy/pypy/-/issues/3090
      @see https://github.com/miurahr/py7zr/pull/114

    :return: recommended buffer size as int.
    """
    if is_64bit() and (is_pypy369later() or sys.version_info >= (3, 7, 5)):
        return 1048576
    else:
        return 32768


def get_memory_limit():
    """
    Get memory limit for allocating decompression chunk buffer.
    :return: allowed chunk size in bytes.
    """
    default_limit = int(128e6)
    if sys.platform.startswith("linux") or sys.platform.startswith("darwin") or sys.platform.startswith("openbsd"):
        import resource

        import psutil

        try:
            soft, _ = resource.getrlimit(resource.RLIMIT_DATA)
            if soft == -1:
                avmem = psutil.virtual_memory().available
                return min(default_limit, (avmem - int(256e6)) >> 2)
            else:
                return min(default_limit, (soft - int(256e6)) >> 2)
        except AttributeError:
            pass
    # fall back to default
    return default_limit


# Exposed constants
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
FILTER_PPMD = 0x36
FILTER_BROTLI = 0x37
FILTER_DEFLATE64 = 0x38


class Constant:
    """Constant base class."""

    def __setattr__(self, *_):
        pass


class DefaultFilters(Constant):
    """Default filter values."""

    ARCHIVE_FILTER = [{"id": FILTER_X86}, {"id": FILTER_LZMA2, "preset": 7 | PRESET_DEFAULT}]
    ENCODED_HEADER_FILTER = [{"id": FILTER_LZMA2, "preset": 7 | PRESET_DEFAULT}]
    ENCRYPTED_ARCHIVE_FILTER = [{"id": FILTER_LZMA2, "preset": 7 | PRESET_DEFAULT}, {"id": FILTER_CRYPTO_AES256_SHA256}]
    ENCRYPTED_HEADER_FILTER = [{"id": FILTER_CRYPTO_AES256_SHA256}]


DEFAULT_FILTERS = DefaultFilters()


class Property(Constant):
    """Hold 7zip property fixed values."""

    END = binascii.unhexlify("00")
    HEADER = binascii.unhexlify("01")
    ARCHIVE_PROPERTIES = binascii.unhexlify("02")
    ADDITIONAL_STREAMS_INFO = binascii.unhexlify("03")
    MAIN_STREAMS_INFO = binascii.unhexlify("04")
    FILES_INFO = binascii.unhexlify("05")
    PACK_INFO = binascii.unhexlify("06")
    UNPACK_INFO = binascii.unhexlify("07")
    SUBSTREAMS_INFO = binascii.unhexlify("08")
    SIZE = binascii.unhexlify("09")
    CRC = binascii.unhexlify("0a")
    FOLDER = binascii.unhexlify("0b")
    CODERS_UNPACK_SIZE = binascii.unhexlify("0c")
    NUM_UNPACK_STREAM = binascii.unhexlify("0d")
    EMPTY_STREAM = binascii.unhexlify("0e")
    EMPTY_FILE = binascii.unhexlify("0f")
    ANTI = binascii.unhexlify("10")
    NAME = binascii.unhexlify("11")
    CREATION_TIME = binascii.unhexlify("12")
    LAST_ACCESS_TIME = binascii.unhexlify("13")
    LAST_WRITE_TIME = binascii.unhexlify("14")
    ATTRIBUTES = binascii.unhexlify("15")
    COMMENT = binascii.unhexlify("16")
    ENCODED_HEADER = binascii.unhexlify("17")
    START_POS = binascii.unhexlify("18")
    DUMMY = binascii.unhexlify("19")


PROPERTY = Property()


class CompressionMethod(Constant):
    """Hold fixed values for method parameter."""

    COPY = binascii.unhexlify("00")
    DELTA = binascii.unhexlify("03")
    BCJ = binascii.unhexlify("04")
    PPC = binascii.unhexlify("05")
    IA64 = binascii.unhexlify("06")
    ARM = binascii.unhexlify("07")
    ARMT = binascii.unhexlify("08")
    SPARC = binascii.unhexlify("09")
    # SWAP = 02..
    SWAP2 = binascii.unhexlify("020302")
    SWAP4 = binascii.unhexlify("020304")
    # 7Z = 03..
    LZMA = binascii.unhexlify("030101")
    PPMD = binascii.unhexlify("030401")
    P7Z_BCJ = binascii.unhexlify("03030103")
    P7Z_BCJ2 = binascii.unhexlify("0303011B")
    BCJ_PPC = binascii.unhexlify("03030205")
    BCJ_IA64 = binascii.unhexlify("03030401")
    BCJ_ARM = binascii.unhexlify("03030501")
    BCJ_ARMT = binascii.unhexlify("03030701")
    BCJ_SPARC = binascii.unhexlify("03030805")
    LZMA2 = binascii.unhexlify("21")
    # MISC : 04..
    MISC_ZIP = binascii.unhexlify("0401")
    MISC_BZIP2 = binascii.unhexlify("040202")
    MISC_DEFLATE = binascii.unhexlify("040108")
    MISC_DEFLATE64 = binascii.unhexlify("040109")
    MISC_Z = binascii.unhexlify("0405")
    MISC_LZH = binascii.unhexlify("0406")
    NSIS_DEFLATE = binascii.unhexlify("040901")
    NSIS_BZIP2 = binascii.unhexlify("040902")
    #
    MISC_ZSTD = binascii.unhexlify("04f71101")
    MISC_BROTLI = binascii.unhexlify("04f71102")
    MISC_LZ4 = binascii.unhexlify("04f71104")
    MISC_LZS = binascii.unhexlify("04f71105")
    MISC_LIZARD = binascii.unhexlify("04f71106")
    # CRYPTO 06..
    CRYPT_ZIPCRYPT = binascii.unhexlify("06f10101")
    CRYPT_RAR29AES = binascii.unhexlify("06f10303")
    CRYPT_AES256_SHA256 = binascii.unhexlify("06f10701")


COMPRESSION_METHOD = CompressionMethod()
