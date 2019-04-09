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


from py7zr.exceptions import UnsupportedCompressionMethodError
from py7zr.properties import CompressionMethod
import lzma
import bz2
import zlib

FILTER_COPY = 1
FILTER_BZIP2 = 2
FILTER_ZIP = 3

lzma_methods_map = {
    CompressionMethod.LZMA: lzma.FILTER_LZMA1,
    CompressionMethod.LZMA2: lzma.FILTER_LZMA2,
    CompressionMethod.DELTA: lzma.FILTER_DELTA,
    CompressionMethod.BCJ: lzma.FILTER_X86,
    CompressionMethod.BCJ_ARM: lzma.FILTER_ARM,
    CompressionMethod.BCJ_ARMT: lzma.FILTER_ARMTHUMB,
    CompressionMethod.BCJ_IA64: lzma.FILTER_IA64,
    CompressionMethod.BCJ_PPC: lzma.FILTER_POWERPC,
    CompressionMethod.BCJ_SPARC: lzma.FILTER_SPARC,
}
alt_methods_map = {
    CompressionMethod.COPY: FILTER_COPY,
    CompressionMethod.MISC_BZIP2: FILTER_BZIP2,
    CompressionMethod.MISC_ZIP: FILTER_ZIP,
}


def get_decompressor(coders):
    decompressor = None
    filters = []
    try:
        for coder in coders:
            filter = lzma_methods_map.get(coder['method'], None)
            if filter is not None:
                properties = coder.get('properties', None)
                if properties is not None:
                    filters.append(lzma._decode_filter_properties(filter, properties))
                else:
                    filters.append({'id': filter})
            else:
                raise UnsupportedCompressionMethodError
    except UnsupportedCompressionMethodError as e:
        filter = alt_methods_map.get(coders[0]['method'], None)
        if len(coders) == 1 and filter is not None:
            if filter == FILTER_BZIP2:
                decompressor = bz2.BZ2Decompressor()
            elif filter == FILTER_ZIP:
                decompressor = zlib.decompressobj(-15)
            elif filter == FILTER_COPY:
                decompressor = DecompressorCopy(100)
            can_partial_decompress = False
        else:
            raise e
    else:
        decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
        can_partial_decompress = True
    return decompressor, can_partial_decompress


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
