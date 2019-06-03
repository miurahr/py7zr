#!/usr/bin/python -u
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
import bz2
import io
import lzma
import zlib

from py7zr import UnsupportedCompressionMethodError
from py7zr.helpers import calculate_crc32
from py7zr.properties import QUEUELEN, READ_BLOCKSIZE, CompressionMethod


class BufferHandler():

    def __init__(self, target):
        self.buf = target
        self.target = "memory buffer"

    def open(self):
        pass

    def write(self, data):
        self.buf.write(data)

    def read(self, size=None):
        if size is not None:
            return self.buf.read(size)
        else:
            return self.buf.read()

    def seek(self, offset, whence=1):
        self.buf.seek(offset, whence)

    def close(self):
        pass


class FileHandler():

    def __init__(self, target):
        self.target = target

    def open(self):
        self.fp = open(self.target, 'wb')

    def write(self, data):
        self.fp.write(data)

    def read(self, size=None):
        if size is not None:
            return self.fp.read(size)
        else:
            return self.fp.read()

    def seek(self, offset, whence=1):
        self.fp.seek(offset, whence)

    def close(self):
        self.fp.close()


class Worker():
    """Extract worker class to invoke handler"""

    def __init__(self, files, fp, src_start):
        self.target_filepath = {}
        self.files = files
        self.fp = fp
        self.src_start = src_start

    def set_output_filepath(self, index, func):
        self.target_filepath[index] = func

    def extract(self, fp):
        fp.seek(self.src_start)
        for f in self.files:
            # Skip empty file read
            if f.emptystream:
                fileish = self.target_filepath.get(f.id, None)
                if fileish is not None:
                    fileish.open()
                    fileish.write(b'')
                    fileish.close()
                continue
            # Does target path detected?
            fileish = self.target_filepath.get(f.id, None)
            if fileish is None:
                fileish = io.BytesIO()
                for s in f.uncompressed:
                    self.decompress(fp, f.folder, fileish, s, f.compressed)
                fileish.close()
                continue
            # retrieve contents
            fileish.open()
            self.decompress(fp, f.folder, fileish, f.uncompressed[-1], f.compressed)
            fileish.close()

    def decompress(self, fp, folder, fileish, size, compressed_size):
        if folder is None:
            fileish.write(b'')
            return
        out_remaining = size
        decompressor = folder.get_decompressor(compressed_size)
        queue = folder.queue
        queue_maxlength = QUEUELEN
        if queue.len > 0:
            if out_remaining > queue.len:
                out_remaining -= queue.len
                fileish.write(queue.dequeue(queue.len))
            else:
                fileish.write(queue.dequeue(out_remaining))
                return

        while out_remaining > 0:
            if not decompressor.eof:
                if decompressor.needs_input:
                    read_size = min(READ_BLOCKSIZE, decompressor.remaining_size)
                    inp = fp.read(read_size)
                else:
                    inp = b''
                max_length = min(out_remaining, queue_maxlength - queue.len)
                tmp = decompressor.decompress(inp, max_length)
                if out_remaining >= len(tmp):
                    out_remaining -= len(tmp)
                    fileish.write(tmp)
                    if out_remaining <= 0:
                        break
                else:
                    queue.enqueue(tmp)
                    fileish.write(queue.dequeue(out_remaining))
                    break
            else:
                if queue.len < out_remaining:
                    print('\nAbort: Something become wrong!')
                    raise
                if queue.len > 0:
                    fileish.write(queue.dequeue(out_remaining))
                break
        return

    def archive(self, fp, folder):
        fp.seek(self.src_start)
        for f in self.files:
            if not f['emptystream']:
                target = self.target_filepath.get(f.id, None)
                target.open()
                length = self.compress(fp, folder, target)
                target.close()
                f['compressed'] = length
            self.files.append(f)
        fp.flush()

    def compress(self, fp, folder, f):
        compressor = folder.get_compressor()
        length = 0
        for indata in f.read(READ_BLOCKSIZE):
            arcdata = compressor.compress(indata)
            folder.crc = calculate_crc32(arcdata, folder.crc)
            length += len(arcdata)
            fp.write(arcdata)
        arcdata = compressor.flush()
        folder.crc = calculate_crc32(arcdata, folder.crc)
        length += len(arcdata)
        fp.write(arcdata)
        return length

    def register_filelike(self, id, fileish):
        if isinstance(fileish, io.BytesIO):
            self.set_output_filepath(id, BufferHandler(fileish))
        else:
            self.set_output_filepath(id, FileHandler(fileish))


class SevenZipDecompressor:

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

    FILTER_BZIP2 = 0x31
    FILTER_ZIP = 0x32
    alt_methods_map = {
        CompressionMethod.MISC_BZIP2: FILTER_BZIP2,
        CompressionMethod.MISC_ZIP: FILTER_ZIP,
    }

    @property
    def needs_input(self):
        return self.decompressor.needs_input

    @property
    def eof(self):
        return self.decompressor.eof

    def decompress(self, data, max_length=None):
        self.consumed += len(data)
        if max_length is not None:
            return self.decompressor.decompress(data, max_length=max_length)
        else:
            return self.decompressor.decompress(data)

    @property
    def unused_data(self):
        return self.decompressor.unused_data

    @property
    def remaining_size(self):
        return self.input_size - self.consumed

    def __init__(self, coders, size):
        self.decompressor = None
        self.input_size = size
        self.consumed = 0
        filters = []
        try:
            for coder in coders:
                if coder['numinstreams'] != 1 or coder['numoutstreams'] != 1:
                    raise UnsupportedCompressionMethodError('Only a simple compression method is currently supported.')
                filter = self.lzma_methods_map.get(coder['method'], None)
                if filter is not None:
                    properties = coder.get('properties', None)
                    if properties is not None:
                        filters[:0] = [lzma._decode_filter_properties(filter, properties)]
                    else:
                        filters[:0] = [{'id': filter}]
                else:
                    raise UnsupportedCompressionMethodError
        except UnsupportedCompressionMethodError as e:
            filter = self.alt_methods_map.get(coders[0]['method'], None)
            if len(coders) == 1 and filter is not None:
                if filter == self.FILTER_BZIP2:
                    self.decompressor = bz2.BZ2Decompressor()
                elif filter == self.FILTER_ZIP:
                    self.decompressor = zlib.decompressobj(-15)
                self.can_partial_decompress = False
            else:
                raise e
        else:
            self.decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
            self.can_partial_decompress = True
        self.filters = filters


class SevenZipCompressor():

    __slots__ = ['filters', 'compressor', 'coders']

    lzma_methods_map_r = {
        lzma.FILTER_LZMA2: CompressionMethod.LZMA2,
        lzma.FILTER_DELTA: CompressionMethod.DELTA,
        lzma.FILTER_X86: CompressionMethod.P7Z_BCJ,
    }

    def __init__(self, filters=None):
        if filters is None:
            self.filters = [{"id": lzma.FILTER_LZMA2, "preset": 7 | lzma.PRESET_EXTREME}, ]
        else:
            self.filters = filters
        self.compressor = lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=self.filters)
        self.coders = []
        for filter in self.filters:
            method = self.lzma_methods_map_r[filter['id']]
            properties = lzma._encode_filter_properties(filter)
            self.coders.append({'method': method, 'properties': properties, 'numinstreams': 1, 'numoutstreams': 1})

    def compress(self, data):
        return self.compressor.compress(data)

    def flush(self):
        return self.compressor.flush()
