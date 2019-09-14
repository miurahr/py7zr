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
import concurrent.futures
import io
import lzma
from io import BytesIO
from typing import Any, BinaryIO, Dict, List, Optional, Union

from py7zr import UnsupportedCompressionMethodError
from py7zr.helpers import calculate_crc32
from py7zr.properties import CompressionMethod, Configuration


class NullHandler():
    '''Null handler pass to null the data.'''

    def __init__(self):
        pass

    def open(self):
        pass

    def write(self, t):
        pass

    def read(self, size):
        return b''

    def seek(self, offset, whence=1):
        pass

    def close(self):
        pass


class BufferHandler():
    '''Buffer handler handles BytesIO/StringIO buffers.'''

    def __init__(self, target: BytesIO) -> None:
        self.buf = target
        self.target = "memory buffer"

    def open(self) -> None:
        pass

    def write(self, data: bytes) -> None:
        self.buf.write(data)

    def read(self, size=None):
        if size is not None:
            return self.buf.read(size)
        else:
            return self.buf.read()

    def seek(self, offset, whence=1):
        self.buf.seek(offset, whence)

    def close(self) -> None:
        pass


class FileHandler():
    '''File handler treat fileish object'''

    def __init__(self, target: str) -> None:
        self.target = target

    def open(self) -> None:
        self.fp = open(self.target, 'wb')

    def write(self, data: bytes) -> None:
        self.fp.write(data)

    def read(self, size=None):
        if size is not None:
            return self.fp.read(size)
        else:
            return self.fp.read()

    def seek(self, offset, whence=1):
        self.fp.seek(offset, whence)

    def close(self) -> None:
        self.fp.close()


Handler = Union[NullHandler, BufferHandler, FileHandler]


class Worker:
    """Extract worker class to invoke handler"""

    def __init__(self, files, src_start: int, header) -> None:
        self.target_filepath = {}  # type: Dict[int, Handler]
        self.files = files
        self.src_start = src_start
        self.header = header

    def set_output_filepath(self, index: int, func: Handler) -> None:
        self.target_filepath[index] = func

    def extract(self, fp: BinaryIO, multithread: bool = False) -> None:
        if multithread:
            numfolders = self.header.main_streams.unpackinfo.numfolders
            positions = self.header.main_streams.packinfo.packpositions
            folders = self.header.main_streams.unpackinfo.folders
            filename = getattr(fp, 'name', None)
            empty_files = [f for f in self.files if f.emptystream]
            with concurrent.futures.ThreadPoolExecutor() as executor:
                threads = []
                threads.append(executor.submit(self.extract_single, open(filename, 'rb'),
                                               empty_files, 0))
                for i in range(numfolders):
                    threads.append(executor.submit(self.extract_single, open(filename, 'rb'),
                                                   folders[i].files, self.src_start + positions[i]))
                for future in concurrent.futures.as_completed(threads):
                    try:
                        future.result()
                    except Exception as e:
                        raise e
        else:
            self.extract_single(fp, self.files, self.src_start)

    def extract_single(self, fp: BinaryIO, files, src_start: int) -> None:
        fp.seek(src_start)
        for f in files:
            fileish = self.target_filepath.get(f.id, NullHandler())  # type: Handler
            fileish.open()
            # Skip empty file read
            if f.emptystream:
                fileish.write(b'')
            else:
                self.decompress(fp, f.folder, fileish, f.uncompressed[-1], f.compressed)
            fileish.close()

    def decompress(self, fp: BinaryIO, folder, fileish: Handler,
                   size: int, compressed_size: Optional[int]) -> None:
        assert folder is not None
        out_remaining = size
        decompressor = folder.get_decompressor(compressed_size)
        while out_remaining > 0:
            if not decompressor.eof:
                max_length = min(out_remaining, Configuration.get('read_blocksize'))
                if decompressor.needs_input:
                    read_size = min(Configuration.get('read_blocksize'), decompressor.remaining_size)
                    inp = fp.read(read_size)
                    tmp = decompressor.decompress(inp, max_length)
                else:
                    tmp = decompressor.decompress(b'', max_length)
                if out_remaining >= len(tmp):
                    out_remaining -= len(tmp)
                    fileish.write(tmp)
                    if out_remaining <= 0:
                        break
            else:
                break
        if decompressor.eof:
            if decompressor.crc is not None and not decompressor.check_crc():
                print('\nCRC error! expected: {}, real: {}'.format(decompressor.crc, decompressor.digest))
        return

    def archive(self, fp: BinaryIO, folder):
        fp.seek(self.src_start)
        for f in self.files:
            if not f['emptystream']:
                target = self.target_filepath.get(f.id, NullHandler())  # type: Handler
                target.open()
                length = self.compress(fp, folder, target)
                target.close()
                f['compressed'] = length
            self.files.append(f)
        fp.flush()

    def compress(self, fp: BinaryIO, folder, f: Handler):
        compressor = folder.get_compressor()
        length = 0
        for indata in f.read(Configuration.get('read_blocksize')):
            arcdata = compressor.compress(indata)
            folder.crc = calculate_crc32(arcdata, folder.crc)
            length += len(arcdata)
            fp.write(arcdata)
        arcdata = compressor.flush()
        folder.crc = calculate_crc32(arcdata, folder.crc)
        length += len(arcdata)
        fp.write(arcdata)
        return length

    def register_filelike(self, id: int, fileish: Union[BinaryIO, str, None]) -> None:
        if fileish is None:
            self.set_output_filepath(id, NullHandler())
        elif isinstance(fileish, io.BytesIO):
            self.set_output_filepath(id, BufferHandler(fileish))
        elif isinstance(fileish, str):
            self.set_output_filepath(id, FileHandler(fileish))
        else:
            raise


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
    }

    def __init__(self, coders: List[Dict[str, Any]], size: int, crc: Optional[int]) -> None:
        self.input_size = size
        self.consumed = 0  # type: int
        self.crc = crc
        self.digest = None  # type: Optional[int]
        filters = []  # type: List[Dict[str, Any]]
        try:
            for coder in coders:
                if coder['numinstreams'] != 1 or coder['numoutstreams'] != 1:
                    raise UnsupportedCompressionMethodError('Only a simple compression method is currently supported.')
                filter = self.lzma_methods_map.get(coder['method'], None)
                if filter is not None:
                    properties = coder.get('properties', None)
                    if properties is not None:
                        filters[:0] = [lzma._decode_filter_properties(filter, properties)]  # type: ignore
                    else:
                        filters[:0] = [{'id': filter}]
                else:
                    raise UnsupportedCompressionMethodError
        except UnsupportedCompressionMethodError as e:
            filter = self.alt_methods_map.get(coders[0]['method'], None)
            if len(coders) == 1 and filter is not None:
                if filter == self.FILTER_BZIP2:
                    self.decompressor = bz2.BZ2Decompressor()  # type: Union[bz2.BZ2Decompressor, lzma.LZMADecompressor]
                else:
                    raise e
                self.can_partial_decompress = False
            else:
                raise e
        else:
            self.decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
            self.can_partial_decompress = True
        self.filters = filters

    @property
    def needs_input(self) -> bool:
        return self.decompressor.needs_input

    @property
    def eof(self) -> bool:
        return self.decompressor.eof

    def decompress(self, data: bytes, max_length: Optional[int] = None) -> bytes:
        self.consumed += len(data)
        if max_length is not None:
            folder_data = self.decompressor.decompress(data, max_length=max_length)
        else:
            folder_data = self.decompressor.decompress(data)
        # calculate CRC with uncompressed data
        if self.crc is not None:
            self.digest = calculate_crc32(folder_data, self.digest)
        return folder_data

    @property
    def unused_data(self):
        return self.decompressor.unused_data

    @property
    def remaining_size(self) -> int:
        return self.input_size - self.consumed

    def check_crc(self):
        return self.crc == self.digest


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


def get_methods_names(coders: List[dict]) -> List[str]:
    methods_name_map = {
        CompressionMethod.LZMA2: "LZMA2",
        CompressionMethod.LZMA: "LZMA",
        CompressionMethod.DELTA: "delta",
    }
    methods_names = []
    for coder in coders:
        methods_names.append(methods_name_map[coder['method']])
    return methods_names
