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
import lzma
import zlib
from typing import Any, Dict, List, Optional

from Crypto.Cipher import AES
from py7zr import UnsupportedCompressionMethodError
from py7zr.helpers import calculate_key
from py7zr.properties import CompressionMethod


class DeflateDecompressor:
    def __init__(self):
        self.buf = b''
        self._decompressor = zlib.decompressobj(-15)

    def decompress(self, data: bytes, max_length: Optional[int] = None):
        dec = self._decompressor.decompress(data)
        if max_length is None:
            res = self.buf + dec
            self.buf = b''
        else:
            tmp = self.buf + dec
            res = tmp[:max_length]
            self.buf = tmp[max_length:]
        return res


class CopyDecompressor:

    def __init__(self):
        self.buf = b''

    def decompress(self, data: bytes, max_length: Optional[int] = None) -> bytes:
        if max_length is None:
            length = len(data)
        else:
            length = min(len(data), max_length)
        buflen = len(self.buf)
        if length > buflen:
            res = self.buf + data[:length - buflen]
            self.buf = data[length - buflen:]
        else:
            res = self.buf[:length]
            self.buf = self.buf[length:] + data
        return res


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
