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
import multiprocessing
import sys
from typing import IO, Any, BinaryIO, Dict, List, Optional, Union

from py7zr import UnsupportedCompressionMethodError
from py7zr.helpers import calculate_crc32
from py7zr.properties import CompressionMethod, Configuration

if sys.version_info < (3, 6):
    import pathlib2 as pathlib
else:
    import pathlib


class CopyDecompressor:

    def __init__(self) -> None:
        self.unused_data = b''

    @property
    def needs_input(self) -> bool:
        return True

    @property
    def eof(self) -> bool:
        return False

    def decompress(self, data: bytes, max_length: Optional[int] = None) -> bytes:
        if max_length is None:
            length = len(data)
        else:
            length = min(len(data), max_length)
        buf = self.unused_data + data
        self.unused_data = buf[length:]
        return buf[:length]


class Worker:
    """Extract worker class to invoke handler"""

    def __init__(self, files, src_start: int, header) -> None:
        self.target_filepath = {}  # type: Dict[int, Optional[pathlib.Path]]
        self.files = files
        self.src_start = src_start
        self.header = header

    def extract(self, fp: BinaryIO, multithread: bool = False) -> None:
        """Extract worker method to handle 7zip folder and decompress each files."""
        if multithread:
            numfolders = self.header.main_streams.unpackinfo.numfolders
            positions = self.header.main_streams.packinfo.packpositions
            folders = self.header.main_streams.unpackinfo.folders
            filename = getattr(fp, 'name', None)
            empty_files = [f for f in self.files if f.emptystream]
            self.extract_single(filename, empty_files, 0)
            extract_processes = []
            for i in range(numfolders):
                p = multiprocessing.Process(target=self.extract_single,
                                            args=(filename, folders[i].files,
                                                  self.src_start + positions[i]))
                p.start()
                extract_processes.append(p)
            for p in extract_processes:
                p.join()
        else:
            self.extract_single(fp, self.files, self.src_start)

    def extract_single(self, fp: Union[BinaryIO, str], files, src_start: int) -> None:
        """Single thread extractor that takes file lists in single 7zip folder."""
        if files is None:
            return
        if isinstance(fp, str):
            fp = open(fp, 'rb')
        fp.seek(src_start)
        for f in files:
            fileish = self.target_filepath.get(f.id, None)
            if fileish is not None:
                with fileish.open(mode='wb') as ofp:
                    if not f.emptystream:
                        self.decompress(fp, f.folder, ofp, f.uncompressed[-1], f.compressed)

    def decompress(self, fp: BinaryIO, folder, fq: IO[Any],
                   size: int, compressed_size: Optional[int]) -> None:
        """decompressor wrapper called from extract method.

           :parameter fp: archive source file pointer
           :parameter folder: Folder object that have decompressor object.
           :parameter fq: output file pathlib.Path
           :parameter size: uncompressed size of target file.
           :parameter compressed_size: compressed size of target file.
           :returns None
        """
        assert folder is not None
        out_remaining = size
        decompressor = folder.get_decompressor(compressed_size)
        while out_remaining > 0:
            max_length = min(out_remaining, io.DEFAULT_BUFFER_SIZE)
            if decompressor.needs_input:
                read_size = min(Configuration.get('read_blocksize'), decompressor.remaining_size)
                inp = fp.read(read_size)
                tmp = decompressor.decompress(inp, max_length)
            else:
                tmp = decompressor.decompress(b'', max_length)
            if len(tmp) > 0 and out_remaining >= len(tmp):
                out_remaining -= len(tmp)
                fq.write(tmp)
                if out_remaining <= 0:
                    break
        assert out_remaining == 0
        if decompressor.eof:
            if decompressor.crc is not None and not decompressor.check_crc():
                print('\nCRC error! expected: {}, real: {}'.format(decompressor.crc, decompressor.digest))
        return

    def archive(self, fp: BinaryIO, folder):
        """Run archive task for specified 7zip folder."""
        fp.seek(self.src_start)
        for f in self.files:
            if not f['emptystream']:
                filepath = self.target_filepath[f.id]
                if filepath is not None:
                    with filepath.open(mode='rb') as target:
                        length = self.compress(fp, folder, target)
                        f['compressed'] = length
            self.files.append(f)
        fp.flush()

    def compress(self, fp: BinaryIO, folder, fq: IO[Any]):
        """Compress specified file-ish into folder where fp placed."""
        compressor = folder.get_compressor()
        length = 0
        for indata in fq.read(Configuration.get('read_blocksize')):
            arcdata = compressor.compress(indata)
            folder.crc = calculate_crc32(arcdata, folder.crc)
            length += len(arcdata)
            fp.write(arcdata)
        arcdata = compressor.flush()
        folder.crc = calculate_crc32(arcdata, folder.crc)
        length += len(arcdata)
        fp.write(arcdata)
        return length

    def register_filelike(self, id: int, fileish: Optional[pathlib.Path]) -> None:
        """register file-ish to worker."""
        self.target_filepath[id] = fileish


class SevenZipDecompressor:
    """Main decompressor object which is properly configured and bind to each 7zip folder.
    because 7zip folder can have a custom compression method"""

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
    FILTER_COPY = 0x33
    FILTER_AES = 0x34
    alt_methods_map = {
        CompressionMethod.MISC_BZIP2: FILTER_BZIP2,
        CompressionMethod.COPY: FILTER_COPY,
    }

    def __init__(self, coders: List[Dict[str, Any]], size: int, crc: Optional[int]) -> None:
        self.input_size = size
        self.consumed = 0  # type: int
        self.crc = crc
        self.digest = None  # type: Optional[int]
        try:
            self._set_lzma_decompressor(coders)
        except UnsupportedCompressionMethodError:
            self._set_alternative_decompressor(coders)

    def _set_lzma_decompressor(self, coders: List[Dict[str, Any]]) -> None:
        filters = []  # type: List[Dict[str, Any]]
        for coder in coders:
            if coder['numinstreams'] != 1 or coder['numoutstreams'] != 1:
                raise UnsupportedCompressionMethodError('Only a simple compression method is currently supported.')
            filter_id = self.lzma_methods_map.get(coder['method'], None)
            if filter_id is None:
                raise UnsupportedCompressionMethodError
            properties = coder.get('properties', None)
            if properties is not None:
                filters[:0] = [lzma._decode_filter_properties(filter_id, properties)]  # type: ignore
            else:
                filters[:0] = [{'id': filter_id}]
        self.decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)  # type: Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, CopyDecompressor]  # noqa

    def _set_alternative_decompressor(self, coders: List[Dict[str, Any]]) -> None:
        filter_id = self.alt_methods_map.get(coders[0]['method'], None)
        if filter_id == self.FILTER_BZIP2:
            self.decompressor = bz2.BZ2Decompressor()
        elif filter_id == self.FILTER_COPY:
            self.decompressor = CopyDecompressor()
        else:
            raise UnsupportedCompressionMethodError

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
    """Main compressor object to configured for each 7zip folder."""

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
            if filter is None:
                break
            method = self.lzma_methods_map_r[filter['id']]
            properties = lzma._encode_filter_properties(filter)
            self.coders.append({'method': method, 'properties': properties, 'numinstreams': 1, 'numoutstreams': 1})

    def compress(self, data):
        return self.compressor.compress(data)

    def flush(self):
        return self.compressor.flush()


def get_methods_names(coders: List[dict]) -> List[str]:
    """Return human readable method names for specified coders"""
    methods_name_map = {
        CompressionMethod.LZMA2: "LZMA2",
        CompressionMethod.LZMA: "LZMA",
        CompressionMethod.DELTA: "delta",
    }
    methods_names = []  # type: List[str]
    for coder in coders:
        methods_names.append(methods_name_map[coder['method']])
    return methods_names
