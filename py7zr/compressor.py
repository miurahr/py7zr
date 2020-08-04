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
import struct
import zlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from py7zr.exceptions import UnsupportedCompressionMethodError
from py7zr.helpers import Buffer, calculate_crc32, calculate_key
from py7zr.properties import (FILTER_ARM, FILTER_ARMTHUMB, FILTER_BZIP2, FILTER_COPY, FILTER_CRYPTO_AES256_SHA256,
                              FILTER_DEFLATE, FILTER_DELTA, FILTER_IA64, FILTER_LZMA, FILTER_LZMA2, FILTER_POWERPC,
                              FILTER_SPARC, FILTER_X86, FILTER_ZSTD, MAGIC_7Z, READ_BLOCKSIZE, CompressionMethod)

try:
    import zstandard as Zstd  # type: ignore
except ImportError:
    Zstd = None


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
        return bytes(data)


class ZstdDecompressor(ISevenZipDecompressor):

    def __init__(self):
        if Zstd is None:
            raise UnsupportedCompressionMethodError
        self._ctc = Zstd.ZstdDecompressor()  # type: ignore

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        dobj = self._ctc.decompressobj()  # type: ignore
        return dobj.decompress(data)


class ZstdCompressor(ISevenZipCompressor):

    def __init__(self):
        if Zstd is None:
            raise UnsupportedCompressionMethodError
        self._ctc = Zstd.ZstdCompressor()  # type: ignore

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self._ctc.compress(data)  # type: ignore

    def flush(self):
        return b''


class BCJFilter:

    _mask_to_allowed_number = [0, 1, 2, 4, 8, 9, 10, 12]
    _mask_to_bit_number = [0, 1, 2, 2, 3, 3, 3, 3]

    def __init__(self, func, readahead: int, is_encoder: bool, stream_size: int = 0):
        self.is_encoder = is_encoder  # type: bool
        #
        self.prev_mask = 0  # type: int
        self.prev_pos = -5  # type: int
        self.current_position = 0  # type: int
        self.stream_size = stream_size  # type: int  # should initialize in child class
        self.buffer = bytearray()
        #
        self._method = func
        self._readahead = readahead

    def _sparc_code(self):
        limit = len(self.buffer) - 4
        i = 0
        while i <= limit:
            if (self.buffer[i], self.buffer[i + 1] & 0xC0) in [(0x40, 0x00), (0x7F, 0xC0)]:
                src = struct.unpack('>L', self.buffer[i:i + 4])[0] << 2
                distance = self.current_position + i
                if self.is_encoder:
                    dest = (src + distance) >> 2
                else:
                    dest = (src - distance) >> 2
                dest = (((0 - ((dest >> 22) & 1)) << 22) & 0x3FFFFFFF) | (dest & 0x3FFFFF) | 0x40000000
                self.buffer[i:i + 4] = struct.pack('>L', dest)
            i += 4
        self.current_position = i
        return i

    def _ppc_code(self):
        limit = len(self.buffer) - 4
        i = 0
        while i <= limit:
            # PowerPC branch 6(48) 24(Offset) 1(Abs) 1(Link)
            distance = self.current_position + i
            if self.buffer[i] & 0xFC == 0x48 and self.buffer[i + 3] & 0x03 == 1:
                src = struct.unpack('>L', self.buffer[i:i + 4])[0] & 0x3FFFFFC
                if self.is_encoder:
                    dest = src + distance
                else:
                    dest = src - distance
                # lsb = int(self.buffer[i + 3]) & 0x03 == 1
                dest = (0x48 << 24) | (dest & 0x03FFFFFF) | 1
                self.buffer[i:i + 4] = struct.pack('>L', dest)
            i += 4
        self.current_position = i
        return i

    def _unpack_thumb(self, b: Union[bytearray, bytes, memoryview]) -> int:
        return ((b[1] & 0x07) << 19) | (b[0] << 11) | ((b[3] & 0x07) << 8) | b[2]

    def _pack_thumb(self, val: int):
        b = bytes([(val >> 11) & 0xFF, 0xF0 | ((val >> 19) & 0x07), val & 0xFF, 0xF8 | ((val >> 8) & 0x07)])
        return b

    def _armt_code(self) -> int:
        limit = len(self.buffer) - 4
        i = 0
        while i <= limit:
            if self.buffer[i + 1] & 0xF8 == 0xF0 and self.buffer[i + 3] & 0xF8 == 0xF8:
                src = self._unpack_thumb(self.buffer[i:i + 4]) << 1
                distance = self.current_position + i + 4
                if self.is_encoder:
                    dest = src + distance
                else:
                    dest = src - distance
                dest >>= 1
                self.buffer[i:i + 4] = self._pack_thumb(dest)
                i += 2
            i += 2
        self.current_position += i
        return i

    def _arm_code(self) -> int:
        limit = len(self.buffer) - 4
        i = 0
        while i <= limit:
            if self.buffer[i + 3] == 0xEB:
                src = struct.unpack('<L', self.buffer[i:i + 3] + b'\x00')[0] << 2
                distance = self.current_position + i + 8
                if self.is_encoder:
                    dest = (src + distance) >> 2
                else:
                    dest = (src - distance) >> 2
                self.buffer[i:i + 3] = struct.pack('<L', dest & 0xFFFFFF)[:3]
            i += 4
        self.current_position += i
        return i

    def _x86_code(self) -> int:
        size = len(self.buffer)
        if size < 5:
            return 0
        if self.current_position - self.prev_pos > 5:
            self.prev_pos = self.current_position - 5
        view = memoryview(self.buffer)
        limit = size - 5
        buffer_pos = 0
        while buffer_pos <= limit:
            if view[buffer_pos] not in [0xe8, 0xe9]:
                buffer_pos += 1
                continue
            offset = self.current_position + buffer_pos - self.prev_pos
            self.prev_pos = self.current_position + buffer_pos
            if offset > 5:
                self.prev_mask = 0
            else:
                for i in range(offset):
                    self.prev_mask &= 0x77
                    self.prev_mask <<= 1
            # note:
            # condition (self.prev_mask >> 1) in [0, 1, 2, 4, 8, 9, 10, 12]
            # is as same as
            # condition _mask_to_allowed_status[(self.prev_mask >> 1) & 0x7] and (self.prev_mask >> 1) < 0x10:
            # when _mask_to_allowed_status = [True, True, True, False, True, False, False, False]
            #
            if view[buffer_pos + 4] in [0, 0xff] and (self.prev_mask >> 1) in self._mask_to_allowed_number:
                jump_target = self.buffer[buffer_pos + 1:buffer_pos + 5]
                src = struct.unpack('<L', jump_target)[0]
                distance = self.current_position + buffer_pos + 5
                idx = self._mask_to_bit_number[self.prev_mask >> 1]
                while True:
                    if self.is_encoder:
                        dest = (src + distance) & 0xffffffff  # uint32 behavior
                    else:
                        dest = (src - distance) & 0xffffffff
                    if self.prev_mask == 0:
                        break
                    b = 0xFF & (dest >> (24 - idx * 8))
                    if not (b == 0 or b == 0xFF):
                        break
                    src = dest ^ ((1 << (32 - idx * 8)) - 1) & 0xffffffff
                write_view = view[buffer_pos + 1:buffer_pos + 5]
                write_view[0:3] = (dest & 0xFFFFFF).to_bytes(3, 'little')
                write_view[3:4] = [b'\x00', b'\xff'][(dest >> 24) & 1]  # (~(((dest >> 24) & 1) - 1)) & 0xFF
                buffer_pos += 5
                self.prev_mask = 0
            else:
                buffer_pos += 1
                self.prev_mask |= 1
        self.current_position += buffer_pos
        return buffer_pos

    def _decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        self.buffer.extend(data)
        pos = self._method()
        if self.current_position > self.stream_size - self._readahead:
            offset = self.stream_size - self.current_position
            tmp = bytes(self.buffer[:pos + offset])
            self.current_position = self.stream_size
            self.buffer = bytearray()
        else:
            tmp = bytes(self.buffer[:pos])
            self.buffer = self.buffer[pos:]
        return tmp

    def _compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        self.buffer.extend(data)
        pos = self._method()
        tmp = bytes(self.buffer[:pos])
        self.buffer = self.buffer[pos:]
        return tmp

    def _flush(self):
        return bytes(self.buffer)


class BcjSparcDecoder(ISevenZipDecompressor, BCJFilter):

    def __init__(self, size: int):
        super().__init__(self._sparc_code, 4, False, size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self._decompress(data)


class BcjSparcEncoder(ISevenZipCompressor, BCJFilter):

    def __init__(self):
        super().__init__(self._sparc_code, 4, True)

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self._compress(data)

    def flush(self):
        return self._flush()


class BcjPpcDecoder(ISevenZipDecompressor, BCJFilter):

    def __init__(self, size: int):
        super().__init__(self._ppc_code, 4, False, size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self._decompress(data)


class BcjPpcEncoder(ISevenZipCompressor, BCJFilter):

    def __init__(self):
        super().__init__(self._ppc_code, 4, True)

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self._compress(data)

    def flush(self):
        return self._flush()


class BcjArmtDecoder(ISevenZipDecompressor, BCJFilter):

    def __init__(self, size: int):
        super().__init__(self._armt_code, 4, False, size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self._decompress(data)


class BcjArmtEncoder(ISevenZipCompressor, BCJFilter):

    def __init__(self):
        super().__init__(self._armt_code, 4, True)

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self._compress(data)

    def flush(self):
        return self._flush()


class BcjArmDecoder(ISevenZipDecompressor, BCJFilter):

    def __init__(self, size: int):
        super().__init__(self._arm_code, 4, False, size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self._decompress(data)


class BcjArmEncoder(ISevenZipCompressor, BCJFilter):

    def __init__(self):
        super().__init__(self._arm_code, 4, True)

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self._compress(data)

    def flush(self):
        return self._flush()


class BCJDecoder(ISevenZipDecompressor, BCJFilter):

    def __init__(self, size: int):
        super().__init__(self._x86_code, 5, False, size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self._decompress(data)


class BCJEncoder(ISevenZipCompressor, BCJFilter):

    def __init__(self):
        super().__init__(self._x86_code, 5, True)

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self._compress(data)

    def flush(self):
        return self._flush()


algorithm_class_map = {
    FILTER_ZSTD: (ZstdCompressor, ZstdDecompressor),
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


def get_alternative_compressor(filter, password=None):
    filter_id = filter['id']
    if filter_id not in algorithm_class_map:
        raise UnsupportedCompressionMethodError
    elif SupportedMethods.is_crypto_id(filter_id):
        return algorithm_class_map[filter_id][0](password)
    else:
        return algorithm_class_map[filter_id][0]()


def get_alternative_decompressor(coder: Dict[str, Any], unpacksize=None, password=None) -> Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, ISevenZipDecompressor]:  # noqa
    filter_id = SupportedMethods.get_filter_id(coder)
    # Special treatment for BCJ filters
    if filter_id in [FILTER_X86, FILTER_ARM, FILTER_ARMTHUMB, FILTER_POWERPC, FILTER_SPARC]:
        return algorithm_class_map[filter_id][1](size=unpacksize)
    # Check supported?
    if SupportedMethods.is_native_coder(coder):
        raise UnsupportedCompressionMethodError('Unknown method code:{}'.format(coder['method']))
    if filter_id not in algorithm_class_map:
        raise UnsupportedCompressionMethodError('Unknown method filter_id:{}'.format(filter_id))
    #
    if SupportedMethods.is_crypto_id(filter_id):
        return algorithm_class_map[filter_id][1](coder['properties'], password)
    elif SupportedMethods.need_property(filter_id):
        return algorithm_class_map[filter_id][1](coder['properties'])
    else:
        return algorithm_class_map[filter_id][1]()


class LZMA1Decompressor(ISevenZipDecompressor):
    def __init__(self, filters, unpacksize):
        self._decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
        self.unpacksize = unpacksize

    def decompress(self, data, max_length):
        return self._decompressor.decompress(data, max_length)


def get_lzma_decompressor(coders: List[Dict[str, Any]], unpacksize: int):
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


class DecompressorChain:
    """decompressor filter chain"""

    def __init__(self, methods_map, unpacksizes):
        self.filters = []  # type: List[ISevenZipDecompressor]
        self._unpacksizes = []
        shift = 0
        prev = False
        for i, r in enumerate(methods_map):
            shift += 1 if r and prev else 0
            prev = r
            self._unpacksizes.append(unpacksizes[i - shift])
        self._unpacked = [0 for _ in range(len(self._unpacksizes))]
        self._unused = bytearray()
        self._buf = bytearray()

    def add_filter(self, filter):
        self.filters.append(filter)

    def _decompress(self, data, max_length: int):
        for i, decompressor in enumerate(self.filters):
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

    def decompress(self, data, max_length: int = -1) -> bytes:
        if max_length < 0:
            res = self._buf + self._decompress(self._unused + data, max_length)
            self._buf = bytearray()
            self._unused = bytearray()
        else:
            current_buf_len = len(self._buf)
            if current_buf_len >= max_length:
                self._unused.extend(data)
                res = self._buf[:max_length]
                self._buf = self._buf[max_length:]
            else:
                if len(self._unused) > 0:
                    tmp = self._decompress(self._unused + data, max_length)
                    self._unused = bytearray()
                else:
                    tmp = self._decompress(data, max_length)
                if current_buf_len + len(tmp) <= max_length:
                    res = self._buf + tmp
                    self._buf = bytearray()
                else:
                    res = self._buf + tmp[:max_length - current_buf_len]
                    self._buf = bytearray(tmp[max_length - current_buf_len:])
        return res

    @property
    def unused_size(self):
        return len(self._unused)


class SevenZipDecompressor:
    """Main decompressor object which is properly configured and bind to each 7zip folder.
    because 7zip folder can have a custom compression method"""

    def __init__(self, coders: List[Dict[str, Any]], packsize: int, unpacksizes: List[int], crc: Optional[int],
                 password: Optional[str] = None) -> None:
        self.input_size = packsize
        self.unpacksizes = unpacksizes
        self.consumed = 0  # type: int
        self.crc = crc
        self.digest = None  # type: Optional[int]
        if len(coders) > 4:
            raise UnsupportedCompressionMethodError('Maximum cascade of filters is 4 but got {}.'.format(len(coders)))
        self.methods_map = [SupportedMethods.is_native_coder(coder) for coder in coders]  # type: List[bool]
        # --------- Hack for special combinations
        # hack for LZMA1+BCJ which should be native+alternative
        _bcj_filters = [FILTER_X86, FILTER_ARM, FILTER_ARMTHUMB, FILTER_POWERPC, FILTER_SPARC]
        if len(coders) >= 2:
            target_compressor = False
            has_bcj = False
            bcj_index = -1
            for i, coder in enumerate(coders):
                filter_id = SupportedMethods.get_filter_id(coder)
                if SupportedMethods.is_compressor_id(filter_id) and filter_id != FILTER_LZMA2:
                    target_compressor = True
                if filter_id in _bcj_filters:
                    has_bcj = True
                    bcj_index = i
                if target_compressor and has_bcj:
                    self.methods_map[bcj_index] = False
                    break
        # --------- end of Hack for special combinations
        self.cchain = DecompressorChain(self.methods_map, unpacksizes)
        if all(self.methods_map):
            decompressor = get_lzma_decompressor(coders, unpacksizes[-1])
            self.cchain.add_filter(decompressor)
        elif not any(self.methods_map):
            for i in range(len(coders)):
                self.cchain.add_filter(get_alternative_decompressor(coders[i], unpacksizes[i], password))
        elif any(self.methods_map):
            for i in range(len(coders)):
                if (not any(self.methods_map[:i])) and all(self.methods_map[i:]):
                    for j in range(i):
                        self.cchain.add_filter(get_alternative_decompressor(coders[j], unpacksizes[j], password))
                    self.cchain.add_filter(get_lzma_decompressor(coders[i:], unpacksizes[i]))
                    break
            else:
                for i in range(len(coders)):
                    if self.methods_map[i]:
                        self.cchain.add_filter(get_lzma_decompressor([coders[i]], unpacksizes[i]))
                    else:
                        self.cchain.add_filter(get_alternative_decompressor(coders[i], unpacksizes[i], password))
        else:
            raise UnsupportedCompressionMethodError

    def decompress(self, data: bytes, max_length: Optional[int] = None) -> bytes:
        self.consumed += len(data)
        if max_length is not None:
            folder_data = self.cchain.decompress(data, max_length=max_length)
        else:
            folder_data = self.cchain.decompress(data)
        # calculate CRC with uncompressed data
        if self.digest:
            self.digest = calculate_crc32(folder_data, self.digest)
        else:
            self.digest = calculate_crc32(folder_data)
        return folder_data

    def check_crc(self):
        return self.crc == self.digest

    @property
    def unused_size(self):
        return self.cchain.unused_size


class CompressorChain:
    '''compressor filter chain'''

    def __init__(self, methods_map):
        self.filters = []  # type: List[ISevenZipCompressor]
        self.digest = 0
        self.packsize = 0
        self._unpacksizes = []
        self.methods_map = methods_map

    def add_filter(self, filter):
        self.filters.append(filter)
        self._unpacksizes.append(0)

    def compress(self, data):
        for i, compressor in enumerate(self.filters):
            self._unpacksizes[i] += len(data)
            data = compressor.compress(data)
        self.packsize += len(data)
        self.digest = calculate_crc32(data, self.digest)
        return data

    def flush(self):
        data = None
        for i, compressor in enumerate(self.filters):
            if data:
                self._unpacksizes[i] += len(data)
                data = compressor.compress(data)
                data += compressor.flush()
            else:
                data = compressor.flush()
        self.packsize += len(data)
        self.digest = calculate_crc32(data, self.digest)
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

    __slots__ = ['filters', 'compressor', 'coders', 'cchain', 'methods_map']

    def __init__(self, filters=None, password=None):
        if filters is None:
            self.filters = [{"id": lzma.FILTER_LZMA2, "preset": 7 | lzma.PRESET_EXTREME}]
        else:
            self.filters = filters
        if len(self.filters) > 4:
            raise UnsupportedCompressionMethodError('Maximum cascade of filters is 4 but got {}.'.format(len(self.filters)))
        self.methods_map = [SupportedMethods.is_native_filter(filter) for filter in self.filters]
        self.coders = []
        if all(self.methods_map) and SupportedMethods.is_compressor(self.filters[-1]):  # all native
            self.cchain = CompressorChain(self.methods_map)
            self._set_native_compressors_coders(self.filters)
            return
        #
        for i, f in enumerate(self.filters):
            if f['id'] == FILTER_X86:
                self.methods_map[i] = False
        #
        self.cchain = CompressorChain(self.methods_map)
        if not any(self.methods_map):  # all alternative
            for filter in filters:
                self._set_alternate_compressors_coders(filter, password)
        elif SupportedMethods.is_crypto(self.filters[-1]) and all(self.methods_map[:-1]):  # Crypto + native compression
            self._set_native_compressors_coders(self.filters[:-1])
            self._set_alternate_compressors_coders(self.filters[-1], password)
        else:
            raise UnsupportedCompressionMethodError

    def _set_native_compressors_coders(self, filters):
        self.cchain.add_filter(lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filters))
        for filter in filters:
            self.coders.insert(0, SupportedMethods.get_coder(filter))

    def _set_alternate_compressors_coders(self, filter, password=None):
        compressor = get_alternative_compressor(filter, password)
        if SupportedMethods.is_crypto(filter):
            properties = compressor.encode_filter_properties()
        else:
            properties = None
        self.cchain.add_filter(compressor)
        self.coders.insert(0, {'method': SupportedMethods.get_method_id(filter),
                               'properties': properties, 'numinstreams': 1, 'numoutstreams': 1})

    def compress(self, data):
        return self.cchain.compress(data)

    def flush(self):
        return self.cchain.flush()

    @property
    def digest(self):
        return self.cchain.digest

    @property
    def unpacksizes(self):
        return self.cchain.unpacksizes

    @property
    def packsize(self):
        return self.cchain.packsize


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
               {'id': CompressionMethod.MISC_ZSTD, 'name': 'ZStandard', 'native': False, 'need_prop': False,
                'filter_id': FILTER_ZSTD, 'type': MethodsType.compressor},
               {'id': CompressionMethod.CRYPT_AES256_SHA256, 'name': '7zAES', 'native': False, 'need_prop': True,
                'filter_id': FILTER_CRYPTO_AES256_SHA256, 'type': MethodsType.crypto},
               ]

    @classmethod
    def _find_method(cls, key_id, key_value):
        return next((item for item in cls.methods if item[key_id] == key_value), None)

    @classmethod
    def get_filter_id(cls, coder):
        return cls._find_method('id', coder['method'])['filter_id']

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
    def is_crypto(cls, filter) -> bool:
        method = cls._find_method('filter_id', filter['id'])
        if method is None:
            raise UnsupportedCompressionMethodError
        return method['type'] == MethodsType.crypto

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
    def get_method_id(cls, filter) -> bytes:
        method = cls._find_method('filter_id', filter['id'])
        if method is None:
            raise UnsupportedCompressionMethodError
        return method['id']

    @classmethod
    def get_coder(cls, filter) -> Dict[str, Any]:
        method = cls.get_method_id(filter)
        if filter['id'] in [lzma.FILTER_LZMA1, lzma.FILTER_LZMA2, lzma.FILTER_DELTA]:
            properties = lzma._encode_filter_properties(filter)  # type: Optional[bytes] # type: ignore  # noqa
        else:
            properties = None
        return {'method': method, 'properties': properties, 'numinstreams': 1, 'numoutstreams': 1}


def get_methods_names_string(coders_lists: List[List[dict]]) -> str:
    # list of known method names with a display priority order
    methods_namelist = ['LZMA2', 'LZMA', 'BZip2', 'DEFLATE', 'DEFLATE64*', 'delta', 'COPY', 'ZStandard', 'LZ4*', 'BCJ2*',
                        'BCJ', 'ARM', 'ARMT', 'IA64', 'PPC', 'SPARC', '7zAES']
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
