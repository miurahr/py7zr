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
import zlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from py7zr import UnsupportedCompressionMethodError
from py7zr.helpers import Buffer, calculate_crc32, calculate_key
from py7zr.properties import (FILTER_BZIP2, FILTER_COPY, FILTER_CRYPTO_AES256_SHA256, FILTER_DEFLATE, FILTER_ZSTD,
                              READ_BLOCKSIZE, ArchivePassword, CompressionMethod, alt_methods_map, alt_methods_map_r,
                              crypto_methods, extra_compressors, lzma_methods_map, lzma_methods_map_r,
                              lzma_native_compressors, lzma_native_filters, methods_name_map)

try:
    import zstandard as Zstd  # type: ignore
except ImportError:
    Zstd = None


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
    elif filter_id == FILTER_DEFLATE:
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
    if filter_id is None:
        raise UnsupportedCompressionMethodError('Unknown method code:{}'.format(coders[0]['method']))
    if filter_id == FILTER_BZIP2:
        decompressor = bz2.BZ2Decompressor()  # type: Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, ISevenZipDecompressor]  # noqa
    elif filter_id == FILTER_DEFLATE:
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
        raise UnsupportedCompressionMethodError('Unknown method filter_id:{}'.format(filter_id))
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

    AES_CBC_BLOCKSIZE = 16

    def __init__(self, password: str) -> None:
        byte_password = password.encode('utf-16LE')
        self.cycles = 19  # FIXME
        self.iv = get_random_bytes(16)
        self.salt = b''
        self.method = CompressionMethod.CRYPT_AES256_SHA256
        key = calculate_key(byte_password, self.cycles, self.salt, 'sha256')
        self.iv += bytes(self.AES_CBC_BLOCKSIZE - len(self.iv))  # zero padding if iv < AES_CBC_BLOCKSIZE
        self.cipher = AES.new(key, AES.MODE_CBC, self.iv)
        self.flushed = False
        self.buf = Buffer(size=READ_BLOCKSIZE + self.AES_CBC_BLOCKSIZE)

    def encode_filter_properties(self):
        # cycles = secrets.SystemRandom().randint(1, 23)
        saltsize = len(self.salt)
        ivsize = len(self.iv)
        ivfirst = 1  # FIXME: it should always 1
        saltfirst = 1 if len(self.salt) > 0 else 0
        firstbyte = (self.cycles + (ivfirst << 6) + (saltfirst << 7)).to_bytes(1, 'little')
        secondbyte = (((ivsize - 1) & 0x0f) + (((saltsize - saltfirst) << 4) & 0xf0)).to_bytes(1, 'little')
        properties = firstbyte + secondbyte + self.salt + self.iv
        return properties

    def compress(self, data):
        '''Compression + AES encryption with 16byte alignment.'''
        # The size is < 16 which should be only last chunk.
        # From p7zip/CPP/7zip/common/FilterCoder.cpp
        # /*
        # AES filters need 16-bytes alignment for HARDWARE-AES instructions.
        # So we call IFilter::Filter(, size), where (size != 16 * N) only for last data block.
        # AES-CBC filters need data size aligned for 16-bytes.
        # So the encoder can add zeros to the end of original stream.
        # Some filters (BCJ and others) don't process data at the end of stream in some cases.
        # So the encoder and decoder write such last bytes without change.
        # */
        currentlen = len(self.buf) + len(data)
        nextpos = (currentlen // self.AES_CBC_BLOCKSIZE) * self.AES_CBC_BLOCKSIZE
        if currentlen == nextpos:
            self.buf.add(data)
            res = self.cipher.encrypt(self.buf.view)
            self.buf.reset()
        elif nextpos < 16:
            self.buf.add(data)
            res = b''
        else:
            buflen = len(self.buf)
            self.buf.add(data[:nextpos - buflen])
            res = self.cipher.encrypt(self.buf.view)
            self.buf.set(data[nextpos - buflen:])
        return res

    def flush(self):
        if self.flushed:
            return b''
        currentlen = len(self.buf)
        if currentlen == 0:
            self.flushed = True
            return b''
        padlen = -currentlen & 15  # padlen = 16 - currentlen % 16 if currentlen % 16 > 0 else 0
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
        return self._compressor.flush()


class DeflateDecompressor(ISevenZipDecompressor):
    def __init__(self):
        self.buf = b''
        self.flushed = False
        self._decompressor = zlib.decompressobj(wbits=-15)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = 0):
        if len(data) == 0:
            if self.flushed:
                tmp = self.buf
                self.buf = b''
                return tmp
            else:
                tmp = self.buf + self._decompressor.flush()
                self.flushed = True
            if max_length == 0:
                res = tmp
                self.buf = b''
            else:
                res = tmp[:max_length]
                self.buf = tmp[max_length:]
        elif max_length == 0:
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
        if all([x['method'] in lzma_methods_map for x in coders]):
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


class CompressorChain:
    '''compressor filter chain'''

    def __init__(self, methods_map):
        self.compressors = []  # type: List[ISevenZipCompressor]
        self.digests = []
        self.packsizes = []
        self._unpacksizes = []
        self.methods_map = methods_map

    def add_filter(self, filter):
        self.compressors.append(filter)
        self.digests.append(0)
        self.packsizes.append(0)
        self._unpacksizes.append(0)

    def encode(self, data):
        for i, compressor in enumerate(self.compressors):
            self.digests[i] += calculate_crc32(data, self.digests[i])
            self._unpacksizes[i] += len(data)
            data = compressor.compress(data)
            self.packsizes[i] += len(data)
        return data

    def flush(self):
        data = None
        for i, compressor in enumerate(self.compressors):
            if data:
                self.digests[i] += calculate_crc32(data, self.digests[i])
                self._unpacksizes[i] += len(data)
                data = compressor.compress(data)
                data += compressor.flush()
            else:
                data = compressor.flush()
            self.packsizes[i] += len(data)
        return data

    @property
    def unpacksizes(self):
        result = []
        shift = 0
        prev = False
        for i, r in enumerate(self.methods_map):
            shift += 1 if r and prev else 0
            prev = r
            result.insert(0, self._unpacksizes[i - shift])
        return result


class SevenZipCompressor:
    """Main compressor object to configured for each 7zip folder."""

    __slots__ = ['filters', 'compressor', 'coders', 'digest', 'cchain', 'methods_map']

    def __init__(self, filters=None):
        if filters is None:
            self.filters = [{"id": lzma.FILTER_LZMA2, "preset": 7 | lzma.PRESET_EXTREME}]
        else:
            self.filters = filters
        self.coders = []
        self.methods_map = []
        if len(self.filters) > 4:
            raise UnsupportedCompressionMethodError('Maximum cascade of filters is 4 but got {}.'.format(len(self.filters)))
        for filter in self.filters:
            if filter['id'] in lzma_methods_map_r:
                self.methods_map.append(True)
            elif filter['id'] in alt_methods_map_r:
                self.methods_map.append(False)
            else:
                raise UnsupportedCompressionMethodError
        # FIXME: Following complex if-else block has many duplicated code and missing filter combination cases.
        self.cchain = CompressorChain(self.methods_map)
        if all(self.methods_map):
            if self.filters[-1]['id'] in lzma_native_compressors:
                _compressor = lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=self.filters)
                self.cchain.add_filter(_compressor)
                self._set_native_coders(self.filters)
            else:
                # LZMA/LZMA2 compression should be a first filter
                raise UnsupportedCompressionMethodError
        elif any(self.methods_map):  # mix of native filters and extra filters
            if self.filters[-1]['id'] in crypto_methods:
                if all(self.methods_map[:-1]):
                    # Crypto + native compression
                    password = ArchivePassword().get()
                    self.cchain.add_filter(lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filters[:-1]))
                    _crypto = AESCompressor(password)
                    self.cchain.add_filter(_crypto)
                    aes_properties = _crypto.encode_filter_properties()
                    self._set_native_coders(self.filters[:-1])
                    self.coders.insert(0, {'method': CompressionMethod.CRYPT_AES256_SHA256,
                                           'properties': aes_properties, 'numinstreams': 1, 'numoutstreams': 1})
                elif self.filters[-2] in extra_compressors and all(self.methods_map[:-2]):
                    password = ArchivePassword().get()
                    self.cchain.add_filter(lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filters[:-2]))
                    self.cchain.add_filter(get_alternative_compressor(self.filters[-2:-1]))
                    _crypto = AESCompressor(password)
                    self.cchain.add_filter(_crypto)
                    aes_properties = _crypto.encode_filter_properties()
                    self.coders.insert(0, {'method': CompressionMethod.CRYPT_AES256_SHA256,
                                           'properties': aes_properties, 'numinstreams': 1, 'numoutstreams': 1})
                    self.coders.insert(0, {'method': alt_methods_map_r[self.filters[0]['id']], 'properties': None,
                                           'numinstreams': 1, 'numoutstreams': 1})
                    self._set_native_coders(filters[:-2])
                else:
                    raise UnsupportedCompressionMethodError
            elif self.filters[-1]['id'] in extra_compressors:
                if len(self.filters) == 2 and self.filters[1]['id'] in lzma_native_filters:
                    self.cchain.add_filter(lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filters[1:]))
                    self.cchain.add_filter(get_alternative_compressor(self.filters[0]))
                    self.coders.insert(0, {'method': alt_methods_map_r[self.filters[0]['id']], 'properties': None,
                                           'numinstreams': 1, 'numoutstreams': 1})
                    self._set_native_coders(filters[1:])
                else:
                    raise UnsupportedCompressionMethodError
            else:
                raise UnsupportedCompressionMethodError
        else:
            if self.filters[-1]['id'] in crypto_methods:
                for filter in filters[:-1]:
                    self.cchain.add_filter(get_alternative_compressor(filter))
                    self.coders.insert(0, {'method': alt_methods_map_r[filter['id']], 'properties': None,
                                       'numinstreams': 1, 'numoutstreams': 1})
                password = ArchivePassword().get()
                _crypto = AESCompressor(password)
                self.cchain.add_filter(_crypto)
                aes_properties = _crypto.encode_filter_properties()
                self.coders.insert(0, {'method': CompressionMethod.CRYPT_AES256_SHA256,
                                       'properties': aes_properties, 'numinstreams': 1, 'numoutstreams': 1})
            else:
                for filter in filters:
                    self.cchain.add_filter(get_alternative_compressor(filter))
                    self.coders.insert(0, {'method': alt_methods_map_r[filter['id']], 'properties': None,
                                           'numinstreams': 1, 'numoutstreams': 1})

    def _set_native_coders(self, filters):
        for filter in filters:
            if filter['id'] in [lzma.FILTER_LZMA1, lzma.FILTER_LZMA2, lzma.FILTER_DELTA]:
                method = lzma_methods_map_r[filter['id']]
                properties = lzma._encode_filter_properties(filter)
                self.coders.insert(0, {'method': method, 'properties': properties, 'numinstreams': 1, 'numoutstreams': 1})
            else:
                method = lzma_methods_map_r[filter['id']]
                self.coders.insert(0, {'method': method, 'properties': None, 'numinstreams': 1, 'numoutstreams': 1})

    def compress(self, data):
        return self.cchain.encode(data)

    def flush(self):
        return self.cchain.flush()

    @property
    def digests(self):
        return self.cchain.digests

    @property
    def unpacksizes(self):
        return self.cchain.unpacksizes

    @property
    def packsizes(self):
        return self.cchain.packsizes


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
