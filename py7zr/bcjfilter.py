#
# p7zr library
#
# Copyright (c) 2019,2020 Hiroshi Miura <miurahr@linux.com>
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
import struct
from typing import Union


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

    def sparc_code(self):
        limit = len(self.buffer) - 4
        i = 0
        while i <= limit:
            if (self.buffer[i], self.buffer[i + 1] & 0xC0) in [
                (0x40, 0x00),
                (0x7F, 0xC0),
            ]:
                src = struct.unpack(">L", self.buffer[i : i + 4])[0] << 2
                distance = self.current_position + i
                if self.is_encoder:
                    dest = (src + distance) >> 2
                else:
                    dest = (src - distance) >> 2
                dest = (((0 - ((dest >> 22) & 1)) << 22) & 0x3FFFFFFF) | (dest & 0x3FFFFF) | 0x40000000
                self.buffer[i : i + 4] = struct.pack(">L", dest)
            i += 4
        self.current_position = i
        return i

    def ppc_code(self):
        limit = len(self.buffer) - 4
        i = 0
        while i <= limit:
            # PowerPC branch 6(48) 24(Offset) 1(Abs) 1(Link)
            distance = self.current_position + i
            if self.buffer[i] & 0xFC == 0x48 and self.buffer[i + 3] & 0x03 == 1:
                src = struct.unpack(">L", self.buffer[i : i + 4])[0] & 0x3FFFFFC
                if self.is_encoder:
                    dest = src + distance
                else:
                    dest = src - distance
                # lsb = int(self.buffer[i + 3]) & 0x03 == 1
                dest = (0x48 << 24) | (dest & 0x03FFFFFF) | 1
                self.buffer[i : i + 4] = struct.pack(">L", dest)
            i += 4
        self.current_position = i
        return i

    def _unpack_thumb(self, b: Union[bytearray, bytes, memoryview]) -> int:
        return ((b[1] & 0x07) << 19) | (b[0] << 11) | ((b[3] & 0x07) << 8) | b[2]

    def _pack_thumb(self, val: int):
        b = bytes(
            [
                (val >> 11) & 0xFF,
                0xF0 | ((val >> 19) & 0x07),
                val & 0xFF,
                0xF8 | ((val >> 8) & 0x07),
            ]
        )
        return b

    def armt_code(self) -> int:
        limit = len(self.buffer) - 4
        i = 0
        while i <= limit:
            if self.buffer[i + 1] & 0xF8 == 0xF0 and self.buffer[i + 3] & 0xF8 == 0xF8:
                src = self._unpack_thumb(self.buffer[i : i + 4]) << 1
                distance = self.current_position + i + 4
                if self.is_encoder:
                    dest = src + distance
                else:
                    dest = src - distance
                dest >>= 1
                self.buffer[i : i + 4] = self._pack_thumb(dest)
                i += 2
            i += 2
        self.current_position += i
        return i

    def arm_code(self) -> int:
        limit = len(self.buffer) - 4
        i = 0
        while i <= limit:
            if self.buffer[i + 3] == 0xEB:
                src = struct.unpack("<L", self.buffer[i : i + 3] + b"\x00")[0] << 2
                distance = self.current_position + i + 8
                if self.is_encoder:
                    dest = (src + distance) >> 2
                else:
                    dest = (src - distance) >> 2
                self.buffer[i : i + 3] = struct.pack("<L", dest & 0xFFFFFF)[:3]
            i += 4
        self.current_position += i
        return i

    def x86_code(self) -> int:
        """
        The code algorithm from liblzma/simple/x86.c
        It is slightly different from LZMA-SDK's bra86.c
        :return: buffer position
        """
        size = len(self.buffer)
        if size < 5:
            return 0
        if self.current_position - self.prev_pos > 5:
            self.prev_pos = self.current_position - 5
        view = memoryview(self.buffer)
        limit = size - 5
        buffer_pos = 0
        pos1 = 0
        pos2 = 0
        while buffer_pos <= limit:
            # --
            # The following is pythonic way as same as
            # if self.buffer[buffer_pos] not in [0xe9, 0xe8]:
            #    buffer_pos += 1
            #     continue
            # --
            if pos1 >= 0:
                pos1 = self.buffer.find(0xE9, buffer_pos, limit)
            if pos2 >= 0:
                pos2 = self.buffer.find(0xE8, buffer_pos, limit)
            if pos1 < 0 and pos2 < 0:
                buffer_pos = limit + 1
                break
            elif pos1 < 0:
                buffer_pos = pos2
            elif pos2 < 0:
                buffer_pos = pos1
            else:
                buffer_pos = min(pos1, pos2)
            # --
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
            if view[buffer_pos + 4] in [0, 0xFF] and (self.prev_mask >> 1) in self._mask_to_allowed_number:
                jump_target = self.buffer[buffer_pos + 1 : buffer_pos + 5]
                src = struct.unpack("<L", jump_target)[0]
                distance = self.current_position + buffer_pos + 5
                idx = self._mask_to_bit_number[self.prev_mask >> 1]
                while True:
                    if self.is_encoder:
                        dest = (src + distance) & 0xFFFFFFFF  # uint32 behavior
                    else:
                        dest = (src - distance) & 0xFFFFFFFF
                    if self.prev_mask == 0:
                        break
                    b = 0xFF & (dest >> (24 - idx * 8))
                    if not (b == 0 or b == 0xFF):
                        break
                    src = dest ^ ((1 << (32 - idx * 8)) - 1) & 0xFFFFFFFF
                write_view = view[buffer_pos + 1 : buffer_pos + 5]
                write_view[0:3] = (dest & 0xFFFFFF).to_bytes(3, "little")
                write_view[3:4] = [b"\x00", b"\xff"][(dest >> 24) & 1]  # (~(((dest >> 24) & 1) - 1)) & 0xFF
                buffer_pos += 5
                self.prev_mask = 0
            else:
                buffer_pos += 1
                self.prev_mask |= 1
                if self.buffer[buffer_pos + 3] in [0, 0xFF]:
                    self.prev_mask |= 0x10
        self.current_position += buffer_pos
        return buffer_pos

    def decode(self, data: Union[bytes, bytearray, memoryview], max_length: int = -1) -> bytes:
        self.buffer.extend(data)
        pos = self._method()
        if self.current_position > self.stream_size - self._readahead:
            offset = self.stream_size - self.current_position
            tmp = bytes(self.buffer[: pos + offset])
            self.current_position = self.stream_size
            self.buffer = bytearray()
        else:
            tmp = bytes(self.buffer[:pos])
            self.buffer = self.buffer[pos:]
        return tmp

    def encode(self, data: Union[bytes, bytearray, memoryview]) -> bytes:
        self.buffer.extend(data)
        pos = self._method()
        tmp = bytes(self.buffer[:pos])
        self.buffer = self.buffer[pos:]
        return tmp

    def flush(self):
        return bytes(self.buffer)


class BCJDecoder(BCJFilter):
    def __init__(self, size: int):
        super().__init__(self.x86_code, 5, False, size)


class BCJEncoder(BCJFilter):
    def __init__(self):
        super().__init__(self.x86_code, 5, True)


class SparcDecoder(BCJFilter):
    def __init__(self, size: int):
        super().__init__(self.sparc_code, 4, False, size)


class SparcEncoder(BCJFilter):
    def __init__(self):
        super().__init__(self.sparc_code, 4, True)


class PPCDecoder(BCJFilter):
    def __init__(self, size: int):
        super().__init__(self.ppc_code, 4, False, size)


class PPCEncoder(BCJFilter):
    def __init__(self):
        super().__init__(self.ppc_code, 4, True)


class ARMTDecoder(BCJFilter):
    def __init__(self, size: int):
        super().__init__(self.armt_code, 4, False, size)


class ARMTEncoder(BCJFilter):
    def __init__(self):
        super().__init__(self.armt_code, 4, True)


class ARMDecoder(BCJFilter):
    def __init__(self, size: int):
        super().__init__(self.arm_code, 4, False, size)


class ARMEncoder(BCJFilter):
    def __init__(self):
        super().__init__(self.arm_code, 4, True)
