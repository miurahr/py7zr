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

import hashlib
import os
import stat
import struct
import sys
import time as _time
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Optional
from zlib import crc32

if sys.platform == "win32":
    from win32file import (CloseHandle, CreateFileW, DeviceIoControl, GENERIC_READ, GetFileAttributes,  # noqa
                           OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, FILE_FLAG_OPEN_REPARSE_POINT)
    from winioctlcon import FSCTL_GET_REPARSE_POINT  # noqa


def calculate_crc32(data: bytes, value: Optional[int] = None, blocksize: int = 1024 * 1024) -> int:
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


def calculate_key(password: bytes, cycles: int, salt: bytes, digest: str) -> bytes:
    assert digest == 'sha256'
    if cycles == 0x3f:
        ba = bytearray()
        ba.extend(salt)
        ba.extend(password)
        for i in range(32):
            ba.append(0)
        key = bytes(ba[:32])  # type: bytes
    else:
        rounds = 1 << cycles
        m = hashlib.sha256()
        for round in range(rounds):
            m.update(salt)
            m.update(password)
            m.update(round.to_bytes(8, byteorder='little', signed=False))
        key = m.digest()[:32]
    return key


EPOCH_AS_FILETIME = 116444736000000000


def filetime_to_dt(ft):
    """Convert Windows NTFS file time into python datetime object."""
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


class ArchiveTimestamp(int):
    """Windows FILETIME timestamp."""

    def __repr__(self):
        return '%s(%d)' % (type(self).__name__, self)

    def totimestamp(self) -> float:
        """Convert 7z FILETIME to Python timestamp."""
        # FILETIME is 100-nanosecond intervals since 1601/01/01 (UTC)
        return (self / 10000000.0) + TIMESTAMP_ADJUST

    def as_datetime(self):
        """Convert FILETIME to Python datetime object."""
        return datetime.fromtimestamp(self.totimestamp(), UTC())

    @staticmethod
    def from_datetime(val):
        return ArchiveTimestamp((val - TIMESTAMP_ADJUST) * 10000000.0)


def _check_bit(val, flag):
    return bool(val & flag == flag)


def islink(path):
    """
    Cross-platform islink implementation.
    Supports Windows NT symbolic links and reparse points.
    """
    if sys.platform != "win32" or sys.getwindowsversion()[0] < 6:
        return os.path.islink(path)
    return os.path.exists(path) and _check_bit(GetFileAttributes(path), stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _parse_reparse_buffer(buf):
    """ Implementing the below in Python:

    typedef struct _REPARSE_DATA_BUFFER {
        ULONG  ReparseTag;
        USHORT ReparseDataLength;
        USHORT Reserved;
        union {
            struct {
                USHORT SubstituteNameOffset;
                USHORT SubstituteNameLength;
                USHORT PrintNameOffset;
                USHORT PrintNameLength;
                ULONG Flags;
                WCHAR PathBuffer[1];
            } SymbolicLinkReparseBuffer;
            struct {
                USHORT SubstituteNameOffset;
                USHORT SubstituteNameLength;
                USHORT PrintNameOffset;
                USHORT PrintNameLength;
                WCHAR PathBuffer[1];
            } MountPointReparseBuffer;
            struct {
                UCHAR  DataBuffer[1];
            } GenericReparseBuffer;
        } DUMMYUNIONNAME;
    } REPARSE_DATA_BUFFER, *PREPARSE_DATA_BUFFER;
    """
    # See https://docs.microsoft.com/en-us/windows-hardware/drivers/ddi/content/ntifs/ns-ntifs-_reparse_data_buffer

    data = {'tag': struct.unpack('<I', buf[:4])[0],
            'data_length': struct.unpack('<H', buf[4:6])[0],
            'reserved': struct.unpack('<H', buf[6:8])[0]}
    buf = buf[8:]

    if data['tag'] in (stat.IO_REPARSE_TAG_MOUNT_POINT, stat.IO_REPARSE_TAG_SYMLINK):
        keys = ['substitute_name_offset',
                'substitute_name_length',
                'print_name_offset',
                'print_name_length']
        if data['tag'] == stat.IO_REPARSE_TAG_SYMLINK:
            keys.append('flags')

        # Parsing
        for k in keys:
            if k == 'flags':
                fmt, sz = '<I', 4
            else:
                fmt, sz = '<H', 2
            data[k] = struct.unpack(fmt, buf[:sz])[0]
            buf = buf[sz:]

    # Using the offset and lengths grabbed, we'll set the buffer.
    data['buffer'] = buf

    return data


def readlink(path, *, dir_fd=None):
    """
    Cross-platform implementation of readlink for Python < 3.8
    Supports Windows NT symbolic links and reparse points.
    """
    if sys.platform != "win32":
        return os.readlink(path, dir_fd=dir_fd)

    if not os.path.exists(path):
        raise OSError(22, 'Invalid argument', path)

    if islink(path):  # may be a symbolic link.
        return os.readlink(path, dir_fd=dir_fd)

    if sys.version_info >= (3, 8):
        rpath = os.readlink(path, dir_fd=dir_fd)
    else:
        # FILE_FLAG_OPEN_REPARSE_POINT alone is not enough if 'path'
        # is a symbolic link to a directory or a NTFS junction.
        # We need to set FILE_FLAG_BACKUP_SEMANTICS as well.
        # See https://docs.microsoft.com/en-us/windows/desktop/api/fileapi/nf-fileapi-createfilea
        handle = CreateFileW(path, GENERIC_READ, 0, None, OPEN_EXISTING,
                             FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, 0)
        MAXIMUM_REPARSE_DATA_BUFFER_SIZE = 16 * 1024
        buf = DeviceIoControl(handle, FSCTL_GET_REPARSE_POINT, None, MAXIMUM_REPARSE_DATA_BUFFER_SIZE)
        CloseHandle(handle)
        result = _parse_reparse_buffer(buf)
        if result['tag'] in (stat.IO_REPARSE_TAG_MOUNT_POINT, stat.IO_REPARSE_TAG_SYMLINK):
            offset = result['substitute_name_offset']
            ending = offset + result['substitute_name_length']
            rpath = result['buffer'][offset:ending].decode('UTF-16-LE')
        else:
            rpath = result['buffer']
        if result['tag'] == stat.IO_REPARSE_TAG_MOUNT_POINT:
            rpath[:0] = '\\??\\'
    return rpath
