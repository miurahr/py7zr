#!/usr/bin/python -u
#
# p7zr library
#
# Copyright (c) 2019-2021 Hiroshi Miura <miurahr@linux.com>
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
import struct
import zlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import ppmd as Ppmd  # type: ignore
import zstandard as Zstd
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

import py7zr.bcjfilter as BCJFilter
from py7zr.exceptions import PasswordRequired, UnsupportedCompressionMethodError
from py7zr.helpers import Buffer, BufferedRW, calculate_crc32, calculate_key
from py7zr.properties import (FILTER_ARM, FILTER_ARMTHUMB, FILTER_BZIP2, FILTER_COPY, FILTER_CRYPTO_AES256_SHA256,
                              FILTER_DEFLATE, FILTER_DELTA, FILTER_IA64, FILTER_LZMA, FILTER_LZMA2, FILTER_POWERPC,
                              FILTER_PPMD, FILTER_SPARC, FILTER_X86, FILTER_ZSTD, MAGIC_7Z, READ_BLOCKSIZE,
                              CompressionMethod)


class ISevenZipCompressor(ABC):

    @abstractmethod
    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        '''
        Compress data (interface)
        :param data: input data
        :return: output data
        '''
        pass

    @abstractmethod
    def flush(self) -> bytes:
        '''
        Flush output buffer(interface)
        :return: output data
        '''
        pass


class ISevenZipDecompressor(ABC):

    @abstractmethod
    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        '''
        Decompress data (interface)
        :param data: input data
        :param max_length: maximum length of output data when it can respect, otherwise ignore.
        :return: output data
        '''
        pass


class AESCompressor(ISevenZipCompressor):
    '''AES Compression(Encryption) class.
    It accept pre-processing filter which may be a LZMA compression.'''

    AES_CBC_BLOCKSIZE = 16

    def __init__(self, password: str) -> None:
        self.cycles = 19  # FIXME
        self.iv = get_random_bytes(16)
        self.salt = b''
        self.method = CompressionMethod.CRYPT_AES256_SHA256
        key = calculate_key(password.encode('utf-16LE'), self.cycles, self.salt, 'sha256')
        self.iv += bytes(self.AES_CBC_BLOCKSIZE - len(self.iv))  # zero padding if iv < AES_CBC_BLOCKSIZE
        self.cipher = AES.new(key, AES.MODE_CBC, self.iv)
        self.flushed = False
        self.buf = Buffer(size=READ_BLOCKSIZE + self.AES_CBC_BLOCKSIZE * 2)

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
        # hopefully aligned and larger than block size.
        if currentlen >= 16 and (currentlen & 0x0f) == 0:
            self.buf.add(data)
            res = self.cipher.encrypt(self.buf.view)
            self.buf.reset()
        elif currentlen > 16:  # when not aligned
            # nextpos = (currentlen // self.AES_CBC_BLOCKSIZE) * self.AES_CBC_BLOCKSIZE
            nextpos = currentlen & ~0x0f
            buflen = len(self.buf)
            self.buf.add(data[:nextpos - buflen])
            res = self.cipher.encrypt(self.buf.view)
            self.buf.set(data[nextpos - buflen:])
        else:  # pragma: no-cover # smaller than block size, it will processed when flush()
            self.buf.add(data)
            res = b''
        return res

    def flush(self):
        if len(self.buf) > 0:
            padlen = -len(self.buf) & 15  # padlen = 16 - currentlen % 16 if currentlen % 16 > 0 else 0
            self.buf.add(bytes(padlen))
            res = self.cipher.encrypt(self.buf.view)
            self.buf.reset()
        else:
            res = b''
        return res


class AESDecompressor(ISevenZipDecompressor):

    def __init__(self, aes_properties: bytes, password: str) -> None:
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
            key = calculate_key(password.encode('utf-16LE'), numcyclespower, salt, 'sha256')
            self.cipher = AES.new(key, AES.MODE_CBC, iv)
            self.buf = Buffer(size=READ_BLOCKSIZE + 16)
        else:
            raise UnsupportedCompressionMethodError

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        currentlen = len(self.buf) + len(data)
        # when aligned to 16 bytes(expected)
        if len(data) > 0 and (currentlen & 0x0f) == 0:
            self.buf.add(data)
            temp = self.cipher.decrypt(self.buf.view)
            self.buf.reset()
            return temp
        elif len(data) > 0:  # pragma: no-cover
            # nextpos = (currentlen // 16) * 16
            nextpos = currentlen & ~0x0f
            buflen = len(self.buf)
            temp2 = data[nextpos - buflen:]
            self.buf.add(data[:nextpos - buflen])
            temp = self.cipher.decrypt(self.buf.view)
            self.buf.set(temp2)
            return temp
        elif len(self.buf) == 0:  # pragma: no-cover  # action flush
            return b''
        else:  # pragma: no-cover  # action padding
            # align = 16
            # padlen = (align - offset % align) % align
            #       = (align - (offset & (align - 1))) & (align - 1)
            #       = -offset & (align -1)
            #       = -offset & (16 - 1) = -offset & 15
            padlen = -len(self.buf) & 15
            self.buf.add(bytes(padlen))
            temp3 = self.cipher.decrypt(self.buf.view)  # type: bytes
            self.buf.reset()
            return temp3


class DeflateCompressor(ISevenZipCompressor):

    def __init__(self):
        self._compressor = zlib.compressobj(wbits=-15)

    def compress(self, data):
        return self._compressor.compress(data)

    def flush(self):
        return self._compressor.flush()


class DeflateDecompressor(ISevenZipDecompressor):

    def __init__(self):
        self.flushed = False
        self._decompressor = zlib.decompressobj(wbits=-15)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        if len(data) == 0:
            if self.flushed:
                return b''
            else:
                self.flushed = True
                return self._decompressor.flush()
        return self._decompressor.decompress(data)


class CopyCompressor(ISevenZipCompressor):

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return bytes(data)

    def flush(self):
        return b''


class CopyDecompressor(ISevenZipDecompressor):

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return bytes(data)


class ZstdDecompressor(ISevenZipDecompressor):

    def __init__(self, properties):
        if len(properties) not in [3, 5] or (properties[0], properties[1], 0) > Zstd.ZSTD_VERSION:
            raise UnsupportedCompressionMethodError
        self._buf = BufferedRW()
        ctx = Zstd.ZstdDecompressor()  # type: ignore
        self._decompressor = ctx.stream_writer(self._buf)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        self._decompressor.write(data)
        if max_length > 0:
            result = self._buf.read(max_length)
        else:
            result = self._buf.read()
        return result


class ZstdCompressor(ISevenZipCompressor):

    def __init__(self):
        self._buf = BufferedRW()
        ctx = Zstd.ZstdCompressor()  # type: ignore
        self._compressor = ctx.stream_writer(self._buf)
        self.flushed = False

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        self._compressor.write(data)
        result = self._buf.read()
        return result

    def flush(self):
        if self.flushed:
            return None
        self._compressor.flush(Zstd.FLUSH_FRAME)
        self.flushed = True
        result = self._buf.read()
        return result


class PpmdDecompressor(ISevenZipDecompressor):

    def __init__(self, properties: bytes):
        if not isinstance(properties, bytes):
            raise UnsupportedCompressionMethodError
        if len(properties) == 5:
            level, mem = struct.unpack("<BL", properties)
        elif len(properties) == 7:
            level, mem, _, _ = struct.unpack("<BLBB", properties)
        else:
            raise UnsupportedCompressionMethodError
        self._buf = BufferedRW()
        self.decoder = None
        self.level = level
        self.mem = mem
        self.initialized = False

    def _init2(self):
        self.decoder = Ppmd.Ppmd7Decoder(self._buf, self.level, self.mem)  # type: ignore
        self.initialized = True

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length=-1) -> bytes:
        self._buf.write(data)
        if not self.initialized:
            if len(self._buf) <= 4:
                return b''
            self._init2()
        assert self.decoder is not None
        if max_length <= 0:
            return self.decoder.decode(1)
        if len(data) == 0:
            return self.decoder.decode(max_length)
        #
        size = min(READ_BLOCKSIZE, max_length)
        res = bytearray()
        while len(self._buf) > 0 and len(res) < size:
            res += self.decoder.decode(1)
        return bytes(res)


class PpmdCompressor(ISevenZipCompressor):

    def __init__(self, level: int, mem: int):
        self._buf = BufferedRW()
        self.encoder = Ppmd.Ppmd7Encoder(self._buf, level, mem)  # type: ignore

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        self.encoder.encode(data)
        return self._buf.read()

    def flush(self):
        self.encoder.flush()
        return self._buf.read()


class BcjSparcDecoder(ISevenZipDecompressor):

    def __init__(self, size: int):
        self.decoder = BCJFilter.SparcDecoder(size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self.decoder.decode(data)


class BcjSparcEncoder(ISevenZipCompressor):

    def __init__(self):
        self.encoder = BCJFilter.SparcEncoder()

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self.encoder.encode(data)

    def flush(self):
        return self.encoder.flush()


class BcjPpcDecoder(ISevenZipDecompressor):

    def __init__(self, size: int):
        self.decoder = BCJFilter.PpcDecoder(size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self.decoder.decode(data)


class BcjPpcEncoder(ISevenZipCompressor):

    def __init__(self):
        self.encoder = BCJFilter.PpcEncoder()

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self.encoder.encode(data)

    def flush(self):
        return self.encoder.flush()


class BcjArmtDecoder(ISevenZipDecompressor):

    def __init__(self, size: int):
        self.decoder = BCJFilter.ArmtDecoder(size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self.decoder.decode(data)


class BcjArmtEncoder(ISevenZipCompressor):

    def __init__(self):
        self.encoder = BCJFilter.ArmtEncoder()

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self.encoder.encode(data)

    def flush(self):
        return self.encoder.flush()


class BcjArmDecoder(ISevenZipDecompressor):

    def __init__(self, size: int):
        self.decoder = BCJFilter.ArmDecoder(size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self.decoder.decode(data)


class BcjArmEncoder(ISevenZipCompressor):

    def __init__(self):
        self.encoder = BCJFilter.ArmEncoder()

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self.encoder.encode(data)

    def flush(self):
        return self.encoder.flush()


class BCJDecoder(ISevenZipDecompressor):

    def __init__(self, size: int):
        self.decoder = BCJFilter.BCJDecoder(size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self.decoder.decode(data)


class BCJEncoder(ISevenZipCompressor):

    def __init__(self):
        self.encoder = BCJFilter.BCJEncoder()

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self.encoder.encode(data)

    def flush(self):
        return self.encoder.flush()


algorithm_class_map = {
    FILTER_ZSTD: (ZstdCompressor, ZstdDecompressor),
    FILTER_PPMD: (PpmdCompressor, PpmdDecompressor),
    FILTER_BZIP2: (bz2.BZ2Compressor, bz2.BZ2Decompressor),
    FILTER_COPY: (CopyCompressor, CopyDecompressor),
    FILTER_DEFLATE: (DeflateCompressor, DeflateDecompressor),
    FILTER_CRYPTO_AES256_SHA256: (AESCompressor, AESDecompressor),
    FILTER_X86: (BCJEncoder, BCJDecoder),
    FILTER_ARM: (BcjArmEncoder, BcjArmDecoder),
    FILTER_ARMTHUMB: (BcjArmtEncoder, BcjArmtDecoder),
    FILTER_POWERPC: (BcjPpcEncoder, BcjPpcDecoder),
    FILTER_SPARC: (BcjSparcEncoder, BcjSparcDecoder),
}  # type: Dict[int, Tuple[Any, Any]]


class LZMA1Decompressor(ISevenZipDecompressor):
    def __init__(self, filters, unpacksize):
        self._decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
        self.unpacksize = unpacksize

    def decompress(self, data, max_length):
        return self._decompressor.decompress(data, max_length)


class SevenZipDecompressor:
    """Main decompressor object which is properly configured and bind to each 7zip folder.
    because 7zip folder can have a custom compression method"""

    def __init__(self, coders: List[Dict[str, Any]], packsize: int, unpacksizes: List[int], crc: Optional[int],
                 password: Optional[str] = None) -> None:
        self.input_size = packsize
        self.unpacksizes = unpacksizes
        self.consumed = 0  # type: int
        self.crc = crc
        self.digest = 0
        if len(coders) > 4:
            raise UnsupportedCompressionMethodError('Maximum cascade of filters is 4 but got {}.'.format(len(coders)))
        self.methods_map = [SupportedMethods.is_native_coder(coder) for coder in coders]  # type: List[bool]
        # Check if password given for encrypted archive
        if SupportedMethods.needs_password(coders) and password is None:
            raise PasswordRequired("Password is required for extracting given archive.")
        # Check filters combination and required parameters
        if len(coders) >= 2:
            target_compressor = False
            has_bcj = False
            bcj_index = -1
            for i, coder in enumerate(coders):
                filter_id = SupportedMethods.get_filter_id(coder)
                if SupportedMethods.is_compressor_id(filter_id) and filter_id != FILTER_LZMA2:
                    target_compressor = True
                if filter_id in [FILTER_X86, FILTER_ARM, FILTER_ARMTHUMB, FILTER_POWERPC, FILTER_SPARC]:
                    has_bcj = True
                    bcj_index = i
                # hack for LZMA1+BCJ which should be native+alternative
                if target_compressor and has_bcj:
                    self.methods_map[bcj_index] = False
                    break
        self.chain = []  # type: List[Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, ISevenZipDecompressor]]
        self._unpacksizes = []  # type: List[int]
        self.input_size = self.input_size
        shift = 0
        prev = False
        for i, r in enumerate(self.methods_map):
            shift += 1 if r and prev else 0
            prev = r
            self._unpacksizes.append(unpacksizes[i - shift])
        self._unpacked = [0 for _ in range(len(self._unpacksizes))]
        self.consumed = 0
        self._unused = bytearray()
        self._buf = bytearray()
        self._pos = 0
        # ---
        if all(self.methods_map):
            decompressor = self._get_lzma_decompressor(coders, unpacksizes[-1])
            self.chain.append(decompressor)
        elif not any(self.methods_map):
            for i in range(len(coders)):
                self.chain.append(self._get_alternative_decompressor(coders[i], unpacksizes[i], password))
        elif any(self.methods_map):
            for i in range(len(coders)):
                if (not any(self.methods_map[:i])) and all(self.methods_map[i:]):
                    for j in range(i):
                        self.chain.append(self._get_alternative_decompressor(coders[j], unpacksizes[j], password))
                    self.chain.append(self._get_lzma_decompressor(coders[i:], unpacksizes[i]))
                    break
            else:
                for i in range(len(coders)):
                    if self.methods_map[i]:
                        self.chain.append(self._get_lzma_decompressor([coders[i]], unpacksizes[i]))
                    else:
                        self.chain.append(self._get_alternative_decompressor(coders[i], unpacksizes[i], password))
        else:
            raise UnsupportedCompressionMethodError

    def _decompress(self, data, max_length: int):
        for i, decompressor in enumerate(self.chain):
            if self._unpacked[i] < self._unpacksizes[i]:
                if isinstance(decompressor, LZMA1Decompressor):
                    data = decompressor.decompress(data, max_length)  # always give max_length for lzma1
                else:
                    data = decompressor.decompress(data)
                self._unpacked[i] += len(data)
            elif len(data) == 0:
                data = b''
            else:
                raise EOFError
        return data

    def decompress(self, fp, max_length: int = -1) -> bytes:
        # read data from disk
        rest_size = self.input_size - self.consumed
        read_size = min(rest_size, READ_BLOCKSIZE)
        data = fp.read(read_size)
        self.consumed += len(data)
        #
        if max_length < 0:
            res = self._buf[self._pos:] + self._decompress(self._unused + data, max_length)
            self._buf = bytearray()
            self._unused = bytearray()
            self._pos = 0
        else:
            current_buf_len = len(self._buf) - self._pos
            if current_buf_len >= max_length:
                self._unused.extend(data)
                res = self._buf[self._pos:self._pos + max_length]
                self._pos += max_length
            else:
                if len(self._unused) > 0:
                    tmp = self._decompress(self._unused + data, max_length)
                    self._unused = bytearray()
                else:
                    tmp = self._decompress(data, max_length)
                if current_buf_len + len(tmp) <= max_length:
                    res = self._buf[self._pos:] + tmp
                    self._buf = bytearray()
                    self._pos = 0
                else:
                    res = self._buf[self._pos:] + tmp[:max_length - current_buf_len]
                    self._buf = bytearray(tmp[max_length - current_buf_len:])
                    self._pos = 0
        self.digest = calculate_crc32(res, self.digest)
        return res

    def check_crc(self):
        return self.crc == self.digest

    @property
    def unused_size(self):
        return len(self._unused)

    def _get_lzma_decompressor(self, coders: List[Dict[str, Any]], unpacksize: int):
        filters = []  # type: List[Dict[str, Any]]
        lzma1 = False
        for coder in coders:
            if coder['numinstreams'] != 1 or coder['numoutstreams'] != 1:
                raise UnsupportedCompressionMethodError('Only a simple compression method is currently supported.')
            if not SupportedMethods.is_native_coder(coder):
                raise UnsupportedCompressionMethodError
            properties = coder.get('properties', None)
            filter_id = SupportedMethods.get_filter_id(coder)
            if filter_id == FILTER_LZMA:
                lzma1 = True
            if properties is not None:
                filters[:0] = [lzma._decode_filter_properties(filter_id, properties)]  # type: ignore
            else:
                filters[:0] = [{'id': filter_id}]
        if lzma1:
            return LZMA1Decompressor(filters, unpacksize)
        else:
            return lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)

    def _get_alternative_decompressor(self, coder: Dict[str, Any], unpacksize=None, password=None) -> Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, ISevenZipDecompressor]:  # noqa
        filter_id = SupportedMethods.get_filter_id(coder)
        # Special treatment for BCJ filters
        if filter_id in [FILTER_X86, FILTER_ARM, FILTER_ARMTHUMB, FILTER_POWERPC, FILTER_SPARC]:
            return algorithm_class_map[filter_id][1](size=unpacksize)
        # Check supported?
        if SupportedMethods.is_native_coder(coder):
            raise UnsupportedCompressionMethodError('Unknown method code:{}'.format(coder['method']))
        if filter_id not in algorithm_class_map:
            raise UnsupportedCompressionMethodError('Unknown method filter_id:{}'.format(filter_id))
        if algorithm_class_map[filter_id][1] is None:
            raise UnsupportedCompressionMethodError(
                'Decompression is not supported by {}.'.format(SupportedMethods.get_method_name_id(filter_id)))
        #
        if SupportedMethods.is_crypto_id(filter_id):
            return algorithm_class_map[filter_id][1](coder['properties'], password)
        elif SupportedMethods.need_property(filter_id):
            return algorithm_class_map[filter_id][1](coder['properties'])
        else:
            return algorithm_class_map[filter_id][1]()


class SevenZipCompressor:
    """Main compressor object to configured for each 7zip folder."""

    __slots__ = ['filters', 'chain', 'compressor', 'coders', 'methods_map', 'digest', 'packsize', '_unpacksizes']

    def __init__(self, filters=None, password=None):
        self.filters = []  # type: List[ISevenZipCompressor]
        self.chain = []
        self.digest = 0
        self.packsize = 0
        self._unpacksizes = []
        if filters is None:
            self.filters = [{"id": lzma.FILTER_LZMA2, "preset": 7 | lzma.PRESET_EXTREME}]
        else:
            self.filters = filters
        if len(self.filters) > 4:
            raise UnsupportedCompressionMethodError('Maximum cascade of filters is 4 but got {}.'.format(len(self.filters)))
        self.methods_map = [SupportedMethods.is_native_filter(filter) for filter in self.filters]
        self.coders = []
        if all(self.methods_map) and SupportedMethods.is_compressor(self.filters[-1]):  # all native
            self._set_native_compressors_coders(self.filters)
            return
        #
        for i, f in enumerate(self.filters):
            if f['id'] == FILTER_X86:
                self.methods_map[i] = False
        #
        if not any(self.methods_map):  # all alternative
            for f in filters:
                self._set_alternate_compressors_coders(f, password)
        elif SupportedMethods.is_crypto_id(self.filters[-1]['id']) and all(self.methods_map[:-1]):
            self._set_native_compressors_coders(self.filters[:-1])
            self._set_alternate_compressors_coders(self.filters[-1], password)
        else:
            raise UnsupportedCompressionMethodError

    def _set_native_compressors_coders(self, filters):
        self.chain.append(lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filters))
        self._unpacksizes.append(0)
        for filter in filters:
            self.coders.insert(0, SupportedMethods.get_coder(filter))

    def _set_alternate_compressors_coders(self, alt_filter, password=None):
        filter_id = alt_filter['id']
        properties = None
        if filter_id not in algorithm_class_map:
            raise UnsupportedCompressionMethodError
        elif SupportedMethods.is_crypto_id(filter_id):
            compressor = algorithm_class_map[filter_id][0](password)
        elif SupportedMethods.need_property(filter_id):
            if filter_id == FILTER_ZSTD:
                level = 3
                properties = struct.pack("BBBBB", Zstd.ZSTD_VERSION[0], Zstd.ZSTD_VERSION[1], level, 0, 0)
                compressor = algorithm_class_map[filter_id][0]()
            elif filter_id == FILTER_PPMD:
                order = alt_filter.get('level', 6)
                mem_size = alt_filter.get('mem', 16) << 20
                properties = struct.pack("<BLBB", order, mem_size, 0, 0)
                compressor = algorithm_class_map[filter_id][0](order, mem_size)
        else:
            compressor = algorithm_class_map[filter_id][0]()
        if SupportedMethods.is_crypto_id(filter_id):
            properties = compressor.encode_filter_properties()
        self.chain.append(compressor)
        self._unpacksizes.append(0)
        self.coders.insert(0, {'method': SupportedMethods.get_method_id(filter_id),
                               'properties': properties, 'numinstreams': 1, 'numoutstreams': 1})

    def compress(self, fd, fp, crc=0):
        data = fd.read(READ_BLOCKSIZE)
        insize = len(data)
        foutsize = 0
        while data:
            crc = calculate_crc32(data, crc)
            for i, compressor in enumerate(self.chain):
                self._unpacksizes[i] += len(data)
                data = compressor.compress(data)
            self.packsize += len(data)
            self.digest = calculate_crc32(data, self.digest)
            foutsize += len(data)
            fp.write(data)
            data = fd.read(READ_BLOCKSIZE)
            insize += len(data)
        return insize, foutsize, crc

    def flush(self, fp):
        data = None
        for i, compressor in enumerate(self.chain):
            if data:
                self._unpacksizes[i] += len(data)
                data = compressor.compress(data)
                data += compressor.flush()
            else:
                data = compressor.flush()
        self.packsize += len(data)
        self.digest = calculate_crc32(data, self.digest)
        fp.write(data)
        return len(data)

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


class MethodsType(Enum):
    compressor = 0
    filter = 1
    crypto = 2


class SupportedMethods:
    """Hold list of methods."""

    formats = [{'name': "7z", 'magic': MAGIC_7Z}]
    methods = [{'id': CompressionMethod.COPY, 'name': 'COPY', 'native': False, 'need_prop': False,
                'filter_id': FILTER_COPY, 'type': MethodsType.compressor},
               {'id': CompressionMethod.LZMA2, 'name': "LZMA2", 'native': True, 'need_prop': True,
                'filter_id': FILTER_LZMA2, 'type': MethodsType.compressor},
               {'id': CompressionMethod.DELTA, 'name': "DELTA", 'native': True, 'need_prop': True,
                'filter_id': FILTER_DELTA, 'type': MethodsType.filter},
               {'id': CompressionMethod.LZMA, 'name': "LZMA", 'native': True, 'need_prop': True,
                'filter_id': FILTER_LZMA, 'type': MethodsType.compressor},
               {'id': CompressionMethod.P7Z_BCJ, 'name': "BCJ", 'native': True, 'need_prop': False,
                'filter_id': FILTER_X86, 'type': MethodsType.filter},
               {'id': CompressionMethod.BCJ_PPC, 'name': 'PPC', 'native': True, 'need_prop': False,
                'filter_id': FILTER_POWERPC, 'type': MethodsType.filter},
               {'id': CompressionMethod.BCJ_IA64, 'name': 'IA64', 'native': True, 'need_prop': False,
                'filter_id': FILTER_IA64, 'type': MethodsType.filter},
               {'id': CompressionMethod.BCJ_ARM, 'name': "ARM", 'native': True, 'need_prop': False,
                'filter_id': FILTER_ARM, 'type': MethodsType.filter},
               {'id': CompressionMethod.BCJ_ARMT, 'name': "ARMT", 'native': True, 'need_prop': False,
                'filter_id': FILTER_ARMTHUMB, 'type': MethodsType.filter},
               {'id': CompressionMethod.BCJ_SPARC, 'name': 'SPARC', 'native': True, 'need_prop': False,
                'filter_id': FILTER_SPARC, 'type': MethodsType.filter},
               {'id': CompressionMethod.MISC_DEFLATE, 'name': 'DEFLATE', 'native': False, 'need_prop': False,
                'filter_id': FILTER_DEFLATE, 'type': MethodsType.compressor},
               {'id': CompressionMethod.MISC_BZIP2, 'name': 'BZip2', 'native': False, 'need_prop': False,
                'filter_id': FILTER_BZIP2, 'type': MethodsType.compressor},
               {'id': CompressionMethod.MISC_ZSTD, 'name': 'ZStandard', 'native': False, 'need_prop': True,
                'filter_id': FILTER_ZSTD, 'type': MethodsType.compressor},
               {'id': CompressionMethod.PPMD, 'name': 'PPMd', 'native': False, 'need_prop': True,
                'filter_id': FILTER_PPMD, 'type': MethodsType.compressor},
               {'id': CompressionMethod.CRYPT_AES256_SHA256, 'name': '7zAES', 'native': False, 'need_prop': True,
                'filter_id': FILTER_CRYPTO_AES256_SHA256, 'type': MethodsType.crypto},
               ]

    @classmethod
    def _find_method(cls, key_id, key_value):
        return next((item for item in cls.methods if item[key_id] == key_value), None)

    @classmethod
    def get_method_name_id(cls, filter_id):
        method = cls._find_method('filter_id', filter_id)
        return method['name']

    @classmethod
    def get_filter_id(cls, coder):
        method = cls._find_method('id', coder['method'])
        if method is None:
            return None
        return method['filter_id']

    @classmethod
    def is_native_filter(cls, filter) -> bool:
        method = cls._find_method('filter_id', filter['id'])
        if method is None:
            raise UnsupportedCompressionMethodError
        return method['native']

    @classmethod
    def is_compressor(cls, filter):
        method = cls._find_method('filter_id', filter['id'])
        return method['type'] == MethodsType.compressor

    @classmethod
    def is_compressor_id(cls, filter_id):
        method = cls._find_method('filter_id', filter_id)
        return method['type'] == MethodsType.compressor

    @classmethod
    def is_native_coder(cls, coder) -> bool:
        method = cls._find_method('id', coder['method'])
        if method is None:
            raise UnsupportedCompressionMethodError
        return method['native']

    @classmethod
    def need_property(cls, filter_id):
        method = cls._find_method('filter_id', filter_id)
        if method is None:
            raise UnsupportedCompressionMethodError
        return method['need_prop']

    @classmethod
    def is_crypto_id(cls, filter_id) -> bool:
        method = cls._find_method('filter_id', filter_id)
        if method is None:
            raise UnsupportedCompressionMethodError
        return method['type'] == MethodsType.crypto

    @classmethod
    def get_method_id(cls, filter_id) -> bytes:
        method = cls._find_method('filter_id', filter_id)
        if method is None:
            raise UnsupportedCompressionMethodError
        return method['id']

    @classmethod
    def get_coder(cls, filter) -> Dict[str, Any]:
        method = cls.get_method_id(filter['id'])
        if filter['id'] in [lzma.FILTER_LZMA1, lzma.FILTER_LZMA2, lzma.FILTER_DELTA]:
            properties = lzma._encode_filter_properties(filter)  # type: Optional[bytes] # type: ignore  # noqa
        else:
            properties = None
        return {'method': method, 'properties': properties, 'numinstreams': 1, 'numoutstreams': 1}

    @classmethod
    def needs_password(cls, coders) -> bool:
        for coder in coders:
            filter_id = SupportedMethods.get_filter_id(coder)
            if filter_id is None:
                continue
            if SupportedMethods.is_crypto_id(filter_id):
                return True
        return False


def get_methods_names_string(coders_lists: List[List[dict]]) -> str:
    # list of known method names with a display priority order
    methods_namelist = ['LZMA2', 'LZMA', 'BZip2', 'DEFLATE', 'DEFLATE64*', 'delta', 'COPY', 'PPMd', 'ZStandard',
                        'LZ4*', 'BCJ2*', 'BCJ', 'ARM', 'ARMT', 'IA64', 'PPC', 'SPARC', '7zAES']
    unsupported_methods = {CompressionMethod.P7Z_BCJ2: 'BCJ2*',
                           CompressionMethod.MISC_LZ4: 'LZ4*',
                           CompressionMethod.MISC_DEFLATE64: 'DEFLATE64*'}
    methods_names = []
    for coders in coders_lists:
        for coder in coders:
            for m in SupportedMethods.methods:
                if coder['method'] == m['id']:
                    methods_names.append(m['name'])
            if coder['method'] in unsupported_methods:
                methods_names.append(unsupported_methods[coder['method']])
    return ', '.join(filter(lambda x: x in methods_names, methods_namelist))
