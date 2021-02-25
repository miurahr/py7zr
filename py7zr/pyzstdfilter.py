#!/usr/bin/python -u
#
# p7zr library
#
# Copyright (c) 2021 Hiroshi Miura <miurahr@linux.com>
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

import pyzstd

from py7zr.exceptions import UnsupportedCompressionMethodError

ZSTD_VERSION = (1, 4, 8)


class ZstdCompressor:

    def __init__(self, level):
        self.compressor = pyzstd.ZstdCompressor(level)

    def compress(self, data):
        return self.compressor.compress(data)

    def flush(self):
        return self.compressor.flush()


class ZstdDecompressor:

    def __init__(self, properties):
        if len(properties) not in [3, 5] or (properties[0], properties[1], 0) > ZSTD_VERSION:
            raise UnsupportedCompressionMethodError
        self.decompressor = pyzstd.ZstdDecompressor()

    def decompress(self, data):
        return self.decompressor.decompress(data)
