#!/usr/bin/python -u
#
# p7zr library
#
# Copyright (c) 2019-2021 Hiroshi Miura <miurahr@linux.com>
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

from typing import Union

import zstandard

from py7zr.exceptions import UnsupportedCompressionMethodError
from py7zr.helpers import BufferedRW

ZSTD_VERSION = zstandard.ZSTD_VERSION


class ZstdDecompressor():

    def __init__(self, properties):
        if len(properties) not in [3, 5] or (properties[0], properties[1], 0) > ZSTD_VERSION:
            raise UnsupportedCompressionMethodError
        self._buf = BufferedRW()
        ctx = zstandard.ZstdDecompressor()  # type: ignore
        self._decompressor = ctx.stream_writer(self._buf)

    def decompress(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        self._decompressor.write(data)
        if max_length > 0:
            result = self._buf.read(max_length)
        else:
            result = self._buf.read()
        return result


class ZstdCompressor():

    def __init__(self, level):
        self._buf = BufferedRW()
        ctx = zstandard.ZstdCompressor(level)  # type: ignore
        self._compressor = ctx.stream_writer(self._buf)
        self.flushed = False

    def compress(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        self._compressor.write(data)
        result = self._buf.read()
        return result

    def flush(self):
        if self.flushed:
            return None
        self._compressor.flush(zstandard.FLUSH_FRAME)
        self.flushed = True
        result = self._buf.read()
        return result
