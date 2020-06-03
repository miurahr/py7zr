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
import lzma
import zlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

from Crypto.Cipher import AES

from py7zr import UnsupportedCompressionMethodError
from py7zr.helpers import Buffer, calculate_key
from py7zr.properties import READ_BLOCKSIZE, ArchivePassword, CompressionMethod

try:
    import zstandard as Zstd  # type: ignore
except ImportError:
    Zstd = None


class ISevenZipCompressor(ABC):
    @abstractmethod
    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        pass

    @abstractmethod
    def flush(self) -> bytes:
        pass


class ISevenZipDecompressor(ABC):
    @abstractmethod
    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        pass


class DeflateDecompressor(ISevenZipDecompressor):
    def __init__(self):
        self.buf = b''
        self._decompressor = zlib.decompressobj(-15)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1):
        if max_length < 0:
            res = self.buf + self._decompressor.decompress(data)
            self.buf = b''
        else:
            tmp = self.buf + self._decompressor.decompress(data)
            res = tmp[:max_length]
            self.buf = tmp[max_length:]
        return res


class CopyDecompressor(ISevenZipDecompressor):

    def __init__(self):
        self._buf = bytes()

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        if max_length < 0:
            length = len(data)
        else:
            length = min(len(data), max_length)
        buflen = len(self._buf)
        if length > buflen:
            res = self._buf + data[:length - buflen]
            self._buf = data[length - buflen:]
        else:
            res = self._buf[:length]
            self._buf = self._buf[length:] + data
        return res


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


def check_lzma_coders(coders: List[Dict[str, Any]]) -> bool:
    res = True
    for coder in coders:
        if lzma_methods_map.get(coder['method'], None) is None:
            res = False
            break
    return res


def get_lzma_decompressor(coders: List[Dict[str, Any]]):
    filters = []  # type: List[Dict[str, Any]]
    for coder in coders:
        if coder['numinstreams'] != 1 or coder['numoutstreams'] != 1:
            raise UnsupportedCompressionMethodError('Only a simple compression method is currently supported.')
        filter_id = lzma_methods_map.get(coder['method'], None)
        if filter_id is None:
            raise UnsupportedCompressionMethodError
        properties = coder.get('properties', None)
        if properties is not None:
            filters[:0] = [lzma._decode_filter_properties(filter_id, properties)]  # type: ignore
        else:
            filters[:0] = [{'id': filter_id}]
    return lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)


FILTER_BZIP2 = 0x31
FILTER_ZIP = 0x32
FILTER_COPY = 0x33
FILTER_AES = 0x34
FILTER_ZSTD = 0x35
alt_methods_map = {
    CompressionMethod.MISC_BZIP2: FILTER_BZIP2,
    CompressionMethod.MISC_DEFLATE: FILTER_ZIP,
    CompressionMethod.COPY: FILTER_COPY,
    CompressionMethod.CRYPT_AES256_SHA256: FILTER_AES,
    CompressionMethod.MISC_ZSTD: FILTER_ZSTD,
}


def get_alternative_decompressor(coders: List[Dict[str, Any]]):
    filter_id = alt_methods_map.get(coders[0]['method'], None)
    if filter_id == FILTER_BZIP2:
        decompressor = bz2.BZ2Decompressor()
    elif filter_id == FILTER_ZIP:
        decompressor = DeflateDecompressor()
    elif filter_id == FILTER_COPY:
        decompressor = CopyDecompressor()
    elif filter_id == FILTER_ZSTD and Zstd:
        decompressor = ZstdDecompressor()
    elif filter_id == FILTER_AES:
        password = ArchivePassword().get()
        properties = coders[0].get('properties', None)
        decompressor = AESDecompressor(properties, password, coders[1:])
    else:
        raise UnsupportedCompressionMethodError
    return decompressor


class AESDecompressor(ISevenZipDecompressor):

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
            if len(coders) == 0:
                self._decompressor = CopyDecompressor()  # type: Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, ISevenZipDecompressor]  # noqa
            else:
                try:
                    self._decompressor = get_lzma_decompressor(coders)
                except UnsupportedCompressionMethodError:
                    self._decompressor = get_alternative_decompressor(coders)

            self.cipher = AES.new(key, AES.MODE_CBC, iv)
            self.buf = Buffer(size=READ_BLOCKSIZE + 16)
            self.flushed = False
        else:
            raise UnsupportedCompressionMethodError

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        if len(data) == 0 and len(self.buf) == 0:  # action flush
            return self._decompressor.decompress(b'', max_length)
        elif len(data) == 0:  # action padding
            self.flushded = True
            # align = 16
            # padlen = (align - offset % align) % align
            #       = (align - (offset & (align - 1))) & (align - 1)
            #       = -offset & (align -1)
            #       = -offset & (16 - 1) = -offset & 15
            padlen = -len(self.buf) & 15
            self.buf.add(bytes(padlen))
            temp = self.cipher.decrypt(self.buf.view)  # type: bytes
            self.buf.reset()
            return self._decompressor.decompress(temp, max_length)
        else:
            currentlen = len(self.buf) + len(data)
            nextpos = (currentlen // 16) * 16
            if currentlen == nextpos:
                self.buf.add(data)
                temp = self.cipher.decrypt(self.buf.view)
                self.buf.reset()
                return self._decompressor.decompress(temp, max_length)
            else:
                buflen = len(self.buf)
                temp2 = data[nextpos - buflen:]
                self.buf.add(data[:nextpos - buflen])
                temp = self.cipher.decrypt(self.buf.view)
                self.buf.set(temp2)
                return self._decompressor.decompress(temp, max_length)


class ZstdDecompressor(ISevenZipDecompressor):

    def __init__(self):
        if Zstd is None:
            raise UnsupportedCompressionMethodError
        self.buf = b''  # type: bytes
        self._ctc = Zstd.ZstdDecompressor()  # type: ignore

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        dobj = self._ctc.decompressobj()  # type: ignore
        if max_length < 0:
            res = self.buf + dobj.decompress(data)
            self.buf = b''
        else:
            tmp = self.buf + dobj.decompress(data)
            res = tmp[:max_length]
            self.buf = tmp[max_length:]
        return res


class ZstdCompressor(ISevenZipCompressor):

    def __init__(self):
        if Zstd is None:
            raise UnsupportedCompressionMethodError
        self._ctc = Zstd.ZstdCompressor()  # type: ignore

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self._ctc.compress(data)  # type: ignore

    def flush(self):
        pass
