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

import functools
import io
import os
import struct
from binascii import unhexlify
from functools import reduce
from io import BytesIO
from operator import and_, or_
from struct import pack, unpack
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

from py7zr.compression import SevenZipCompressor, SevenZipDecompressor
from py7zr.exceptions import Bad7zFile, UnsupportedCompressionMethodError
from py7zr.helpers import ArchiveTimestamp, calculate_crc32
from py7zr.properties import (MAGIC_7Z, CompressionMethod, Configuration,
                              Property)

MAX_LENGTH = 65536


def read_crcs(file: BinaryIO, count: int) -> List[int]:
    data = file.read(4 * count)
    return [unpack('<L', data[i * 4:i * 4 + 4])[0] for i in range(count)]


def write_crcs(file: BinaryIO, crcs):
    for crc in crcs:
        write_uint32(file, crc)


def read_bytes(file: BinaryIO, length: int) -> Tuple[bytes, ...]:
    return unpack(b'B' * length, file.read(length))


def read_byte(file: BinaryIO) -> int:
    return ord(file.read(1))


def write_bytes(file: BinaryIO, data):
    if isinstance(data, bytes):
        return file.write(data)
    elif isinstance(data, bytearray):
        assert len(data) > 0
        return file.write(pack(b'B' * len(data), data))
    else:
        raise


def write_byte(file: BinaryIO, data):
    assert len(data) == 1
    return write_bytes(file, data)


def read_real_uint64(file: BinaryIO) -> Tuple[int, bytes]:
    """read 8 bytes, return unpacked value as a little endian unsigned long long, and raw data."""
    res = file.read(8)
    a = unpack('<Q', res)[0]
    return a, res


def read_uint32(file: BinaryIO) -> Tuple[int, bytes]:
    """read 4 bytes, return unpacked value as a little endian unsigned long, and raw data."""
    res = file.read(4)
    a = unpack('<L', res)[0]
    return a, res


def write_uint32(file: BinaryIO, value):
    """write uint32 value in 4 bytes."""
    b = pack('<L', value)
    file.write(b)


def read_uint64(file: BinaryIO) -> int:
    """read UINT64, definition show in write_uint64()"""
    b = ord(file.read(1))
    if b == 255:
        return read_real_uint64(file)[0]
    blen = [(0b01111111, 0), (0b10111111, 1), (0b11011111, 2), (0b11101111, 3),
            (0b11110111, 4), (0b11111011, 5), (0b11111101, 6), (0b11111110, 7)]
    mask = 0x80
    vlen = 8
    for v, l in blen:
        if b <= v:
            vlen = l
            break
        mask >>= 1
    if vlen == 0:
        return b & (mask - 1)
    val = file.read(vlen)
    value = int.from_bytes(val, byteorder='little')
    highpart = b & (mask - 1)
    return value + (highpart << (vlen * 8))


def write_real_uint64(file: BinaryIO, value: int):
    """write 8 bytes, as an unsigned long long."""
    file.write(pack('<Q', value))


def write_uint64(file: BinaryIO, value: int):
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
    mask = 0x80
    length = (value.bit_length() + 7) // 8 or 1
    ba = bytearray(value.to_bytes(length, 'little'))
    for _ in range(length - 1):
        mask |= mask >> 1
    if ba[0] >= 2 ** (8 - length):
        file.write(pack('B', mask))
    elif length > 1:
        ba[0] |= mask
    else:
        pass
    file.write(ba)


def read_boolean(file: BinaryIO, count: int, checkall: int = False) -> List[bool]:
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


def write_boolean(file: BinaryIO, booleans: List[bool], all_defined: bool = False):
    if all_defined and reduce(and_, booleans):
        file.write(b'\x01')
        return
    elif all_defined:
        file.write(b'\x00')
    mask = 0x80
    o = 0x00
    for b in booleans:
        if mask == 0:
            file.write(pack('B', o))
            mask = 0x80
            o = 0x80 if b else 0x00
        else:
            o |= mask if b else 0x00
            mask >>= 1
    if mask != 0x00:
        file.write(pack('B', o))


def read_utf16(file: BinaryIO) -> str:
    """read a utf-16 string from file"""
    val = ''
    for _ in range(MAX_LENGTH):
        ch = file.read(2)
        if ch == unhexlify('0000'):
            break
        val += ch.decode('utf-16')
    return val


def write_utf16(file: BinaryIO, val: str):
    """write a utf-16 string to file"""
    file.write(val.encode('utf-16'))
    file.write(unhexlify(('0000')))


class ArchiveProperties:

    __slots__ = ['property_data']

    def __init__(self):
        self.property_data = []

    @classmethod
    def retrieve(cls, file):
        return cls()._read(file)

    def _read(self, file):
        pid = file.read(1)
        if pid == Property.ARCHIVE_PROPERTIES:
            while True:
                ptype = file.read(1)
                if ptype == Property.END:
                    break
                size = read_uint64(file)
                props = read_bytes(file, size)
                self.property_data.append(props)
        return self

    def write(self, file):
        if len(self.property_data) > 0:
            write_byte(file, Property.ARCHIVE_PROPERTIES)
            for data in self.property_data:
                write_uint64(file, len(data))
                write_bytes(file, data)
            write_byte(file, Property.END)


class PackInfo:
    """ information about packed streams """

    __slots__ = ['packpos', 'numstreams', 'packsizes', 'packpositions', 'crcs']

    def __init__(self) -> None:
        self.packpos = 0  # type: int
        self.numstreams = 0  # type: int
        self.packsizes = []  # type: List[int]
        self.crcs = None  # type: Optional[List[int]]

    @classmethod
    def retrieve(cls, file: BinaryIO):
        return cls()._read(file)

    def _read(self, file: BinaryIO):
        self.packpos = read_uint64(file)
        self.numstreams = read_uint64(file)
        pid = file.read(1)
        if pid == Property.SIZE:
            self.packsizes = [read_uint64(file) for _ in range(self.numstreams)]
            pid = file.read(1)
            if pid == Property.CRC:
                self.crcs = [read_uint64(file) for _ in range(self.numstreams)]
                pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))
        self.packpositions = [sum(self.packsizes[:i]) for i in range(self.numstreams)]  # type: List[int]
        return self

    def write(self, file: BinaryIO):
        assert self.packpos is not None
        numstreams = len(self.packsizes)
        assert self.crcs is None or len(self.crcs) == numstreams
        write_byte(file, Property.PACK_INFO)
        write_uint64(file, self.packpos)
        write_uint64(file, numstreams)
        write_byte(file, Property.SIZE)
        for size in self.packsizes:
            write_uint64(file, size)
        if self.crcs is not None:
            write_bytes(file, Property.CRC)
            for crc in self.crcs:
                write_uint64(file, crc)
        write_byte(file, Property.END)


class Folder:
    """ a "Folder" represents a stream of compressed data.
    coders: list of coder
    num_coders: length of coders
    coder: hash list
        keys:  method, numinstreams, numoutstreams, properties
    unpacksizes: uncompressed sizes of outstreams
    """

    __slots__ = ['unpacksizes', 'solid', 'num_coders', 'coders', 'digestdefined', 'totalin', 'totalout',
                 'bindpairs', 'packed_indices', 'queue', 'crc', 'decompressor', 'compressor', 'files']

    def __init__(self) -> None:
        self.unpacksizes = None  # type: Optional[List[int]]
        self.coders = []  # type: List[Any]
        self.bindpairs = []  # type: List[Any]
        self.packed_indices = []  # type: List[Any]
        # calculated values
        self.totalin = 0  # type: int
        self.totalout = 0  # type: int
        # internal values
        self.solid = False  # type: bool
        self.digestdefined = False  # type: bool
        self.crc = None  # type: Optional[int]
        # compress/decompress objects
        self.decompressor = None  # type: Optional[SevenZipDecompressor]
        self.compressor = None  # type: Optional[SevenZipCompressor]
        self.files = None

    @classmethod
    def retrieve(cls, file: BinaryIO):
        obj = cls()
        obj._read(file)
        return obj

    def _read(self, file: BinaryIO) -> None:
        num_coders = read_uint64(file)
        for i in range(num_coders):
            while True:
                b = read_byte(file)
                methodsize = b & 0xf
                iscomplex = b & 0x10 == 0x10
                hasattributes = b & 0x20 == 0x20
                last_alternative = b & 0x80 == 0
                c = {'method': file.read(methodsize)}  # type: Dict[str, Any]
                if iscomplex:
                    c['numinstreams'] = read_uint64(file)
                    c['numoutstreams'] = read_uint64(file)
                else:
                    c['numinstreams'] = 1
                    c['numoutstreams'] = 1
                self.totalin += c['numinstreams']
                self.totalout += c['numoutstreams']
                if hasattributes:
                    proplen = read_uint64(file)
                    c['properties'] = file.read(proplen)
                self.coders.append(c)
                if last_alternative:
                    break
        num_bindpairs = self.totalout - 1
        for i in range(num_bindpairs):
            self.bindpairs.append((read_uint64(file), read_uint64(file),))
        num_packedstreams = self.totalin - num_bindpairs
        if num_packedstreams == 1:
            for i in range(self.totalin):
                if self._find_in_bin_pair(i) < 0:  # there is no in_bin_pair
                    self.packed_indices.append(i)
        elif num_packedstreams > 1:
            for i in range(num_packedstreams):
                self.packed_indices.append(read_uint64(file))

    def write(self, file: BinaryIO):
        num_coders = len(self.coders)
        assert num_coders > 0
        write_uint64(file, num_coders)
        for i, c in enumerate(self.coders):
            method = c['method']
            method_size = len(method)
            numinstreams = c['numinstreams']
            numoutstreams = c['numoutstreams']
            iscomplex = 0x00 if numinstreams == 1 and numoutstreams == 1 else 0x10
            last_alternative = 0x80 if i < num_coders - 1 else 0x00
            hasattributes = 0x20 if c['properties'] is not None else 0x00
            write_byte(file, struct.pack('B', method_size & 0xf | iscomplex | hasattributes | last_alternative))
            write_bytes(file, method)
            if iscomplex == 0x10:
                write_uint64(file, numinstreams)
                write_uint64(file, numoutstreams)
            if c['properties'] is not None:
                write_uint64(file, len(c['properties']))
                write_bytes(file, c['properties'])
        num_bindpairs = self.totalout - 1
        assert len(self.bindpairs) == num_bindpairs
        num_packedstreams = self.totalin - num_bindpairs
        for bp in self.bindpairs:
            write_uint64(file, bp[0])
            write_uint64(file, bp[1])
        if num_packedstreams > 1:
            for pi in self.packed_indices:
                write_uint64(file, pi)

    def get_decompressor(self, size: int) -> SevenZipDecompressor:
        if self.decompressor is not None:
            return self.decompressor
        else:
            try:
                self.decompressor = SevenZipDecompressor(self.coders, size, self.crc)
            except Exception as e:
                raise e
            if self.decompressor is not None:
                return self.decompressor
            else:
                raise

    def get_compressor(self) -> SevenZipCompressor:
        if self.compressor is not None:
            return self.compressor
        else:
            try:
                # FIXME: set filters
                self.compressor = SevenZipCompressor()
                self.coders = self.compressor.coders
                return self.compressor
            except Exception as e:
                raise e

    def get_unpack_size(self) -> int:
        if self.unpacksizes is None:
            return 0
        for i in range(len(self.unpacksizes) - 1, -1, -1):
            if self._find_out_bin_pair(i):
                return self.unpacksizes[i]
        raise TypeError('not found')

    def _find_in_bin_pair(self, index: int) -> int:
        for idx, (a, b) in enumerate(self.bindpairs):
            if a == index:
                return idx
        return -1

    def _find_out_bin_pair(self, index: int) -> int:
        for idx, (a, b) in enumerate(self.bindpairs):
            if b == index:
                return idx
        return -1

    def is_encrypted(self) -> bool:
        return CompressionMethod.CRYPT_AES256_SHA256 in [x['method'] for x in self.coders]


class UnpackInfo:
    """ combines multiple folders """

    __slots__ = ['numfolders', 'folders', 'datastreamidx']

    @classmethod
    def retrieve(cls, file: BinaryIO):
        obj = cls()
        obj._read(file)
        return obj

    def __init__(self):
        self.numfolders = None
        self.folders = []
        self.datastreamidx = None

    def _read(self, file: BinaryIO):
        pid = file.read(1)
        if pid != Property.FOLDER:
            raise Bad7zFile('folder id expected but %s found' % repr(pid))
        self.numfolders = read_uint64(file)
        self.folders = []
        external = read_byte(file)
        if external == 0x00:
            self.folders = [Folder.retrieve(file) for _ in range(self.numfolders)]
        else:
            datastreamidx = read_uint64(file)
            current_pos = file.tell()
            file.seek(datastreamidx, 0)
            self.folders = [Folder.retrieve(file) for _ in range(self.numfolders)]
            file.seek(current_pos, 0)
        self._retrieve_coders_info(file)

    def _retrieve_coders_info(self, file: BinaryIO):
        pid = file.read(1)
        if pid != Property.CODERS_UNPACK_SIZE:
            raise Bad7zFile('coders unpack size id expected but %s found' % repr(pid))
        for folder in self.folders:
            folder.unpacksizes = [read_uint64(file) for _ in range(folder.totalout)]
        pid = file.read(1)
        if pid == Property.CRC:
            defined = read_boolean(file, self.numfolders, checkall=True)
            crcs = read_crcs(file, self.numfolders)
            for idx, folder in enumerate(self.folders):
                folder.digestdefined = defined[idx]
                folder.crc = crcs[idx]
            pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))

    def write(self, file: BinaryIO):
        file.write(Property.UNPACK_INFO)
        file.write(Property.FOLDER)
        write_uint64(file, self.numfolders)
        write_byte(file, b'\x00')
        for i in range(self.numfolders):
            for f in self.folders:
                f.write(file)
        # If support external entity, we may write
        # self.datastreamidx here.
        # folder data will be written in another place.
        #   write_byte(file, b'\x01')
        #   assert self.datastreamidx is not None
        #   write_uint64(file, self.datastreamidx)
        write_byte(file, Property.CODERS_UNPACK_SIZE)
        for folder in self.folders:
            for i in range(folder.totalout):
                write_uint64(file, folder.unpacksizes[i])
        write_byte(file, Property.END)


class SubstreamsInfo:
    """ defines the substreams of a folder """

    def __init__(self):
        self.digests = []  # type: List[int]
        self.digestsdefined = []  # type: List[bool]
        self.unpacksizes = None  # type: Optional[List[int]]

    @classmethod
    def retrieve(cls, file: BinaryIO, numfolders: int, folders: List[Folder]):
        obj = cls()
        obj._read(file, numfolders, folders)
        return obj

    def _read(self, file: BinaryIO, numfolders: int, folders: List[Folder]):
        pid = file.read(1)
        if pid == Property.NUM_UNPACK_STREAM:
            self.num_unpackstreams_folders = [read_uint64(file) for _ in range(numfolders)]
            pid = file.read(1)
        else:
            self.num_unpackstreams_folders = [1] * numfolders
        if pid == Property.SIZE:
            self.unpacksizes = []
            for i in range(len(self.num_unpackstreams_folders)):
                totalsize = 0  # type: int
                for j in range(1, self.num_unpackstreams_folders[i]):
                    size = read_uint64(file)
                    self.unpacksizes.append(size)
                    totalsize += size
                self.unpacksizes.append(folders[i].get_unpack_size() - totalsize)
            pid = file.read(1)
        num_digests = 0
        num_digests_total = 0
        for i in range(numfolders):
            numsubstreams = self.num_unpackstreams_folders[i]
            if numsubstreams != 1 or not folders[i].digestdefined:
                num_digests += numsubstreams
            num_digests_total += numsubstreams
        if pid == Property.CRC:
            defined = read_boolean(file, num_digests, checkall=1)
            crcs = read_crcs(file, num_digests)
            didx = 0
            for i in range(numfolders):
                folder = folders[i]
                numsubstreams = self.num_unpackstreams_folders[i]
                if numsubstreams == 1 and folder.digestdefined and folder.crc is not None:
                    self.digestsdefined.append(True)
                    self.digests.append(folder.crc)
                else:
                    for j in range(numsubstreams):
                        self.digestsdefined.append(defined[didx])
                        self.digests.append(crcs[didx])
                        didx += 1
            pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %r found' % pid)
        if not self.digestsdefined:
            self.digestsdefined = [False] * num_digests_total
            self.digests = [0] * num_digests_total

    def write(self, file: BinaryIO, numfolders: int):
        if self.num_unpackstreams_folders is None or len(self.num_unpackstreams_folders) == 0:
            # nothing to write
            return
        if self.unpacksizes is None:
            raise ValueError
        write_byte(file, Property.SUBSTREAMS_INFO)
        if not functools.reduce(lambda x, y: x and (y == 1), self.num_unpackstreams_folders, True):
            write_byte(file, Property.NUM_UNPACK_STREAM)
            for n in self.num_unpackstreams_folders:
                write_uint64(file, n)
        write_byte(file, Property.SIZE)
        idx = 0
        for i in range(numfolders):
            for j in range(1, self.num_unpackstreams_folders[i]):
                size = self.unpacksizes[idx]
                write_uint64(file, size)
                idx += 1
            idx += 1
        if functools.reduce(lambda x, y: x or y, self.digestsdefined, False):
            write_byte(file, Property.CRC)
            write_boolean(file, self.digestsdefined, all_defined=True)
            write_crcs(file, self.digests)
        write_byte(file, Property.END)


class StreamsInfo:
    """ information about compressed streams """

    __slots__ = ['packinfo', 'unpackinfo', 'substreamsinfo']

    def __init__(self):
        self.packinfo = None  # type: PackInfo
        self.unpackinfo = None  # type: UnpackInfo
        self.substreamsinfo = None  # type: SubstreamsInfo

    @classmethod
    def retrieve(cls, file: BinaryIO):
        obj = cls()
        obj.read(file)
        return obj

    def read(self, file: BinaryIO) -> None:
        pid = file.read(1)
        if pid == Property.PACK_INFO:
            self.packinfo = PackInfo.retrieve(file)
            pid = file.read(1)
        if pid == Property.UNPACK_INFO:
            self.unpackinfo = UnpackInfo.retrieve(file)
            pid = file.read(1)
        if pid == Property.SUBSTREAMS_INFO:
            self.substreamsinfo = SubstreamsInfo.retrieve(file, self.unpackinfo.numfolders, self.unpackinfo.folders)
            pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))

    def write(self, file: BinaryIO):
        if self.packinfo is not None:
            write_byte(file, Property.PACK_INFO)
            self.packinfo.write(file)
        if self.unpackinfo is not None:
            write_byte(file, Property.UNPACK_INFO)
            self.unpackinfo.write(file)
        if self.substreamsinfo is not None:
            write_byte(file, Property.SUBSTREAMS_INFO)
            self.substreamsinfo.write(file, self.unpackinfo.numfolders)
        write_byte(file, Property.END)


class FilesInfo:
    """ holds file properties """

    def __init__(self):
        self.numfiles = None
        self.files = None
        self.emptyfiles = None
        self.antifiles = None
        self.dataindex = None

    @classmethod
    def retrieve(cls, file: BinaryIO):
        obj = cls()
        obj._read(file)
        return obj

    def _read(self, fp: BinaryIO):
        self.numfiles = read_uint64(fp)
        self.files = [{'emptystream': False} for _ in range(self.numfiles)]
        numemptystreams = 0
        while True:
            typ = read_uint64(fp)
            if typ > 255:
                raise Bad7zFile('invalid type, must be below 256, is %d' % typ)
            prop = struct.pack(b'B', typ)
            if prop == Property.END:
                break
            size = read_uint64(fp)
            if prop == Property.DUMMY:
                # Added by newer versions of 7z to adjust padding.
                fp.seek(size, os.SEEK_CUR)
                continue
            buffer = io.BytesIO(fp.read(size))
            if prop == Property.EMPTY_STREAM:
                isempty = read_boolean(buffer, self.numfiles)
                list(map(lambda x, y: x.update({'emptystream': y}), self.files, isempty))
                for x in isempty:
                    if x:
                        numemptystreams += 1
                self.emptyfiles = [False] * numemptystreams
                self.antifiles = [False] * numemptystreams
            elif prop == Property.EMPTY_FILE:
                self.emptyfiles = read_boolean(buffer, numemptystreams)
            elif prop == Property.ANTI:
                self.antifiles = read_boolean(buffer, numemptystreams)
            elif prop == Property.NAME:
                external = buffer.read(1)
                if external == b'\x00':
                    self._read_name(buffer)
                else:
                    self.dataindex = read_uint64(buffer)
                    # try to read external data
                    current_pos = fp.tell()
                    fp.seek(self.dataindex, 0)
                    self._read_name(buffer)
                    fp.seek(current_pos, 0)
            elif prop == Property.CREATION_TIME:
                self._readTimes(buffer, self.files, 'creationtime')
            elif prop == Property.LAST_ACCESS_TIME:
                self._readTimes(buffer, self.files, 'lastaccesstime')
            elif prop == Property.LAST_WRITE_TIME:
                self._readTimes(buffer, self.files, 'lastwritetime')
            elif prop == Property.ATTRIBUTES:
                defined = read_boolean(buffer, self.numfiles, checkall=1)
                external = buffer.read(1)
                if external == b'\x00':
                    self._read_attributes(buffer, defined)
                else:
                    self.dataindex = read_uint64(buffer)
                    # try to read external data
                    current_pos = fp.tell()
                    fp.seek(self.dataindex, 0)
                    self._read_attributes(fp, defined)
                    fp.seek(current_pos, 0)
            else:
                raise Bad7zFile('invalid type %r' % (prop))

    def _read_name(self, buffer: BinaryIO) -> None:
        for f in self.files:
            f['filename'] = read_utf16(buffer)

    def _read_attributes(self, buffer: BinaryIO, defined: List[bool]) -> None:
        for idx, f in enumerate(self.files):
            if defined[idx]:
                f['attributes'], _ = read_uint32(buffer)
            else:
                f['attributes'] = None

    def _readTimes(self, fp: BinaryIO, files: List[Dict[str, Any]], name: str) -> None:
        defined = read_boolean(fp, len(files), checkall=1)
        # NOTE: the "external" flag is currently ignored, should be 0x00
        self.external = fp.read(1)
        for i in range(len(files)):
            if defined[i]:
                files[i][name] = ArchiveTimestamp(read_real_uint64(fp)[0])
            else:
                files[i][name] = None

    def write(self, file: BinaryIO):
        assert self.files is not None
        numfiles = len(self.files)
        numemptystreams = 0
        emptystreams = []
        for f in self.files:
            if f['emptystream']:
                numemptystreams += 1
            emptystreams.append(f['emptystream'])
        assert numfiles == len(emptystreams)
        write_byte(file, Property.FILES_INFO)
        write_uint64(file, numfiles)
        write_byte(file, Property.EMPTY_STREAM)
        write_boolean(file, emptystreams, all_defined=False)
        if self.emptyfiles is not None:
            if functools.reduce(or_, self.emptyfiles):  # there are some emptyfile
                write_byte(file, Property.EMPTY_FILE)
                write_boolean(file, self.emptyfiles)
        if self.antifiles is not None:
            if functools.reduce(or_, self.antifiles):  # there are some antifiles
                write_byte(file, Property.ANTI)
                write_boolean(file, self.antifiles)
        write_byte(file, Property.NAME)
        no_external = b'\x00'
        write_byte(file, no_external)
        for f in self.files:
            if f.get('filename', None) is not None:
                write_utf16(file, f['filename'])


class Header:
    """ the archive header """

    __slot__ = ['solid', 'properties', 'additional_streams', 'main_streams', 'files_info',
                'size', '_start_pos']

    def __init__(self) -> None:
        self.solid = False
        self.properties = None
        self.additional_streams = None
        self.main_streams = None
        self.files_info = None
        self.size = 0  # fixme. Not implemented yet
        self._start_pos = 0

    @classmethod
    def retrieve(cls, fp: BinaryIO, buffer: BytesIO, start_pos: int):
        obj = cls()
        obj._read(fp, buffer, start_pos)
        return obj

    def _read(self, fp: BinaryIO, buffer: BytesIO, start_pos: int) -> None:
        self._start_pos = start_pos
        fp.seek(self._start_pos)
        self._decode_header(fp, buffer)

    def _decode_header(self, fp: BinaryIO, buffer: BytesIO) -> None:
        """
        Decode header data or encoded header data from buffer.
        When buffer consist of encoded buffer, it get stream data
        from it and call itself recursively
        """
        pid = buffer.read(1)
        if not pid:
            # empty archive
            return
        elif pid == Property.HEADER:
            self._extract_header_info(buffer)
            return
        elif pid != Property.ENCODED_HEADER:
            raise TypeError('Unknown field: %r' % (id))
        # get from encoded header
        streams = StreamsInfo.retrieve(buffer)
        self._decode_header(fp, self._get_headerdata_from_streams(fp, streams))

    def _get_headerdata_from_streams(self, fp: BinaryIO, streams: StreamsInfo) -> BytesIO:
        """get header data from given streams.unpackinfo and packinfo.
        folder data are stored in raw data positioned in afterheader."""
        buffer = io.BytesIO()
        src_start = self._start_pos
        for folder in streams.unpackinfo.folders:
            if folder.is_encrypted():
                raise UnsupportedCompressionMethodError()

            uncompressed = folder.unpacksizes
            if not isinstance(uncompressed, (list, tuple)):
                uncompressed = [uncompressed] * len(folder.coders)
            compressed_size = streams.packinfo.packsizes[0]
            uncompressed_size = uncompressed[-1]

            src_start += streams.packinfo.packpos
            fp.seek(src_start, 0)
            decompressor = folder.get_decompressor(compressed_size)
            folder_data = decompressor.decompress(fp.read(compressed_size))[:uncompressed_size]
            src_start += uncompressed_size
            if folder.digestdefined:
                if folder.crc != calculate_crc32(folder_data):
                    raise Bad7zFile('invalid block data')
            buffer.write(folder_data)
        buffer.seek(0, 0)
        return buffer

    def _build_encoded_header(self):
        buf = io.BytesIO()
        self.write(buf, encoded=False)
        header_data = buf.getvalue()
        streams = StreamsInfo()
        streams.packinfo = PackInfo()
        streams.packinfo.packpos = 0
        streams.packinfo.packsizes = []  # TODO: fixme
        streams.unpackinfo = UnpackInfo()
        streams.unpackinfo.folders = []  # fixme

    def write(self, file: BinaryIO, encoded: bool = True):
        if encoded:
            self._build_encoded_header()
            write_byte(file, Property.ENCODED_HEADER)
        else:
            write_byte(file, Property.HEADER)
            if self.properties is not None:
                self.properties.write(file)
            if self.additional_streams is not None:
                self.additional_streams.write(file)
            if self.main_streams is not None:
                self.main_streams.write(file)
            if self.files_info is not None:
                self.files_info.write(file)
            write_byte(file, Property.END)

    def _extract_header_info(self, fp: BinaryIO) -> None:
        pid = fp.read(1)
        if pid == Property.ARCHIVE_PROPERTIES:
            self.properties = ArchiveProperties.retrieve(fp)
            pid = fp.read(1)
        if pid == Property.ADDITIONAL_STREAMS_INFO:
            self.additional_streams = StreamsInfo.retrieve(fp)
            pid = fp.read(1)
        if pid == Property.MAIN_STREAMS_INFO:
            self.main_streams = StreamsInfo.retrieve(fp)
            pid = fp.read(1)
        if pid == Property.FILES_INFO:
            self.files_info = FilesInfo.retrieve(fp)
            pid = fp.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % (repr(pid)))


class SignatureHeader:
    """The SignatureHeader class hold information of a signature header of archive."""

    __slots__ = ['version', 'startheadercrc', 'nextheaderofs', 'nextheadersize', 'nextheadercrc']

    def __init__(self) -> None:
        self.version = (Configuration.P7ZIP_MAJOR_VERSION, Configuration.P7ZIP_MINOR_VERSION)  # type: Tuple[bytes, ...]
        self.startheadercrc = None  # type: Optional[int]
        self.nextheaderofs = None  # type: Optional[int]
        self.nextheadersize = None  # type: Optional[int]
        self.nextheadercrc = None  # type: Optional[int]

    @classmethod
    def retrieve(cls, file: BinaryIO):
        obj = cls()
        obj._read(file)
        return obj

    def _read(self, file: BinaryIO) -> None:
        file.seek(len(MAGIC_7Z), 0)
        self.version = read_bytes(file, 2)
        self.startheadercrc, _ = read_uint32(file)
        self.nextheaderofs, data = read_real_uint64(file)
        crc = calculate_crc32(data)
        self.nextheadersize, data = read_real_uint64(file)
        crc = calculate_crc32(data, crc)
        self.nextheadercrc, data = read_uint32(file)
        crc = calculate_crc32(data, crc)
        if crc != self.startheadercrc:
            raise Bad7zFile('invalid header data')

    def calccrc(self, header: Header):
        buf = io.BytesIO()
        header.write(buf)
        data = buf.getvalue()
        self.nextheadersize = len(data)
        self.nextheadercrc = calculate_crc32(data)
        assert self.nextheaderofs is not None
        buf = io.BytesIO()
        write_uint64(buf, self.nextheaderofs)
        write_uint64(buf, self.nextheadersize)
        write_uint32(buf, self.nextheadercrc)
        data = buf.getvalue()
        self.startheadercrc = calculate_crc32(data)

    def write(self, file: BinaryIO):
        assert self.startheadercrc is not None
        assert self.nextheadercrc is not None
        assert self.nextheaderofs is not None
        assert self.nextheadersize is not None
        file.seek(0, 0)
        write_bytes(file, MAGIC_7Z)
        write_byte(file, self.version[0])
        write_byte(file, self.version[1])
        write_uint32(file, self.startheadercrc)
        write_uint64(file, self.nextheaderofs)
        write_uint64(file, self.nextheadersize)
        write_uint32(file, self.nextheadercrc)
