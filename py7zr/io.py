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
import sys
from array import array
from binascii import unhexlify
from functools import reduce
from struct import pack, unpack
from operator import and_


NEED_BYTESWAP = sys.byteorder != 'little'

if array('L').itemsize == 4:
    ARRAY_TYPE_UINT32 = 'L'
    pass
else:
    assert array('I').itemsize == 4
    ARRAY_TYPE_UINT32 = 'I'


def read_crcs(file, count):
    crcs = array(ARRAY_TYPE_UINT32, file.read(4 * count))
    if NEED_BYTESWAP:
        crcs.byteswap()
    return crcs


def write_crcs(file, crcs):
    for crc in crcs:
        write_uint32(file, crc)

def read_bytes(file, length):
    return unpack(b'B' * length, file.read(length))


def read_byte(file):
    return ord(file.read(1))


def write_bytes(file, data):
    assert len(data) > 0
    if isinstance(data, bytes):
        file.write(data)
    elif isinstance(data, bytearray):
        file.write(pack(b'B' * len(data), data))
    else:
        raise


def write_byte(file, data):
    assert len(data) == 1
    file.write(pack('B', data))


def read_real_uint64(file):
    res = file.read(8)
    a, b = unpack('<LL', res)
    return b << 32 | a, res


def read_uint32(file):
    res = file.read(4)
    a = unpack('<L', res)[0]
    return a, res


def write_uint32(file, value):
    b = pack('<L', value)
    file.write(b)


def read_uint64(file):
    """
    UINT64 means real UINT64 encoded with the following scheme:

      Size of encoding sequence depends from first byte:
      First_Byte  Extra_Bytes        Value
      (binary)
      0xxxxxxx               : ( xxxxxxx           )
      10xxxxxx    BYTE y[1]  : (  xxxxxx << (8 * 1)) + y
      110xxxxx    BYTE y[2]  : (   xxxxx << (8 * 2)) + y
      ...
      1111110x    BYTE y[6]  : (       x << (8 * 6)) + y
      11111110    BYTE y[7]  :                         y
      11111111    BYTE y[8]  :                         y
    """
    b = ord(file.read(1))
    mask = 0x80
    for i in range(8):
        if b & mask == 0:
            bytes = array('B', file.read(i))
            bytes.reverse()
            value = (bytes and reduce(lambda x, y: x << 8 | y, bytes)) or 0
            highpart = b & (mask - 1)
            return value + (highpart << (i * 8))
        mask >>= 1


def write_uint64(file, value):
    file.write(encode_uint64(value))


def write_real_uint64(file, value):
    file.write(encode_real_uint64(value))


def encode_uint64(value):
    mask = 0x80
    ba = bytearray(value.to_bytes(bytelen(value), 'big'))
    for i in range(len(ba) - 1):
        mask |= mask >> 1
    if ba[0] >= 2 ** (8 - len(ba)):
        return ba.rjust(len(ba) + 1, mask.to_bytes(1, 'big'))
    elif len(ba) > 1:
        ba[0] |= mask
    else:
        pass
    return ba


def bytelen(value):
    bitwidth = value.bit_length()
    return bitwidth // 8 + (0 if bitwidth % 8 == 0 else 1)


def encode_real_uint64(value):
    return value.to_bytes(8, 'big')


def read_boolean(file, count, checkall=0):
    if checkall:
        all_defined = file.read(1)
        if all_defined != unhexlify('00'):
            return [True] * count
    result = []
    b = 0
    mask = 0
    for i in range(count):
        if mask == 0:
            b = ord(file.read(1))
            mask = 0x80
        result.append(b & mask != 0)
        mask >>= 1
    return result


def write_boolean(file, booleans, all_defined=True):
    if all_defined and reduce(and_, booleans):
        file.write(b'\xff')
        return
    elif all_defined:
        file.write(b'\x00')
    mask = 0x80
    o = 0x00
    for b in booleans:
        if mask == 0:
            file.write(o)
            mask = 0x80
            o = 0x00
        else:
            o |= mask if b else 0x00
            mask >>= 1
    if mask != 0x80:
        file.write(o)
