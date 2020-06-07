#!/usr/bin/python -u
#
# p7zr library
#
# Copyright (c) 2019,2020 Hiroshi Miura <miurahr@linux.com>
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
import secrets
import zlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from Crypto.Cipher import AES

from py7zr import UnsupportedCompressionMethodError
from py7zr.helpers import Buffer, calculate_crc32, calculate_key
from py7zr.properties import (FILTER_BZIP2, FILTER_COPY, FILTER_CRYPTO_AES256_SHA256, FILTER_ZIP, FILTER_ZSTD,
                              READ_BLOCKSIZE, ArchivePassword, CompressionMethod, alt_methods_map, alt_methods_map_r,
                              lzma_methods_map, lzma_methods_map_r, methods_name_map)

try:
    import zstandard as Zstd  # type: ignore
except ImportError:
    Zstd = None


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


def get_alternative_compressor(filter):
    filter_id = filter['id']
    if filter_id == FILTER_BZIP2:
        compressor = bz2.BZ2Compressor()
    elif filter_id == FILTER_ZIP:
        compressor = DeflateCompressor()
    elif filter_id == FILTER_COPY:
        compressor = CopyCompressor()
    elif filter_id == FILTER_ZSTD and Zstd:
        compressor = ZstdCompressor()
    else:
        raise UnsupportedCompressionMethodError
    return compressor


def get_alternative_decompressor(coders: List[Dict[str, Any]]):
    filter_id = alt_methods_map.get(coders[0]['method'], None)
    if filter_id == FILTER_BZIP2:
        decompressor = bz2.BZ2Decompressor()  # type: Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, ISevenZipDecompressor]  # noqa
    elif filter_id == FILTER_ZIP:
        decompressor = DeflateDecompressor()
    elif filter_id == FILTER_COPY:
        decompressor = CopyDecompressor()
    elif filter_id == FILTER_ZSTD and Zstd:
        decompressor = ZstdDecompressor()
    elif filter_id == FILTER_CRYPTO_AES256_SHA256:
        password = ArchivePassword().get()
        properties = coders[0].get('properties', None)
        assert properties is not None
        decompressor = AESDecompressor(properties, password, coders[1:])
    else:
        raise UnsupportedCompressionMethodError
    return decompressor


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


class AESCompressor(ISevenZipCompressor):
    '''AES Compression(Encryption) class.
    It accept pre-processing filter which may be a LZMA compression.'''

    def __init__(self, filters, password: str) -> None:
        byte_password = password.encode('utf-16LE')
        cycles = secrets.SystemRandom().randint(1, 23)
        ivsize = 16
        iv = secrets.token_bytes(ivsize)
        salt = b''
        saltsize = len(salt)
        ivfirst = 1 if ivsize > 15 else 0
        saltfirst = 1 if saltsize > 15 else 0
        firstbyte = (cycles + (ivfirst << 6)  + (saltfirst << 7)).to_bytes(1, 'little')
        secondbyte = (((ivsize - ivfirst) & 0x0f) + (((saltsize - saltfirst) << 4) & 0xf0)).to_bytes(1, 'little')
        self.method = CompressionMethod.CRYPT_AES256_SHA256
        self.properties = firstbyte + secondbyte + salt + iv
        key = calculate_key(byte_password, cycles, salt, 'sha256')
        self.cipher = AES.new(key, AES.MODE_CBC, bytes(iv))
        self._set_compressor(filters)
        self.flushed = False
        self.buf = Buffer(size=READ_BLOCKSIZE + 16)

    def _set_compressor(self, filters):
        if len(filters) == 0:
            self._compressor = CopyCompressor()
        else:
            if filters[-1]['id'] in lzma_methods_map_r:
                try:
                    self._compressor = lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filters)
                except ValueError:
                    raise UnsupportedCompressionMethodError
            else:
                if len(filters) != 1:
                    raise UnsupportedCompressionMethodError
                else:
                    self._compressor = get_alternative_compressor(filters[0])

    def compress(self, data):
        if len(data) == 0:  # action padding
            self.flushed = True
            temp = self._compressor.flush()
            self.buf.add(temp)
            padlen = -len(self.buf) & 15
            self.buf.add(bytes(padlen))
            res = self.cipher.encrypt(self.buf.view)  # type: bytes
            self.buf.reset()
            return res
        else:
            compressed = self._compressor.compress(data)
            if len(compressed) == 0:
                return b''
            currentlen = len(self.buf) + len(compressed)
            nextpos = (currentlen // 16) * 16
            if currentlen == nextpos:
                self.buf.add(compressed)
                res = self.cipher.encrypt(self.buf.view)
                self.buf.reset()
            elif nextpos < 16:
                return b''
            else:
                buflen = len(self.buf)
                self.buf.add(compressed[:nextpos - buflen])
                res = self.cipher.encrypt(self.buf.view)
                self.buf.set(compressed[nextpos - buflen:])
            return res

    def flush(self):
        if self.flushed:
            return b''
        compressed = self._compressor.flush()
        self.buf.add(compressed)
        currentlen = len(self.buf)
        padlen = 16 - currentlen % 16 if currentlen % 16 > 0 else 0
        self.buf.add(bytes(padlen))
        res = self.cipher.encrypt(self.buf.view)
        self.buf.reset()
        self.flushed = True
        return res


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
            self._set_decompressor(coders)
            self.cipher = AES.new(key, AES.MODE_CBC, iv)
            self.buf = Buffer(size=READ_BLOCKSIZE + 16)
            self.flushed = False
        else:
            raise UnsupportedCompressionMethodError

    def _set_decompressor(self, coders):
        if len(coders) == 0:
            self._decompressor = CopyDecompressor()  # type: Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, ISevenZipDecompressor]  # noqa
        else:
            try:
                self._decompressor = get_lzma_decompressor(coders)
            except UnsupportedCompressionMethodError:
                self._decompressor = get_alternative_decompressor(coders)

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


class DeflateCompressor(ISevenZipCompressor):

    def __init__(self):
        self._compressor = zlib.compressobj(wbits=-15)

    def compress(self, data):
        return self._compressor.compress(data)

    def flush(self):
        return b''


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


class CopyCompressor(ISevenZipCompressor):

    def __init__(self):
        self._buf = bytes()

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return bytes(data)

    def flush(self):
        return b''


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
        return b''


class SevenZipDecompressor:
    """Main decompressor object which is properly configured and bind to each 7zip folder.
    because 7zip folder can have a custom compression method"""

    def __init__(self, coders: List[Dict[str, Any]], size: int, crc: Optional[int]) -> None:
        # Get password which was set when creation of py7zr.SevenZipFile object.
        self.input_size = size
        self.consumed = 0  # type: int
        self.crc = crc
        self.digest = None  # type: Optional[int]
        if check_lzma_coders(coders):
            self.decompressor = get_lzma_decompressor(coders)  # type: Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, ISevenZipDecompressor]  # noqa
        else:
            self.decompressor = get_alternative_decompressor(coders)

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

    def check_crc(self):
        return self.crc == self.digest


class SevenZipCompressor:
    """Main compressor object to configured for each 7zip folder."""

    __slots__ = ['filters', 'compressor', 'coders', 'digest']

    def __init__(self, filters=None):
        if filters is None:
            self.filters = [{"id": lzma.FILTER_LZMA2, "preset": 7 | lzma.PRESET_EXTREME}]
        else:
            self.filters = filters
        self.digest = None
        self.coders = []
        if self.filters[-1]['id'] in lzma_methods_map_r:
            try:
                self.compressor = lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=self.filters)
            except ValueError:
                raise UnsupportedCompressionMethodError
            else:
                for filter in self.filters:
                    if filter['id'] in [lzma.FILTER_LZMA1, lzma.FILTER_LZMA2]:
                        method = lzma_methods_map_r[filter['id']]
                        properties = lzma._encode_filter_properties(filter)
                        self.coders.append({'method': method, 'properties': properties, 'numinstreams': 1, 'numoutstreams': 1})
                    else:
                        method = lzma_methods_map_r[filter['id']]
                        self.coders.append({'method': method, 'properties': None, 'numinstreams': 1, 'numoutstreams': 1})
                self.coders.reverse()
        elif self.filters[-1]['id'] == FILTER_CRYPTO_AES256_SHA256:
            password = ArchivePassword().get()
            self.compressor = AESCompressor(self.filters[:-1], password=password)
            aes_properties = self.compressor.properties
            assert aes_properties is not None
            for filter in self.filters:
                if filter['id'] in [lzma.FILTER_LZMA1, lzma.FILTER_LZMA2]:
                    method = lzma_methods_map_r[filter['id']]
                    properties = lzma._encode_filter_properties(filter)
                    self.coders.append({'method': method, 'properties': properties, 'numinstreams': 1,
                                        'numoutstreams': 1})
                elif filter['id'] in lzma_methods_map_r:
                    method = lzma_methods_map_r[filter['id']]
                    self.coders.append({'method': method, 'properties': None, 'numinstreams': 1, 'numoutstreams': 1})
                elif filter['id'] == FILTER_CRYPTO_AES256_SHA256:
                    self.coders.append({'method': CompressionMethod.CRYPT_AES256_SHA256,
                                        'properties': aes_properties, 'numinstreams': 1, 'numoutstreams': 1})
                else:
                    self.coders.append({'method': alt_methods_map_r[filter['id']],
                                        'numinstreams': 1, 'numoutstreams': 1})
            self.coders.reverse()
        elif self.filters[-1]['id'] in alt_methods_map_r:
            if len(self.filters) != 1:
                raise UnsupportedCompressionMethodError
            self.compressor = get_alternative_compressor(self.filters)
            self.coders.append({'method': alt_methods_map_r[self.filters[0]['id']], 'properties': None, 'numinstreams': 1,
                                'numoutstreams': 1})

    def compress(self, data):
        self.digest = calculate_crc32(data, self.digest)
        return self.compressor.compress(data)

    def flush(self):
        return self.compressor.flush()


class Bond:
    """Represent bindings between two methods.
    bonds[i] = (incoder, outstream)
    means
    methods[i].stream[outstream] output data go to method[incoder].stream[0]
    """

    def __init__(self, incoder, outcoder):
        self.incoder = incoder
        self.outcoder = outcoder


def get_methods_names(coders: List[dict]) -> List[str]:
    """Return human readable method names for specified coders"""

    methods_names = []  # type: List[str]
    for coder in coders:
        try:
            methods_names.append(methods_name_map[coder['method']])
        except KeyError:
            raise UnsupportedCompressionMethodError("Unknown method {}".format(coder['method']))
    return methods_names
