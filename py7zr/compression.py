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
import sys
from io import BytesIO
from typing import Any, BinaryIO, Dict, List, Optional, Union

from Crypto.Cipher import AES
from py7zr import DecompressionError, UnsupportedCompressionMethodError
from py7zr.helpers import calculate_crc32, calculate_key
from py7zr.properties import READ_BLOCKSIZE, ArchivePassword, CompressionMethod

if sys.version_info < (3, 6):
    import pathlib2 as pathlib
else:
    import pathlib


class NullHandler():
    '''Null handler pass to null the data.'''

    def __init__(self):
        pass

    def open(self, mode=None):
        pass

    def write(self, t):
        pass

    def read(self, size):
        return b''

    def seek(self, offset, whence=1):
        pass

    def truncate(self, size):
        pass

    def close(self):
        pass

    def stat(self):
        return None


class BufferHandler():
    '''Buffer handler handles BytesIO/StringIO buffers.'''

    def __init__(self, target: BytesIO) -> None:
        self.buf = target
        self.target = "memory buffer"

    def open(self, mode=None) -> None:
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

    def truncate(self, size):
        pass

    def close(self) -> None:
        pass

    def stat(self):
        return None


class FileHandler():
    '''File handler treat fileish object'''

    def __init__(self, target: pathlib.Path) -> None:
        self.target = target

    def open(self, mode='wb') -> None:
        self.fp = self.target.open(mode=mode)

    def write(self, data: bytes) -> None:
        self.fp.write(data)

    def read(self, size=None):
        if size is not None:
            return self.fp.read(size)
        else:
            return self.fp.read()

    def seek(self, offset, whence=1):
        self.fp.seek(offset, whence)

    def truncate(self, size=None):
        self.fp.truncate(size)

    def close(self) -> None:
        self.fp.close()

    def stat(self):
        return self.target.stat()


Handler = Union[NullHandler, BufferHandler, FileHandler]


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


class AESDecompressor:

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

    def __init__(self, aes_properties: bytes, password: str, coders: List[Dict[str, Any]]) -> None:
        byte_password = password.encode('utf-16LE')
        firstbyte = aes_properties[0]
        numcyclespower = firstbyte & 0x3f
        if firstbyte & 0xc0 != 0:
            saltsize = (firstbyte >> 7) & 1
            ivsize = (firstbyte >> 6) & 1
            secondbyte = aes_properties[1]
            saltsize += (secondbyte >> 4)
            ivsize += (secondbyte & 0x0f)
            assert len(aes_properties) == 2 + saltsize + ivsize
            salt = aes_properties[2:2 + saltsize]
            iv = aes_properties[2 + saltsize:2 + saltsize + ivsize]
            assert len(salt) == saltsize
            assert len(iv) == ivsize
            assert numcyclespower <= 24
            if ivsize < 16:
                iv += bytes('\x00' * (16 - ivsize), 'ascii')
            key = calculate_key(byte_password, numcyclespower, salt, 'sha256')
            self.lzma_decompressor = self._set_lzma_decompressor(coders)
            self.cipher = AES.new(key, AES.MODE_CBC, iv)
            self.buf = b''
            self.flushed = False
        else:
            raise UnsupportedCompressionMethodError

    # set pipeline decompressor
    def _set_lzma_decompressor(self, coders: List[Dict[str, Any]]):
        filters = []  # type: List[Dict[str, Any]]
        for coder in coders:
            filter = self.lzma_methods_map.get(coder['method'], None)
            if filter is not None:
                properties = coder.get('properties', None)
                if properties is not None:
                    filters[:0] = [lzma._decode_filter_properties(filter, properties)]  # type: ignore
                else:
                    filters[:0] = [{'id': filter}]
            else:
                raise UnsupportedCompressionMethodError
        return lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)

    @property
    def needs_input(self) -> bool:
        return self.lzma_decompressor.needs_input

    @property
    def eof(self) -> bool:
        return self.lzma_decompressor.eof

    def decompress(self, data: bytes, max_length: Optional[int] = None) -> bytes:
        if len(data) == 0 and len(self.buf) == 0:  # action flush
            return self.lzma_decompressor.decompress(b'', max_length)
        elif len(data) == 0:  # action padding
            self.flushded = True
            padlen = 16 - len(self.buf) % 16
            inp = self.buf + bytes(padlen)
            self.buf = b''
            temp = self.cipher.decrypt(inp)
            return self.lzma_decompressor.decompress(temp, max_length)
        else:
            compdata = self.buf + data
            currentlen = len(compdata)
            a = currentlen // 16
            nextpos = a * 16
            if currentlen == nextpos:
                self.buf = b''
                temp = self.cipher.decrypt(compdata)
                return self.lzma_decompressor.decompress(temp, max_length)
            else:
                self.buf = compdata[nextpos:]
                assert len(self.buf) < 16
                temp = self.cipher.decrypt(compdata[:nextpos])
                return self.lzma_decompressor.decompress(temp, max_length)

    @property
    def unused_data(self):
        return self.buf


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
        """Extract worker method to handle 7zip folder and decompress each files."""
        if hasattr(self.header, 'main_streams') and self.header.main_streams is not None:
            if not multithread:
                src_end = self.src_start + self.header.main_streams.packinfo.packpositions[-1]
                self.extract_single(fp, self.files, self.src_start, src_end)
            else:
                numfolders = self.header.main_streams.unpackinfo.numfolders
                folders = self.header.main_streams.unpackinfo.folders
                filename = getattr(fp, 'name', None)
                empty_files = [f for f in self.files if f.emptystream]
                positions = self.header.main_streams.packinfo.packpositions
                self.extract_single(open(filename, 'rb'), empty_files, 0, 0)
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    threads = []
                    for i in range(numfolders):
                        threads.append(executor.submit(self.extract_single, open(filename, 'rb'),
                                                       folders[i].files, self.src_start + positions[i],
                                                       self.src_start + positions[i + 1]))
                    for future in concurrent.futures.as_completed(threads):
                        try:
                            future.result()
                        except Exception as e:
                            raise e
        else:
            empty_files = [f for f in self.files if f.emptystream]
            self.extract_single(fp, empty_files, 0, 0)

    def extract_single(self, fp: BinaryIO, files, src_start: int, src_end: int) -> None:
        """Single thread extractor that takes file lists in single 7zip folder."""
        if files is None:
            return
        fp.seek(src_start)
        for f in files:
            fileish = self.target_filepath.get(f.id, NullHandler())  # type: Handler
            fileish.open()
            # Skip empty file read
            if f.emptystream:
                fileish.write(b'')
            else:
                self.decompress(fp, f.folder, fileish, f.uncompressed[-1], f.compressed, src_end)
            fileish.close()

    def decompress(self, fp: BinaryIO, folder, fileish: Handler,
                   size: int, compressed_size: Optional[int], src_end: int) -> None:
        """decompressor wrapper called from extract method.

           :parameter fp: archive source file pointer
           :parameter folder: Folder object that have decompressor object.
           :parameter fileish: output file Handler, BufferHandler, FileHandler or NullHandler
           :parameter size: uncompressed size of target file.
           :parameter compressed_size: compressed size of target file.
           :parameter src_end: end position of the folder
           :returns None
        """
        assert folder is not None
        out_remaining = size
        decompressor = folder.get_decompressor(compressed_size)
        while out_remaining > 0:
            max_length = min(out_remaining, io.DEFAULT_BUFFER_SIZE)
            rest_size = src_end - fp.tell()
            read_size = min(READ_BLOCKSIZE, rest_size)
            if read_size == 0:
                tmp = decompressor.decompress(b'', max_length)
            else:
                inp = fp.read(read_size)
                tmp = decompressor.decompress(inp, max_length)
            if len(tmp) == 0:
                raise DecompressionError
            if out_remaining >= len(tmp):
                out_remaining -= len(tmp)
                fileish.write(tmp)
                if out_remaining <= 0:
                    break
        assert out_remaining == 0
        if fp.tell() >= src_end:
            if decompressor.crc is not None and not decompressor.check_crc():
                print('\nCRC error! expected: {}, real: {}'.format(decompressor.crc, decompressor.digest))
        return

    def archive(self, fp: BinaryIO, folder):
        """Run archive task for specified 7zip folder."""
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
        """Compress specified file-ish into folder where fp placed."""
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

    def register_filelike(self, id: int, fileish: Union[pathlib.Path, BinaryIO, None]) -> None:
        """register file-ish to worker. File-ish can be union of BinaryIO, str and None.
        When BytesIO specified use BufferHandler. When None use NullHandler, and
        and str is recognized as a path."""
        if fileish is None:
            self.set_output_filepath(id, NullHandler())
        elif isinstance(fileish, io.BytesIO):
            self.set_output_filepath(id, BufferHandler(fileish))
        elif isinstance(fileish, pathlib.Path):
            self.set_output_filepath(id, FileHandler(fileish))
        else:
            raise


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
        CompressionMethod.CRYPT_AES256_SHA256: FILTER_AES,
    }

    def __init__(self, coders: List[Dict[str, Any]], size: int, crc: Optional[int]) -> None:
        # Get password which was set when creation of py7zr.SevenZipFile object.
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
        self.decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)  # type: Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, AESDecompressor, CopyDecompressor]  # noqa

    def _set_alternative_decompressor(self, coders: List[Dict[str, Any]]) -> None:
        filter_id = self.alt_methods_map.get(coders[0]['method'], None)
        if filter_id == self.FILTER_BZIP2:
            self.decompressor = bz2.BZ2Decompressor()
        elif filter_id == self.FILTER_COPY:
            self.decompressor = CopyDecompressor()
        elif filter_id == self.FILTER_AES:
            password = ArchivePassword().get()
            properties = coders[0].get('properties', None)
            self.decompressor = AESDecompressor(properties, password, coders[1:])
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
