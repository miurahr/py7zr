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

import pyppmd
import pyzstd
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes

from py7zr.exceptions import PasswordRequired, UnsupportedCompressionMethodError
from py7zr.helpers import Buffer, calculate_crc32, calculate_key
from py7zr.properties import (
    COMPRESSION_METHOD,
    FILTER_ARM,
    FILTER_ARMTHUMB,
    FILTER_BROTLI,
    FILTER_BZIP2,
    FILTER_COPY,
    FILTER_CRYPTO_AES256_SHA256,
    FILTER_DEFLATE,
    FILTER_DELTA,
    FILTER_IA64,
    FILTER_LZMA,
    FILTER_LZMA2,
    FILTER_POWERPC,
    FILTER_PPMD,
    FILTER_SPARC,
    FILTER_X86,
    FILTER_ZSTD,
    MAGIC_7Z,
    CompressionMethod,
    get_default_blocksize,
)

try:
    import bcj as BCJFilter  # type: ignore  # noqa
except ImportError:
    import py7zr.bcjfilter as BCJFilter  # type: ignore  # noqa
try:
    import brotli  # type: ignore  # noqa
except ImportError:
    import brotlicffi as brotli  # type: ignore  # noqa
brotli_major = 1
brotli_minor = 0


class ISevenZipCompressor(ABC):
    @abstractmethod
    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        """
        Compress data (interface)
        :param data: input data
        :return: output data
        """
        pass

    @abstractmethod
    def flush(self) -> bytes:
        """
        Flush output buffer(interface)
        :return: output data
        """
        pass


class ISevenZipDecompressor(ABC):
    @abstractmethod
    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        """
        Decompress data (interface)
        :param data: input data
        :param max_length: maximum length of output data when it can respect, otherwise ignore.
        :return: output data
        """
        pass


class AESCompressor(ISevenZipCompressor):
    """AES Compression(Encryption) class.
    It accept pre-processing filter which may be a LZMA compression."""

    AES_CBC_BLOCKSIZE = 16

    def __init__(self, password: str, blocksize: Optional[int] = None) -> None:
        self.cycles = 19  # as same as p7zip
        self.iv = get_random_bytes(16)
        self.salt = b""
        self.method = CompressionMethod.CRYPT_AES256_SHA256
        key = calculate_key(password.encode("utf-16LE"), self.cycles, self.salt, "sha256")
        self.iv += bytes(self.AES_CBC_BLOCKSIZE - len(self.iv))  # zero padding if iv < AES_CBC_BLOCKSIZE
        self.cipher = AES.new(key, AES.MODE_CBC, self.iv)
        self.flushed = False
        if blocksize:
            self.buf = Buffer(size=blocksize + self.AES_CBC_BLOCKSIZE * 2)
        else:
            self.buf = Buffer(size=get_default_blocksize() + self.AES_CBC_BLOCKSIZE * 2)

    def encode_filter_properties(self):
        saltsize = len(self.salt)
        ivsize = len(self.iv)
        ivfirst = 1  # it should always 1
        saltfirst = 1 if len(self.salt) > 0 else 0
        firstbyte = (self.cycles + (ivfirst << 6) + (saltfirst << 7)).to_bytes(1, "little")
        secondbyte = (((ivsize - 1) & 0x0F) + (((saltsize - saltfirst) << 4) & 0xF0)).to_bytes(1, "little")
        properties = firstbyte + secondbyte + self.salt + self.iv
        return properties

    def compress(self, data):
        """Compression + AES encryption with 16byte alignment."""
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
        if currentlen >= 16 and (currentlen & 0x0F) == 0:
            self.buf.add(data)
            res = self.cipher.encrypt(self.buf.view)
            self.buf.reset()
        elif currentlen > 16:  # when not aligned
            # nextpos = (currentlen // self.AES_CBC_BLOCKSIZE) * self.AES_CBC_BLOCKSIZE
            nextpos = currentlen & ~0x0F
            buflen = len(self.buf)
            self.buf.add(data[: nextpos - buflen])
            res = self.cipher.encrypt(self.buf.view)
            self.buf.set(data[nextpos - buflen :])
        else:  # pragma: no-cover # smaller than block size, it will processed when flush()
            self.buf.add(data)
            res = b""
        return res

    def flush(self):
        if len(self.buf) > 0:
            # padlen = 16 - currentlen % 16 if currentlen % 16 > 0 else 0
            padlen = -len(self.buf) & 15
            self.buf.add(bytes(padlen))
            res = self.cipher.encrypt(self.buf.view)
            self.buf.reset()
        else:
            res = b""
        return res


class AESDecompressor(ISevenZipDecompressor):
    """Decrypt data"""

    def __init__(self, aes_properties: bytes, password: str, blocksize: Optional[int] = None) -> None:
        firstbyte = aes_properties[0]
        numcyclespower = firstbyte & 0x3F
        if firstbyte & 0xC0 != 0:
            saltsize = (firstbyte >> 7) & 1
            ivsize = (firstbyte >> 6) & 1
            secondbyte = aes_properties[1]
            saltsize += secondbyte >> 4
            ivsize += secondbyte & 0x0F
            assert len(aes_properties) == 2 + saltsize + ivsize
            salt = aes_properties[2 : 2 + saltsize]
            iv = aes_properties[2 + saltsize : 2 + saltsize + ivsize]
            assert len(salt) == saltsize
            assert len(iv) == ivsize
            assert numcyclespower <= 24
            if ivsize < 16:
                iv += bytes("\x00" * (16 - ivsize), "ascii")
            key = calculate_key(password.encode("utf-16LE"), numcyclespower, salt, "sha256")
            self.cipher = AES.new(key, AES.MODE_CBC, iv)
            if blocksize:
                self.buf = Buffer(size=blocksize + 16)
            else:
                self.buf = Buffer(size=get_default_blocksize() + 16)
        else:
            raise UnsupportedCompressionMethodError(firstbyte, "Wrong 7zAES properties")

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        currentlen = len(self.buf) + len(data)
        # when aligned to 16 bytes(expected)
        if len(data) > 0 and (currentlen & 0x0F) == 0:
            self.buf.add(data)
            temp = self.cipher.decrypt(self.buf.view)
            self.buf.reset()
            return temp
        elif len(data) > 0:  # pragma: no-cover
            # nextpos = (currentlen // 16) * 16
            nextpos = currentlen & ~0x0F
            buflen = len(self.buf)
            temp2 = data[nextpos - buflen :]
            self.buf.add(data[: nextpos - buflen])
            temp = self.cipher.decrypt(self.buf.view)
            self.buf.set(temp2)
            return temp
        elif len(self.buf) == 0:  # pragma: no-cover  # action flush
            return b""
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
                return b""
            else:
                self.flushed = True
                return self._decompressor.flush()
        return self._decompressor.decompress(data)


class CopyCompressor(ISevenZipCompressor):
    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return bytes(data)

    def flush(self):
        return b""


class CopyDecompressor(ISevenZipDecompressor):
    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return bytes(data)


class PpmdDecompressor(ISevenZipDecompressor):
    """Decompress PPMd compressed data"""

    def __init__(self, properties: bytes, blocksize: Optional[int] = None):
        if not isinstance(properties, bytes):
            raise UnsupportedCompressionMethodError(properties, "Unknown type of properties is passed")
        if len(properties) == 5:
            order, mem = struct.unpack("<BL", properties)
        elif len(properties) == 7:
            order, mem, _, _ = struct.unpack("<BLBB", properties)
        else:
            raise UnsupportedCompressionMethodError(properties, "Unknown size of properties is passed")
        self.decoder = pyppmd.Ppmd7Decoder(order, mem)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length=-1) -> bytes:
        if max_length <= 0:
            return self.decoder.decode(data, 1)
        if len(data) == 0:
            return self.decoder.flush(max_length)
        return self.decoder.decode(data, max_length)


class PpmdCompressor(ISevenZipCompressor):
    """Compress with PPMd compression algorithm"""

    def __init__(self, properties: bytes):
        order, mem = self._decode_property(properties)
        self.encoder = pyppmd.Ppmd7Encoder(order, mem)

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self.encoder.encode(data)

    def flush(self):
        return self.encoder.flush()

    def _decode_property(self, properties):
        order, mem, _, _ = struct.unpack("<BLBB", properties)
        return order, mem

    @classmethod
    def encode_filter_properties(cls, filter: Dict[str, Union[str, int]]):
        order = filter.get("order", 8)
        mem = filter.get("mem", 24)
        if isinstance(mem, str):
            if mem.isdecimal():
                size = 1 << int(mem)
            elif mem.lower().endswith("m") and mem[:-1].isdecimal():
                size = int(mem[:-1]) << 20
            elif mem.lower().endswith("k") and mem[:-1].isdecimal():
                size = int(mem[:-1]) << 10
            elif mem.lower().endswith("b") and mem[:-1].isdecimal():
                size = int(mem[:-1])
            else:
                raise ValueError("Ppmd:Unsupported memory size is specified: {0}".format(mem))
        elif isinstance(mem, int):
            size = 1 << mem
        else:
            raise ValueError("Ppmd:Unsupported memory size is specified: {0}".format(mem))
        properties = struct.pack("<BLBB", order, size, 0, 0)
        return properties


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
        self.decoder = BCJFilter.PPCDecoder(size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self.decoder.decode(data)


class BcjPpcEncoder(ISevenZipCompressor):
    def __init__(self):
        self.encoder = BCJFilter.PPCEncoder()

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self.encoder.encode(data)

    def flush(self):
        return self.encoder.flush()


class BcjArmtDecoder(ISevenZipDecompressor):
    def __init__(self, size: int):
        self.decoder = BCJFilter.ARMTDecoder(size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self.decoder.decode(data)


class BcjArmtEncoder(ISevenZipCompressor):
    def __init__(self):
        self.encoder = BCJFilter.ARMTEncoder()

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self.encoder.encode(data)

    def flush(self):
        return self.encoder.flush()


class BcjArmDecoder(ISevenZipDecompressor):
    def __init__(self, size: int):
        self.decoder = BCJFilter.ARMDecoder(size)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self.decoder.decode(data)


class BcjArmEncoder(ISevenZipCompressor):
    def __init__(self):
        self.encoder = BCJFilter.ARMEncoder()

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


class BrotliCompressor(ISevenZipCompressor):
    def __init__(self, level):
        self._compressor = brotli.Compressor(quality=level)

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self._compressor.process(data)

    def flush(self) -> bytes:
        return self._compressor.flush()


class BrotliDecompressor(ISevenZipDecompressor):
    def __init__(self, properties: bytes, block_size: int):
        if len(properties) != 3:
            raise UnsupportedCompressionMethodError(properties, "Unknown size of properties are passed")
        if (properties[0], properties[1]) > (brotli_major, brotli_minor):
            raise UnsupportedCompressionMethodError(
                properties,
                "Unsupported brotli version: {}.{} our {}.{}".format(
                    properties[0], properties[1], brotli_major, brotli_minor
                ),
            )
        self._prefix_checked = False
        self._decompressor = brotli.Decompressor()

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1):
        if not self._prefix_checked:
            # check first 4bytes
            if data[:4] == b"\x50\x2a\x4d\x18":
                raise UnsupportedCompressionMethodError(
                    data[:4], "Unauthorized and modified Brotli data (skipable frame) found."
                )
            self._prefix_checked = True
        return self._decompressor.process(data)


class ZstdCompressor(ISevenZipCompressor):
    def __init__(self, level: int):
        self.compressor = pyzstd.ZstdCompressor(level)

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        return self.compressor.compress(data)

    def flush(self) -> bytes:
        return self.compressor.flush()


class ZstdDecompressor(ISevenZipDecompressor):
    def __init__(self, properties: bytes, blocksize: int):
        if len(properties) not in [3, 5]:
            raise UnsupportedCompressionMethodError(properties, "Zstd takes 3 or 5 bytes properties.")
        if (properties[0], properties[1], 0) > pyzstd.zstd_version_info:
            raise UnsupportedCompressionMethodError(properties, "Zstd version of archive is higher than us.")
        self.decompressor = pyzstd.ZstdDecompressor()

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self.decompressor.decompress(data)


algorithm_class_map = {
    FILTER_ZSTD: (ZstdCompressor, ZstdDecompressor),
    FILTER_BROTLI: (BrotliCompressor, BrotliDecompressor),
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

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        return self._decompressor.decompress(data, max_length)


class SevenZipDecompressor:
    """Main decompressor object which is properly configured and bind to each 7zip folder.
    because 7zip folder can have a custom compression method"""

    def __init__(
        self,
        coders: List[Dict[str, Any]],
        packsize: int,
        unpacksizes: List[int],
        crc: Optional[int],
        password: Optional[str] = None,
        blocksize: Optional[int] = None,
    ) -> None:
        self.input_size = packsize
        self.unpacksizes = unpacksizes
        self.consumed: int = 0
        self.crc = crc
        self.digest: int = 0
        if blocksize:
            self.block_size: int = blocksize
        else:
            self.block_size = get_default_blocksize()
        if len(coders) > 4:
            raise UnsupportedCompressionMethodError(
                coders, "Maximum cascade of filters is 4 but got {}.".format(len(coders))
            )
        self.methods_map = [SupportedMethods.is_native_coder(coder) for coder in coders]  # type: List[bool]
        # Check if password given for encrypted archive
        if SupportedMethods.needs_password(coders) and password is None:
            raise PasswordRequired(coders, "Password is required for extracting given archive.")
        # Check filters combination and required parameters
        if len(coders) >= 2:
            target_compressor = False
            has_bcj = False
            bcj_index = -1
            for i, coder in enumerate(coders):
                filter_id = SupportedMethods.get_filter_id(coder)
                if SupportedMethods.is_compressor_id(filter_id) and filter_id != FILTER_LZMA2:
                    target_compressor = True
                if filter_id in [
                    FILTER_X86,
                    FILTER_ARM,
                    FILTER_ARMTHUMB,
                    FILTER_POWERPC,
                    FILTER_SPARC,
                ]:
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
            raise UnsupportedCompressionMethodError(coders, "Combination order of methods is not supported.")

    def _decompress(self, data, max_length: int):
        for i, decompressor in enumerate(self.chain):
            if self._unpacked[i] < self._unpacksizes[i]:
                if isinstance(decompressor, LZMA1Decompressor) or isinstance(decompressor, PpmdDecompressor):
                    data = decompressor.decompress(data, max_length)  # always give max_length for lzma1
                else:
                    data = decompressor.decompress(data)
                self._unpacked[i] += len(data)
            elif len(data) == 0:
                data = b""
            else:
                raise EOFError
        return data

    def _read_data(self, fp):
        # read data from disk
        # determine read siize
        #    rest_size: rest size of packed data
        #    unused_s: unused packed data size
        #  size to consume for target file is smaller one from
        #    rest_size - unused_s
        #    block_size - unused_s
        rest_size = self.input_size - self.consumed
        unused_s = len(self._unused)
        read_size = min(rest_size - unused_s, self.block_size - unused_s)
        if read_size > 0:
            data = fp.read(read_size)
            self.consumed += len(data)
        else:
            data = b""
        return data

    def decompress(self, fp, max_length: int = -1) -> bytes:
        if max_length < 0:
            data = self._read_data(fp)
            res = self._buf[self._pos :] + self._decompress(self._unused + data, max_length)
            self._buf = bytearray()
            self._unused = bytearray()
            self._pos = 0
        else:
            current_buf_len = len(self._buf) - self._pos
            if current_buf_len >= max_length:  # we already have enough data
                res = self._buf[self._pos : self._pos + max_length]
                self._pos += max_length
            else:
                data = self._read_data(fp)
                if len(self._unused) > 0:
                    tmp = self._decompress(self._unused + data, max_length)
                    self._unused = bytearray()
                else:
                    tmp = self._decompress(data, max_length)
                if current_buf_len + len(tmp) <= max_length:
                    res = self._buf[self._pos :] + tmp
                    self._buf = bytearray()
                    self._pos = 0
                else:
                    res = self._buf[self._pos :] + tmp[: max_length - current_buf_len]
                    self._buf = bytearray(tmp[max_length - current_buf_len :])
                    self._pos = 0
        self.digest = calculate_crc32(res, self.digest)
        return res

    def check_crc(self):
        return self.crc == self.digest

    @property
    def unused_size(self):
        return len(self._unused)

    def _get_lzma_decompressor(self, coders: List[Dict[str, Any]], unpacksize: int):
        filters: List[Dict[str, Any]] = []
        lzma1 = False
        for coder in coders:
            if coder["numinstreams"] != 1 or coder["numoutstreams"] != 1:
                raise UnsupportedCompressionMethodError(coders, "Only a simple compression method is currently supported.")
            if not SupportedMethods.is_native_coder(coder):
                raise UnsupportedCompressionMethodError(coders, "Non python native method is requested.")
            properties = coder.get("properties", None)
            filter_id = SupportedMethods.get_filter_id(coder)
            if filter_id == FILTER_LZMA:
                lzma1 = True
            if properties is not None:
                filters[:0] = [lzma._decode_filter_properties(filter_id, properties)]  # type: ignore
            else:
                filters[:0] = [{"id": filter_id}]
        if lzma1:
            return LZMA1Decompressor(filters, unpacksize)
        else:
            return lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)

    def _get_alternative_decompressor(
        self, coder: Dict[str, Any], unpacksize=None, password=None
    ) -> Union[bz2.BZ2Decompressor, lzma.LZMADecompressor, ISevenZipDecompressor]:  # noqa
        filter_id = SupportedMethods.get_filter_id(coder)
        # Special treatment for BCJ filters
        if filter_id in [
            FILTER_X86,
            FILTER_ARM,
            FILTER_ARMTHUMB,
            FILTER_POWERPC,
            FILTER_SPARC,
        ]:
            return algorithm_class_map[filter_id][1](size=unpacksize)
        # Check supported?
        if SupportedMethods.is_native_coder(coder):
            raise UnsupportedCompressionMethodError(coder, "Unknown method code:{}".format(coder["method"]))
        if filter_id not in algorithm_class_map:
            raise UnsupportedCompressionMethodError(coder, "Unknown method filter_id:{}".format(filter_id))
        if algorithm_class_map[filter_id][1] is None:
            raise UnsupportedCompressionMethodError(
                coder, "Decompression is not supported by {}.".format(SupportedMethods.get_method_name_id(filter_id))
            )
        #
        if SupportedMethods.is_crypto_id(filter_id):
            return algorithm_class_map[filter_id][1](coder["properties"], password, self.block_size)
        elif SupportedMethods.need_property(filter_id):
            return algorithm_class_map[filter_id][1](coder["properties"], self.block_size)
        else:
            return algorithm_class_map[filter_id][1]()


class SevenZipCompressor:
    """Main compressor object to configured for each 7zip folder."""

    __slots__ = [
        "filters",
        "chain",
        "compressor",
        "coders",
        "methods_map",
        "digest",
        "packsize",
        "_block_size",
        "_unpacksizes",
    ]

    def __init__(self, filters=None, password=None, blocksize: Optional[int] = None):
        self.filters: List[Dict[str, Any]] = []
        self.chain: List[ISevenZipCompressor] = []
        self.digest = 0
        self.packsize = 0
        self._unpacksizes: List[int] = []
        if blocksize:
            self._block_size = blocksize
        else:
            self._block_size = get_default_blocksize()
        if filters is None:
            self.filters = [{"id": lzma.FILTER_LZMA2, "preset": 7 | lzma.PRESET_EXTREME}]
        else:
            self.filters = filters
        if len(self.filters) > 4:
            raise UnsupportedCompressionMethodError(
                filters, "Maximum cascade of filters is 4 but got {}.".format(len(self.filters))
            )
        self.methods_map = [SupportedMethods.is_native_filter(filter) for filter in self.filters]
        self.coders: List[Dict[str, Any]] = []
        if all(self.methods_map) and SupportedMethods.is_compressor(self.filters[-1]):  # all native
            self._set_native_compressors_coders(self.filters)
            return
        #
        has_lzma2 = False
        for f in self.filters:
            if f["id"] == FILTER_LZMA2:
                has_lzma2 = True
                break
        if not has_lzma2:
            # when specified other than lzma2, BCJ filters should be alternative
            for i, f in enumerate(self.filters):
                if (
                    f["id"] == FILTER_X86
                    or f["id"] == FILTER_ARM
                    or f["id"] == FILTER_ARMTHUMB
                    or f["id"] == FILTER_SPARC
                    or f["id"] == FILTER_POWERPC
                ):
                    self.methods_map[i] = False
        #
        if not any(self.methods_map):  # all alternative
            for f in filters:
                self._set_alternate_compressors_coders(f, password)
        elif SupportedMethods.is_crypto_id(self.filters[-1]["id"]) and all(self.methods_map[:-1]):
            self._set_native_compressors_coders(self.filters[:-1])
            self._set_alternate_compressors_coders(self.filters[-1], password)
        else:
            raise UnsupportedCompressionMethodError(filters, "Unknown combination of methods.")

    def _set_native_compressors_coders(self, filters):
        self.chain.append(lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filters))
        self._unpacksizes.append(0)
        for filter in filters:
            self.coders.insert(0, SupportedMethods.get_coder(filter))

    def _set_alternate_compressors_coders(self, alt_filter, password=None):
        filter_id = alt_filter["id"]
        properties = None
        if filter_id not in algorithm_class_map:
            raise UnsupportedCompressionMethodError(filter_id, "Unknown filter_id is given.")
        elif SupportedMethods.is_crypto_id(filter_id):
            compressor = algorithm_class_map[filter_id][0](password)
        elif SupportedMethods.need_property(filter_id):
            if filter_id == FILTER_ZSTD:
                level = alt_filter.get("level", 3)
                properties = struct.pack("BBBBB", pyzstd.zstd_version_info[0], pyzstd.zstd_version_info[1], level, 0, 0)
                compressor = algorithm_class_map[filter_id][0](level=level)
            elif filter_id == FILTER_PPMD:
                properties = PpmdCompressor.encode_filter_properties(alt_filter)
                compressor = algorithm_class_map[filter_id][0](properties)
            elif filter_id == FILTER_BROTLI:
                level = alt_filter.get("level", 11)
                properties = struct.pack("BBB", brotli_major, brotli_minor, level)
                compressor = algorithm_class_map[filter_id][0](level)
        else:
            compressor = algorithm_class_map[filter_id][0]()
        if SupportedMethods.is_crypto_id(filter_id):
            properties = compressor.encode_filter_properties()
        self.chain.append(compressor)
        self._unpacksizes.append(0)
        self.coders.insert(
            0,
            {
                "method": SupportedMethods.get_method_id(filter_id),
                "properties": properties,
                "numinstreams": 1,
                "numoutstreams": 1,
            },
        )

    def compress(self, fd, fp, crc=0):
        data = fd.read(self._block_size)
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
            data = fd.read(self._block_size)
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

    formats = [{"name": "7z", "magic": MAGIC_7Z}]
    methods = [
        {
            "id": COMPRESSION_METHOD.COPY,
            "name": "COPY",
            "native": False,
            "need_prop": False,
            "filter_id": FILTER_COPY,
            "type": MethodsType.compressor,
        },
        {
            "id": COMPRESSION_METHOD.LZMA2,
            "name": "LZMA2",
            "native": True,
            "need_prop": True,
            "filter_id": FILTER_LZMA2,
            "type": MethodsType.compressor,
        },
        {
            "id": COMPRESSION_METHOD.DELTA,
            "name": "DELTA",
            "native": True,
            "need_prop": True,
            "filter_id": FILTER_DELTA,
            "type": MethodsType.filter,
        },
        {
            "id": COMPRESSION_METHOD.LZMA,
            "name": "LZMA",
            "native": True,
            "need_prop": True,
            "filter_id": FILTER_LZMA,
            "type": MethodsType.compressor,
        },
        {
            "id": COMPRESSION_METHOD.P7Z_BCJ,
            "name": "BCJ",
            "native": True,
            "need_prop": False,
            "filter_id": FILTER_X86,
            "type": MethodsType.filter,
        },
        {
            "id": COMPRESSION_METHOD.BCJ_PPC,
            "name": "PPC",
            "native": True,
            "need_prop": False,
            "filter_id": FILTER_POWERPC,
            "type": MethodsType.filter,
        },
        {
            "id": COMPRESSION_METHOD.BCJ_IA64,
            "name": "IA64",
            "native": True,
            "need_prop": False,
            "filter_id": FILTER_IA64,
            "type": MethodsType.filter,
        },
        {
            "id": COMPRESSION_METHOD.BCJ_ARM,
            "name": "ARM",
            "native": True,
            "need_prop": False,
            "filter_id": FILTER_ARM,
            "type": MethodsType.filter,
        },
        {
            "id": COMPRESSION_METHOD.BCJ_ARMT,
            "name": "ARMT",
            "native": True,
            "need_prop": False,
            "filter_id": FILTER_ARMTHUMB,
            "type": MethodsType.filter,
        },
        {
            "id": COMPRESSION_METHOD.BCJ_SPARC,
            "name": "SPARC",
            "native": True,
            "need_prop": False,
            "filter_id": FILTER_SPARC,
            "type": MethodsType.filter,
        },
        {
            "id": COMPRESSION_METHOD.MISC_DEFLATE,
            "name": "DEFLATE",
            "native": False,
            "need_prop": False,
            "filter_id": FILTER_DEFLATE,
            "type": MethodsType.compressor,
        },
        {
            "id": COMPRESSION_METHOD.MISC_BZIP2,
            "name": "BZip2",
            "native": False,
            "need_prop": False,
            "filter_id": FILTER_BZIP2,
            "type": MethodsType.compressor,
        },
        {
            "id": COMPRESSION_METHOD.MISC_ZSTD,
            "name": "ZStandard",
            "native": False,
            "need_prop": True,
            "filter_id": FILTER_ZSTD,
            "type": MethodsType.compressor,
        },
        {
            "id": COMPRESSION_METHOD.PPMD,
            "name": "PPMd",
            "native": False,
            "need_prop": True,
            "filter_id": FILTER_PPMD,
            "type": MethodsType.compressor,
        },
        {
            "id": COMPRESSION_METHOD.MISC_BROTLI,
            "name": "Brotli",
            "native": False,
            "need_prop": True,
            "filter_id": FILTER_BROTLI,
            "type": MethodsType.compressor,
        },
        {
            "id": COMPRESSION_METHOD.CRYPT_AES256_SHA256,
            "name": "7zAES",
            "native": False,
            "need_prop": True,
            "filter_id": FILTER_CRYPTO_AES256_SHA256,
            "type": MethodsType.crypto,
        },
    ]

    @classmethod
    def _find_method(cls, key_id, key_value):
        return next((item for item in cls.methods if item[key_id] == key_value), None)

    @classmethod
    def get_method_name_id(cls, filter_id):
        method = cls._find_method("filter_id", filter_id)
        return method["name"]

    @classmethod
    def get_filter_id(cls, coder):
        method = cls._find_method("id", coder["method"])
        if method is None:
            return None
        return method["filter_id"]

    @classmethod
    def is_native_filter(cls, filter) -> bool:
        method = cls._find_method("filter_id", filter["id"])
        if method is None:
            raise UnsupportedCompressionMethodError(filter["id"], "Unknown method id is given.")
        return method["native"]

    @classmethod
    def is_compressor(cls, filter):
        method = cls._find_method("filter_id", filter["id"])
        return method["type"] == MethodsType.compressor

    @classmethod
    def is_compressor_id(cls, filter_id):
        method = cls._find_method("filter_id", filter_id)
        return method["type"] == MethodsType.compressor

    @classmethod
    def is_native_coder(cls, coder) -> bool:
        method = cls._find_method("id", coder["method"])
        if method is None:
            raise UnsupportedCompressionMethodError(coder["method"], "Found an unknown id of method.")
        return method["native"]

    @classmethod
    def need_property(cls, filter_id):
        method = cls._find_method("filter_id", filter_id)
        if method is None:
            raise UnsupportedCompressionMethodError(filter_id, "Found an unknown filter id.")
        return method["need_prop"]

    @classmethod
    def is_crypto_id(cls, filter_id) -> bool:
        method = cls._find_method("filter_id", filter_id)
        if method is None:
            raise UnsupportedCompressionMethodError(filter_id, "Found an unknown filter id.")
        return method["type"] == MethodsType.crypto

    @classmethod
    def get_method_id(cls, filter_id) -> bytes:
        method = cls._find_method("filter_id", filter_id)
        if method is None:
            raise UnsupportedCompressionMethodError(filter_id, "Found an unknown filter id.")
        return method["id"]

    @classmethod
    def get_coder(cls, filter) -> Dict[str, Any]:
        method = cls.get_method_id(filter["id"])
        if filter["id"] in [lzma.FILTER_LZMA1, lzma.FILTER_LZMA2, lzma.FILTER_DELTA]:
            properties: Optional[bytes] = lzma._encode_filter_properties(filter)  # type: ignore  # noqa
        else:
            properties = None
        return {
            "method": method,
            "properties": properties,
            "numinstreams": 1,
            "numoutstreams": 1,
        }

    @classmethod
    def needs_password(cls, coders) -> bool:
        for coder in coders:
            filter_id = SupportedMethods.get_filter_id(coder)
            if filter_id is None:
                continue
            if SupportedMethods.is_crypto_id(filter_id):
                return True
        return False


def get_methods_names(coders_lists: List[List[dict]]) -> List[str]:
    # list of known method names with a display priority order

    methods_namelist = [
        "LZMA2",
        "LZMA",
        "BZip2",
        "DEFLATE",
        "DEFLATE64*",
        "delta",
        "COPY",
        "PPMd",
        "ZStandard",
        "LZ4*",
        "BCJ2*",
        "BCJ",
        "ARM",
        "ARMT",
        "IA64",
        "PPC",
        "SPARC",
        "7zAES",
    ]
    unsupported_methods = {
        COMPRESSION_METHOD.P7Z_BCJ2: "BCJ2*",
        COMPRESSION_METHOD.MISC_LZ4: "LZ4*",
        COMPRESSION_METHOD.MISC_DEFLATE64: "DEFLATE64*",
    }
    methods_names = []
    for coders in coders_lists:
        for coder in coders:
            for m in SupportedMethods.methods:
                if coder["method"] == m["id"]:
                    methods_names.append(m["name"])
            if coder["method"] in unsupported_methods:
                methods_names.append(unsupported_methods[coder["method"]])
    return list(filter(lambda x: x in methods_names, methods_namelist))
