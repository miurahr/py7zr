#!/usr/bin/python -u
#
# p7zr library
#
# Copyright (c) 2019 Hiroshi Miura <miurahr@linux.com>
# Copyright (c) 2004-2015 by Joachim Bauch, mail@joachim-bauch.de
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
#

import struct
import sys
import time as _time
from binascii import unhexlify
from datetime import datetime, timedelta, timezone, tzinfo
from functools import reduce
from zlib import crc32
from array import array
from struct import unpack


NEED_BYTESWAP = sys.byteorder != 'little'


if array('L').itemsize == 4:
    ARRAY_TYPE_UINT32 = 'L'
else:
    assert array('I').itemsize == 4
    ARRAY_TYPE_UINT32 = 'I'


def read_crc(file, count):
    crcs = array(ARRAY_TYPE_UINT32, file.read(4 * count))
    if NEED_BYTESWAP:
        crcs.byteswap()
    return crcs


def read_real_uint64(file):
    res = file.read(8)
    a, b = unpack('<LL', res)
    return b << 32 | a, res


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
    barray = encode_uint64(value)
    file.write(barray)


def encode_uint64(value):
    mask = 0x80
    mv = memoryview(convert_to_bytearray(value))
    l = len(mv.tobytes())
    format = 'c'
    for i in range(l - 1):
        mask |= mask >> 1
        format += 'c'
    if mv[0] >= 2 ** (8 - l):
        pass
    elif l == 1:
        mv[0] &= ~mask
        return struct.pack(format, mv.tobytes())
    else:
        mv[0] |= mask
        return struct.pack(format, mv.tobytes())


def convert_to_bytearray(value):
    bytelen = 0
    v = value
    while v > 0:
        v >>= 8
        bytelen += 1
    return bytearray(value.to_bytes(bytelen, 'big'))


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


def checkcrc(crc, data):
    check = calculate_crc32(data)
    return crc == check


def calculate_crc32(data, value=None, blocksize=1024 * 1024):
    """Calculate CRC32 of strings with arbitrary lengths."""
    length = len(data)
    pos = blocksize
    if value:
        value = crc32(data[:pos], value)
    else:
        value = crc32(data[:pos])
    while pos < length:
        value = crc32(data[pos:pos + blocksize], value)
        pos += blocksize

    return value & 0xffffffff


EPOCH_AS_FILETIME = 116444736000000000


def filetime_to_dt(ft):
    us = (ft - EPOCH_AS_FILETIME) // 10
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=us)


ZERO = timedelta(0)
HOUR = timedelta(hours=1)
SECOND = timedelta(seconds=1)

# A class capturing the platform's idea of local time.
# (May result in wrong values on historical times in
#  timezones where UTC offset and/or the DST rules had
#  changed in the past.)

STDOFFSET = timedelta(seconds=-_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds=-_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET


class LocalTimezone(tzinfo):

    def fromutc(self, dt):
        assert dt.tzinfo is self
        stamp = (dt - datetime(1970, 1, 1, tzinfo=self)) // SECOND
        args = _time.localtime(stamp)[:6]
        dst_diff = DSTDIFF // SECOND
        # Detect fold
        fold = (args == _time.localtime(stamp - dst_diff))
        return datetime(*args, microsecond=dt.microsecond, tzinfo=self)

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0


Local = LocalTimezone()
TIMESTAMP_ADJUST = -11644473600


class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

    def _call__(self):
        return self


UTC = UTC()


class ArchiveTimestamp(int):
    """Windows FILETIME timestamp."""

    def __repr__(self):
        return '%s(%d)' % (type(self).__name__, self)

    def totimestamp(self):
        """Convert 7z FILETIME to Python timestamp."""
        # FILETIME is 100-nanosecond intervals since 1601/01/01 (UTC)
        return (self / 10000000.0) + TIMESTAMP_ADJUST

    def as_datetime(self):
        """Convert FILETIME to Python datetime object."""
        return datetime.fromtimestamp(self.totimestamp(), UTC)
