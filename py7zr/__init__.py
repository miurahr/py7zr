#!/usr/bin/env python
#
#    Pure python p7zr implementation
#    Copyright (C) 2019 Hiroshi Miura
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

try:
    from importlib.metadata import PackageNotFoundError, version  # type: ignore
except ImportError:
    from importlib_metadata import PackageNotFoundError, version  # type: ignore

from py7zr.exceptions import Bad7zFile, DecompressionError, UnsupportedCompressionMethodError
from py7zr.properties import (CHECK_CRC32, CHECK_CRC64, CHECK_NONE, CHECK_SHA256, FILTER_ARM, FILTER_ARMTHUMB, FILTER_BZIP2,
                              FILTER_COPY, FILTER_CRYPTO_AES256_SHA256, FILTER_DEFLATE, FILTER_DELTA, FILTER_IA64,
                              FILTER_LZMA, FILTER_LZMA2, FILTER_POWERPC, FILTER_SPARC, FILTER_X86, FILTER_ZSTD,
                              PRESET_DEFAULT, PRESET_EXTREME)
from py7zr.py7zr import ArchiveInfo, FileInfo, SevenZipFile, is_7zfile, pack_7zarchive, unpack_7zarchive

__copyright__ = 'Copyright (C) 2019,2020 Hiroshi Miura'

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no-cover
    # package is not installed
    __version__ = "unknown"

__all__ = ['__version__', 'ArchiveInfo', 'FileInfo', 'SevenZipFile', 'is_7zfile', 'pack_7zarchive', 'unpack_7zarchive',
           'UnsupportedCompressionMethodError', 'Bad7zFile', 'DecompressionError',
           'FILTER_LZMA', 'FILTER_LZMA2', 'FILTER_DELTA', 'FILTER_COPY', 'FILTER_CRYPTO_AES256_SHA256',
           'FILTER_X86', 'FILTER_ARM', 'FILTER_SPARC', 'FILTER_POWERPC', 'FILTER_IA64', 'FILTER_ARMTHUMB',
           'FILTER_BZIP2', 'FILTER_DEFLATE', 'FILTER_ZSTD',
           'CHECK_SHA256', 'CHECK_CRC64', 'CHECK_CRC32', 'CHECK_NONE', 'PRESET_DEFAULT', 'PRESET_EXTREME']
