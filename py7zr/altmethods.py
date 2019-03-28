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


from py7zr.exceptions import DecompressionError, UnsupportedCompressionMethodError
import bz2
import zlib

FILTER_COPY = 1
FILTER_BZIP2 = 2
FILTER_ZIP = 3


def get_compressor(filter=None):
    if filter == FILTER_BZIP2:
        return bz2.BZ2Decompressor()
    elif filter == FILTER_ZIP:
        return zlib.decompressobj(-15)
    elif filter == FILTER_COPY:
        return DecompressorCopy(100)
    else:
        raise UnsupportedCompressionMethodError


class DecompressorCopy():

    def __init__(self, total):
        self.remaining = total

    def decompress(self, data, max_length=None):
        self.remaining -= len(data)
        return data

    @property
    def need_input(self):
        return self.remaining > 0

    @property
    def eof(self):
        return self.remaining <= 0

