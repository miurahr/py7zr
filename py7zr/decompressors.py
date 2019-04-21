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
#

import io
import lzma
import bz2
import zlib

from py7zr.exceptions import UnsupportedCompressionMethodError, DecompressionError
from py7zr.properties import CompressionMethod, READ_BLOCKSIZE, QUEUELEN

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


def get_decompressor(coders, unpacksize=None):
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
                decompressor = DecompressorCopy(unpacksize)
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
    def needs_input(self):
        return self.remaining > 0

    @property
    def eof(self):
        return self.remaining <= 0


class BufferWriter():

    def __init__(self, target):
        self.buf = target

    def write(self, data):
        self.buf.write(data)

    def flush(self):
        pass

    def close(self):
        self.buf.close()


class FileWriter():

    def __init__(self, target):
        self.fp = io.BufferedWriter(target)

    def write(self, data):
        self.fp.write(data)

    def flush(self):
        self.fp.flush()

    def close(self):
        self.fp.close()


class Worker():
    """Extract worker class to invoke handler"""

    def __init__(self, files, fp, src_start):
        self.handler = {}
        self.files = files
        self.fp = fp
        self.src_start = src_start

    def register_writer(self, index, func):
        self.handler[index] = func

    def extract(self, fp):
        fp.seek(self.src_start)
        for f in self.files:
            handler = self.handler.get(f.id, None)
            if f.emptystream:
                continue
            else:
                folder = f.folder
                sizes = f.uncompressed
                for s in sizes:
                    self.decompress(fp, folder, handler, s)

    def close(self):
        for f in self.files:
            handler = self.handler.get(f.id, None)
            if handler is not None:
                handler.close()

    def decompress(self, fp, folder, data, size):
        if folder is None:
            return b''
        out_remaining = size
        decompressor = folder.decompressor
        queue = folder.queue
        queue_maxlength = QUEUELEN
        if queue.len > 0:
            if out_remaining > queue.len:
                out_remaining -= queue.len
                data.write(queue.dequeue(queue.len))
            else:
                data.write(queue.dequeue(out_remaining))
                return

        while out_remaining > 0:
            if decompressor.needs_input:
                inp = fp.read(READ_BLOCKSIZE)
            else:
                inp = b''
            if not decompressor.eof:
                max_length = min(out_remaining, queue_maxlength - queue.len)
                tmp = decompressor.decompress(inp, max_length)
                if out_remaining > len(tmp):
                    data.write(tmp)
                    out_remaining -= len(tmp)
                else:
                    queue.enqueue(tmp)
                    data.write(queue.dequeue(out_remaining))
                    break
            else:
                raise DecompressionError("Corrupted data")
        return

    def register_filelike(self, id, fileish):
        if isinstance(fileish, io.BytesIO):
            self.register_writer(id, BufferWriter(fileish))
        else:
            self.register_writer(id, FileWriter(fileish))
