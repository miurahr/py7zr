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

from py7zr.compressor import SevenZipCompressor, SevenZipDecompressor
from py7zr.exceptions import Bad7zFile
from py7zr.helpers import ArchiveTimestamp, calculate_crc32
from py7zr.properties import ENCODED_HEADER_DEFAULT, ENCRYPTED_HEADER_DEFAULT, MAGIC_7Z, Property

MAX_LENGTH = 65536
P7ZIP_MAJOR_VERSION = b'\x00'
P7ZIP_MINOR_VERSION = b'\x04'


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


def write_bytes(file: BinaryIO, data: bytes):
    return file.write(data)


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

    |  Size of encoding sequence depends from first byte:
    |  First_Byte  Extra_Bytes        Value
    |  (binary)
    |  0xxxxxxx               : ( xxxxxxx           )
    |  10xxxxxx    BYTE y[1]  : (  xxxxxx << (8 * 1)) + y
    |  110xxxxx    BYTE y[2]  : (   xxxxx << (8 * 2)) + y
    |  ...
    |  1111110x    BYTE y[6]  : (       x << (8 * 6)) + y
    |  11111110    BYTE y[7]  :                         y
    |  11111111    BYTE y[8]  :                         y
    """
    if value < 0x80:
        file.write(pack('B', value))
        return
    if value > 0x01ffffffffffffff:
        file.write(b'\xff')
        file.write(value.to_bytes(8, 'little'))
        return
    byte_length = (value.bit_length() + 7) // 8
    ba = bytearray(value.to_bytes(byte_length, 'little'))
    high_byte = int(ba[-1])
    if high_byte < 2 << (8 - byte_length - 1):
        for x in range(byte_length - 1):
            high_byte |= 0x80 >> x
        file.write(pack('B', high_byte))
        file.write(ba[:byte_length - 1])
    else:
        mask = 0x80
        for x in range(byte_length):
            mask |= 0x80 >> x
        file.write(pack('B', mask))
        file.write(ba)


def read_boolean(file: BinaryIO, count: int, checkall: bool = False) -> List[bool]:
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
    if all_defined and reduce(and_, booleans, True):
        file.write(b'\x01')
        return
    elif all_defined:
        file.write(b'\x00')
    o = bytearray(-(-len(booleans) // 8))
    for i, b in enumerate(booleans):
        if b:
            o[i // 8] |= 1 << (7 - i % 8)
    file.write(o)


def read_utf16(file: BinaryIO) -> str:
    """read a utf-16 string from file"""
    val = ''
    for _ in range(MAX_LENGTH):
        ch = file.read(2)
        if ch == unhexlify('0000'):
            break
        val += ch.decode('utf-16LE')
    return val


def write_utf16(file: BinaryIO, val: str):
    """write a utf-16 string to file"""
    for c in val:
        file.write(c.encode('utf-16LE'))
    file.write(b'\x00\x00')


def bits_to_bytes(bit_length: int) -> int:
    return - (-bit_length // 8)


class PackInfo:
    """ information about packed streams """

    __slots__ = ['packpos', 'numstreams', 'packsizes', 'packpositions', 'crcs', 'digestdefined', 'enable_digests']

    def __init__(self) -> None:
        self.packpos = 0  # type: int
        self.numstreams = 0  # type: int
        self.packsizes = []  # type: List[int]
        self.digestdefined = []  # type: List[bool]
        self.crcs = []  # type: List[int]
        self.enable_digests = True

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
                self.enable_digests = True
                self.digestdefined = read_boolean(file, self.numstreams, True)
                for crcexist in self.digestdefined:
                    if crcexist:
                        self.crcs.append(read_uint32(file)[0])
                pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))  # pragma: no-cover  # noqa
        self.packpositions = [sum(self.packsizes[:i]) for i in range(self.numstreams + 1)]  # type: List[int]
        return self

    def write(self, file: BinaryIO):
        assert self.packpos is not None
        numstreams = len(self.packsizes)
        write_byte(file, Property.PACK_INFO)
        write_uint64(file, self.packpos)
        write_uint64(file, numstreams)
        write_byte(file, Property.SIZE)
        for size in self.packsizes:
            write_uint64(file, size)
        if self.enable_digests:
            assert len(self.crcs) == numstreams
            write_byte(file, Property.CRC)
            write_boolean(file, self.digestdefined, True)
            for i in range(numstreams):
                if self.digestdefined[i]:
                    write_uint32(file, self.crcs[i])
        write_byte(file, Property.END)


class Bond:
    """Represent bindings between two methods.
    bonds[i] = (incoder, outstream)
    means
    methods[i].stream[outstream] output data go to method[incoder].stream[0]
    """

    def __init__(self, incoder, outcoder):
        self.incoder = incoder
        self.outcoder = outcoder


class Folder:
    """ a "Folder" represents a stream of compressed data.
    coders: list of coder
    num_coders: length of coders
    coder: hash list
    keys of coders:  method, numinstreams, numoutstreams, properties
    unpacksizes: uncompressed sizes of outstreams
    """

    __slots__ = ['unpacksizes', 'solid', 'coders', 'digestdefined', 'num_bindpairs', 'num_packedstreams',
                 'bindpairs', 'packed_indices', 'crc', 'compressor', 'decompressor', 'files', 'password']

    def __init__(self) -> None:
        self.unpacksizes = []  # type: List[int]
        self.coders = []  # type: List[Dict[str, Any]]
        self.bindpairs = []  # type: List[Bond]
        self.packed_indices = []  # type: List[int]
        # calculated values
        # internal values
        self.solid = False  # type: bool
        self.digestdefined = False  # type: bool
        self.crc = None  # type: Optional[int]
        # compress/decompress objects
        self.decompressor = None  # type: Optional[SevenZipDecompressor]
        self.compressor = None  # type: Optional[SevenZipCompressor]
        self.files = None
        # encryption
        self.password = None  # type: Optional[str]

    @classmethod
    def retrieve(cls, file: BinaryIO):
        obj = cls()
        obj._read(file)
        return obj

    def _read(self, file: BinaryIO) -> None:
        num_coders = read_uint64(file)
        totalin = 0
        totalout = 0
        for _ in range(num_coders):
            b = read_byte(file)
            methodsize = b & 0xf
            iscomplex = b & 0x10 == 0x10
            hasattributes = b & 0x20 == 0x20
            if methodsize > 0:
                c = {'method': file.read(methodsize)}  # type: Dict[str, Any]
            else:
                c = {'method': b'\x00'}
            if iscomplex:
                c['numinstreams'] = read_uint64(file)
                c['numoutstreams'] = read_uint64(file)
            else:
                c['numinstreams'] = 1
                c['numoutstreams'] = 1
            totalin += c['numinstreams']
            totalout += c['numoutstreams']
            if hasattributes:
                proplen = read_uint64(file)
                c['properties'] = file.read(proplen)
            self.coders.append(c)
        num_bindpairs = totalout - 1
        for i in range(num_bindpairs):
            self.bindpairs.append(Bond(read_uint64(file), read_uint64(file),))
        num_packedstreams = totalin - num_bindpairs
        if num_packedstreams == 1:
            for i in range(totalin):
                if self._find_in_bin_pair(i) < 0:  # there is no in_bin_pair
                    self.packed_indices.append(i)
        else:
            for i in range(num_packedstreams):
                self.packed_indices.append(read_uint64(file))

    def prepare_coderinfo(self, filters):
        self.compressor = SevenZipCompressor(filters=filters, password=self.password)
        self.coders = self.compressor.coders
        assert len(self.coders) > 0
        self.solid = True
        self.digestdefined = False
        num_bindpairs = sum([c['numoutstreams'] for c in self.coders]) - 1
        self.bindpairs = [Bond(incoder=i + 1, outcoder=i) for i in range(num_bindpairs)]
        # Only simple codecs are suport, assert it
        assert sum([c['numinstreams'] for c in self.coders]) == sum([c['numoutstreams'] for c in self.coders])

    def write(self, file: BinaryIO):
        num_coders = len(self.coders)
        write_uint64(file, num_coders)
        for i, c in enumerate(self.coders):
            id = c['method']  # type: bytes
            id_size = len(id) & 0x0f
            iscomplex = 0x10 if not self.is_simple(c) else 0x00
            hasattributes = 0x20 if c['properties'] is not None else 0x00
            flag = struct.pack('B', id_size | iscomplex | hasattributes)
            write_byte(file, flag)
            write_bytes(file, id[:id_size])
            if not self.is_simple(c):  # pragma: no-cover  # Only support simple coders
                write_uint64(file, c['numinstreams'])
                write_uint64(file, c['numoutstreams'])
            if c['properties'] is not None:
                write_uint64(file, len(c['properties']))
                write_bytes(file, c['properties'])
        for bond in self.bindpairs:
            write_uint64(file, bond.incoder)
            write_uint64(file, bond.outcoder)
        if sum([c['numinstreams'] for c in self.coders]) - sum([c['numoutstreams'] for c in self.coders]) > 0:  # pragma: no-cover  # noqa
            for pi in self.packed_indices:
                write_uint64(file, pi)

    def is_simple(self, coder):
        return coder['numinstreams'] == 1 and coder['numoutstreams'] == 1

    def get_decompressor(self, packsize: int, reset: bool = False) -> SevenZipDecompressor:
        if self.decompressor is not None and not reset:
            return self.decompressor
        else:
            self.decompressor = SevenZipDecompressor(self.coders, packsize, self.unpacksizes, self.crc, self.password)
            return self.decompressor

    def get_compressor(self) -> SevenZipCompressor:
        assert self.compressor
        return self.compressor

    def get_unpack_size(self) -> int:
        if self.unpacksizes is None:
            return 0
        for i in range(len(self.unpacksizes) - 1, -1, -1):
            if self._find_out_bin_pair(i) < 0:
                return self.unpacksizes[i]
        return self.unpacksizes[-1]

    def _find_in_bin_pair(self, index: int) -> int:
        for idx, bond in enumerate(self.bindpairs):
            if bond.incoder == index:
                return idx
        return -1

    def _find_out_bin_pair(self, index: int) -> int:
        for idx, bond in enumerate(self.bindpairs):
            if bond.outcoder == index:
                return idx
        return -1


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
            raise Bad7zFile('folder id expected but %s found' % repr(pid))  # pragma: no-cover
        self.numfolders = read_uint64(file)
        self.folders = []
        external = read_byte(file)
        if external == 0x00:
            self.folders = [Folder.retrieve(file) for _ in range(self.numfolders)]
        else:  # pragma: no-cover  # there is no live example
            datastreamidx = read_uint64(file)
            current_pos = file.tell()
            file.seek(datastreamidx, 0)
            self.folders = [Folder.retrieve(file) for _ in range(self.numfolders)]
            file.seek(current_pos, 0)
        self._retrieve_coders_info(file)

    def _retrieve_coders_info(self, file: BinaryIO):
        pid = file.read(1)
        if pid != Property.CODERS_UNPACK_SIZE:
            raise Bad7zFile('coders unpack size id expected but %s found' % repr(pid))  # pragma: no-cover
        for folder in self.folders:
            for c in folder.coders:
                for _ in range(c['numoutstreams']):
                    folder.unpacksizes.append(read_uint64(file))
        pid = file.read(1)
        if pid == Property.CRC:
            defined = read_boolean(file, self.numfolders, checkall=True)
            crcs = read_crcs(file, self.numfolders)
            for idx, folder in enumerate(self.folders):
                folder.digestdefined = defined[idx]
                folder.crc = crcs[idx]
            pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but 0x{:02x} found at 0x{:08x}'.format(ord(pid), file.tell()))  # pragma: no-cover  # noqa

    def write(self, file: BinaryIO):
        assert self.numfolders == len(self.folders)
        file.write(Property.UNPACK_INFO)
        file.write(Property.FOLDER)
        write_uint64(file, self.numfolders)
        write_byte(file, b'\x00')
        for folder in self.folders:
            folder.write(file)
        # If support external entity, we may write
        # self.datastreamidx here.
        # folder data will be written in another place.
        #   write_byte(file, b'\x01')
        #   assert self.datastreamidx is not None
        #   write_uint64(file, self.datastreamidx)
        write_byte(file, Property.CODERS_UNPACK_SIZE)
        for folder in self.folders:
            for s in folder.unpacksizes:
                write_uint64(file, s)
        # FIXME: write CRCs here.
        write_byte(file, Property.END)


class SubstreamsInfo:
    """ defines the substreams of a folder """

    __slots__ = ['digests', 'digestsdefined', 'unpacksizes', 'num_unpackstreams_folders']

    def __init__(self):
        self.digests = []  # type: List[int]
        self.digestsdefined = []  # type: List[bool]
        self.unpacksizes = None  # type: Optional[List[int]]
        self.num_unpackstreams_folders = []  # type: List[int]

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
            defined = read_boolean(file, num_digests, checkall=True)
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
            raise Bad7zFile('end id expected but %r found' % pid)  # pragma: no-cover
        if not self.digestsdefined:
            self.digestsdefined = [False] * num_digests_total
            self.digests = [0] * num_digests_total

    def write(self, file: BinaryIO):
        if len(self.num_unpackstreams_folders) == 0:  # pragma: no-cover  # nothing to write
            return
        write_byte(file, Property.SUBSTREAMS_INFO)
        solid = functools.reduce(lambda x, y: x or (y != 1), self.num_unpackstreams_folders, False)
        if solid:
            write_byte(file, Property.NUM_UNPACK_STREAM)
            for n in self.num_unpackstreams_folders:
                write_uint64(file, n)
        has_multi = functools.reduce(lambda x, y: x or (y > 1), self.num_unpackstreams_folders, False)
        if has_multi:
            assert self.unpacksizes
            write_byte(file, Property.SIZE)
            idx = 0
            for i, num in enumerate(self.num_unpackstreams_folders):
                for j in range(num):
                    if j + 1 != num:
                        write_uint64(file, self.unpacksizes[idx])
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
        self.substreamsinfo = None  # type: Optional[SubstreamsInfo]

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
            raise Bad7zFile('end id expected but %s found' % repr(pid))  # pragma: no-cover

    def write(self, file: BinaryIO):
        write_byte(file, Property.MAIN_STREAMS_INFO)
        if self.packinfo is not None:
            self.packinfo.write(file)
        if self.unpackinfo is not None:
            self.unpackinfo.write(file)
        if self.substreamsinfo is not None:
            self.substreamsinfo.write(file)
        write_byte(file, Property.END)


class HeaderStreamsInfo(StreamsInfo):

    def __init__(self):
        super().__init__()
        self.packinfo = PackInfo()
        self.unpackinfo = UnpackInfo()
        self.unpackinfo.numfolders = 1

    def write(self, file: BinaryIO):
        write_byte(file, Property.ENCODED_HEADER)
        self.packinfo.write(file)
        self.unpackinfo.write(file)
        write_byte(file, Property.END)


class FilesInfo:
    """ holds file properties """

    __slots__ = ['files', 'emptyfiles', 'antifiles']

    def __init__(self):
        self.files = []  # type: List[Dict[str, Any]]
        self.emptyfiles = []  # type: List[bool]
        self.antifiles = None

    @classmethod
    def retrieve(cls, file: BinaryIO):
        obj = cls()
        obj._read(file)
        return obj

    def _read(self, fp: BinaryIO):
        numfiles = read_uint64(fp)
        self.files = [{'emptystream': False} for _ in range(numfiles)]
        numemptystreams = 0
        while True:
            prop = fp.read(1)
            if prop == Property.END:
                break
            size = read_uint64(fp)
            if prop == Property.DUMMY:
                # Added by newer versions of 7z to adjust padding.
                fp.seek(size, os.SEEK_CUR)
                continue
            buffer = io.BytesIO(fp.read(size))
            if prop == Property.EMPTY_STREAM:
                isempty = read_boolean(buffer, numfiles, checkall=False)
                list(map(lambda x, y: x.update({'emptystream': y}), self.files, isempty))  # type: ignore
                numemptystreams += isempty.count(True)
            elif prop == Property.EMPTY_FILE:
                self.emptyfiles = read_boolean(buffer, numemptystreams, checkall=False)
            elif prop == Property.NAME:
                external = buffer.read(1)
                if external == b'\x00':
                    self._read_name(buffer)
                else:  # pragma: no-cover
                    dataindex = read_uint64(buffer)
                    current_pos = fp.tell()
                    fp.seek(dataindex, 0)
                    self._read_name(fp)
                    fp.seek(current_pos, 0)
            elif prop == Property.CREATION_TIME:
                self._read_times(buffer, 'creationtime')
            elif prop == Property.LAST_ACCESS_TIME:
                self._read_times(buffer, 'lastaccesstime')
            elif prop == Property.LAST_WRITE_TIME:
                self._read_times(buffer, 'lastwritetime')
            elif prop == Property.ATTRIBUTES:
                defined = read_boolean(buffer, numfiles, checkall=True)
                external = buffer.read(1)
                if external == b'\x00':
                    self._read_attributes(buffer, defined)
                else:  # pragma: no-cover
                    dataindex = read_uint64(buffer)
                    # try to read external data
                    current_pos = fp.tell()
                    fp.seek(dataindex, 0)
                    self._read_attributes(fp, defined)
                    fp.seek(current_pos, 0)
            elif prop == Property.START_POS:
                self._read_start_pos(buffer)
            else:
                raise Bad7zFile('invalid type %r' % prop)  # pragma: no-cover

    def _read_name(self, buffer: BinaryIO) -> None:
        for f in self.files:
            f['filename'] = read_utf16(buffer).replace('\\', '/')

    def _read_attributes(self, buffer: BinaryIO, defined: List[bool]) -> None:
        for idx, f in enumerate(self.files):
            f['attributes'] = read_uint32(buffer)[0] if defined[idx] else None

    def _read_times(self, fp: BinaryIO, name: str) -> None:
        defined = read_boolean(fp, len(self.files), checkall=True)
        # NOTE: the "external" flag is currently ignored, should be 0x00
        external = fp.read(1)
        assert external == b'\x00'
        for i, f in enumerate(self.files):
            f[name] = ArchiveTimestamp(read_real_uint64(fp)[0]) if defined[i] else None

    def _read_start_pos(self, fp: BinaryIO) -> None:
        defined = read_boolean(fp, len(self.files), checkall=True)
        # NOTE: the "external" flag is currently ignored, should be 0x00
        external = fp.read(1)
        assert external == 0x00
        for i, f in enumerate(self.files):
            f['startpos'] = read_real_uint64(fp)[0] if defined[i] else None

    def _write_times(self, fp: BinaryIO, propid, name: str) -> None:
        write_byte(fp, propid)
        defined = []  # type: List[bool]
        num_defined = 0  # type: int
        for f in self.files:
            if name in f.keys():
                if f[name] is not None:
                    defined.append(True)
                    num_defined += 1
        size = num_defined * 8 + 2
        if not reduce(and_, defined, True):
            size += bits_to_bytes(num_defined)
        write_uint64(fp, size)
        write_boolean(fp, defined, all_defined=True)
        write_byte(fp, b'\x00')
        for i, file in enumerate(self.files):
            if defined[i]:
                write_real_uint64(fp, ArchiveTimestamp.from_datetime(file[name]))
            else:
                pass

    def _write_prop_bool_vector(self, fp: BinaryIO, propid, vector) -> None:
        write_byte(fp, propid)
        write_boolean(fp, vector, all_defined=False)

    @staticmethod
    def _are_there(vector) -> bool:
        if vector is not None:
            if functools.reduce(or_, vector, False):
                return True
        return False

    def _write_names(self, file: BinaryIO):
        name_defined = 0
        names = []
        name_size = 0
        for f in self.files:
            if f.get('filename', None) is not None:
                name_defined += 1
                names.append(f['filename'])
                name_size += len(f['filename'].encode('utf-16LE')) + 2  # len(str + NULL_WORD)
        if name_defined > 0:
            write_byte(file, Property.NAME)
            write_uint64(file, name_size + 1)
            write_byte(file, b'\x00')
            for n in names:
                write_utf16(file, n)

    def _write_attributes(self, file):
        defined = []  # type: List[bool]
        num_defined = 0
        for f in self.files:
            if 'attributes' in f.keys() and f['attributes'] is not None:
                defined.append(True)
                num_defined += 1
            else:
                defined.append(False)
        size = num_defined * 4 + 2
        if num_defined != len(defined):
            size += bits_to_bytes(num_defined)
        write_byte(file, Property.ATTRIBUTES)
        write_uint64(file, size)
        write_boolean(file, defined, all_defined=True)
        write_byte(file, b'\x00')
        for i, f in enumerate(self.files):
            if defined[i]:
                write_uint32(file, f['attributes'])

    def write(self, file: BinaryIO):
        assert self.files is not None
        write_byte(file, Property.FILES_INFO)
        numfiles = len(self.files)
        write_uint64(file, numfiles)
        emptystreams = []  # List[bool]
        for f in self.files:
            emptystreams.append(f['emptystream'])
        if self._are_there(emptystreams):
            write_byte(file, Property.EMPTY_STREAM)
            write_uint64(file, bits_to_bytes(numfiles))
            write_boolean(file, emptystreams, all_defined=False)
        elif self._are_there(self.emptyfiles):
            self._write_prop_bool_vector(file, Property.EMPTY_FILE, self.emptyfiles)
        # padding
        pos = file.tell()
        padlen = -pos & 3  # padlen = 4 - pos % 4 if pos % 4 > 0 else 0
        if 2 >= padlen > 0:
            padlen += 4
        if padlen > 2:
            write_byte(file, Property.DUMMY)
            write_byte(file, (padlen - 2).to_bytes(1, 'little'))
            write_bytes(file, bytes(padlen - 2))
        # Name
        self._write_names(file)
        # timestamps
        self._write_times(file, Property.CREATION_TIME, 'creationtime')
        self._write_times(file, Property.LAST_ACCESS_TIME, 'lastaccesstime')
        self._write_times(file, Property.LAST_WRITE_TIME, 'lastwritetime')
        # start_pos
        # FIXME: TBD
        # attribute
        self._write_attributes(file)
        write_byte(file, Property.END)


class Header:
    """ the archive header """

    __slot__ = ['solid', 'main_streams', 'files_info', 'size', '_start_pos']

    def __init__(self) -> None:
        self.solid = False
        self.main_streams = None
        self.files_info = None
        self.size = 0
        self._start_pos = 0
        self.password = None  # type: Optional[str]

    @classmethod
    def retrieve(cls, fp: BinaryIO, buffer: BytesIO, start_pos: int, password=None):
        obj = cls()
        obj._read(fp, buffer, start_pos, password)
        return obj

    def _read(self, fp: BinaryIO, buffer: BytesIO, start_pos: int, password) -> None:
        """
        Decode header data or encoded header data from buffer.
        When buffer consist of encoded buffer, it get stream data
        from it and call itself recursively
        """
        self._start_pos = start_pos
        fp.seek(self._start_pos)
        pid = buffer.read(1)
        if not pid:
            # empty archive
            return
        if pid == Property.HEADER:
            self._extract_header_info(buffer)
            return
        if pid != Property.ENCODED_HEADER:
            raise TypeError('Unknown field: %r' % id)  # pragma: no-cover
        # get from encoded header
        streams = HeaderStreamsInfo.retrieve(buffer)
        buffer2 = io.BytesIO()
        src_start = self._start_pos
        for folder in streams.unpackinfo.folders:
            uncompressed = folder.unpacksizes
            if not isinstance(uncompressed, (list, tuple)):
                uncompressed = [uncompressed] * len(folder.coders)
            compressed_size = streams.packinfo.packsizes[0]
            uncompressed_size = uncompressed[-1]
            folder.password = password
            src_start += streams.packinfo.packpos
            fp.seek(src_start, 0)
            decompressor = folder.get_decompressor(compressed_size)
            folder_data = decompressor.decompress(fp.read(compressed_size))[:uncompressed_size]
            self.size += compressed_size
            src_start += compressed_size
            if folder.digestdefined:
                if folder.crc != calculate_crc32(folder_data):
                    raise Bad7zFile('invalid block data')
            buffer2.write(folder_data)
        buffer2.seek(0, 0)
        pid = buffer2.read(1)
        if pid != Property.HEADER:
            raise TypeError('Unknown field: %r' % id)  # pragma: no-cover
        self._extract_header_info(buffer2)

    def _encode_header(self, file: BinaryIO, afterheader: int, filters):
        startpos = file.tell()
        packpos = startpos - afterheader
        buf = io.BytesIO()
        _, raw_header_len, raw_crc = self.write(buf, 0, False)
        folder = Folder()
        folder.password = self.password
        folder.prepare_coderinfo(filters=filters)
        assert folder.compressor is not None
        headerstreams = HeaderStreamsInfo()
        headerstreams.unpackinfo.folders = [folder]
        headerstreams.packinfo.packpos = packpos
        headerstreams.packinfo.enable_digests = False
        folder.crc = raw_crc
        folder.unpacksizes = [raw_header_len]
        compressor = folder.get_compressor()
        buf.seek(0, 0)
        data = buf.read(io.DEFAULT_BUFFER_SIZE)
        while data:
            out = compressor.compress(data)
            file.write(out)
            data = buf.read(io.DEFAULT_BUFFER_SIZE)
        out = compressor.flush()
        file.write(out)
        #
        headerstreams.packinfo.packsizes = [compressor.packsize]
        headerstreams.packinfo.crcs = [compressor.digest]
        # actual header start position
        startpos = file.tell()
        headerstreams.write(file)
        return startpos

    def write(self, file: BinaryIO, afterheader: int, encoded=True, encrypted=False):
        startpos = file.tell()
        if encrypted:
            filters = ENCRYPTED_HEADER_DEFAULT
            startpos = self._encode_header(file, afterheader, filters)
        elif encoded:
            filters = ENCODED_HEADER_DEFAULT
            startpos = self._encode_header(file, afterheader, filters)
        else:
            write_byte(file, Property.HEADER)
            if self.main_streams is not None:
                self.main_streams.write(file)
            if self.files_info is not None:
                self.files_info.write(file)
            write_byte(file, Property.END)
        endpos = file.tell()
        header_len = endpos - startpos
        file.seek(startpos, io.SEEK_SET)
        crc = calculate_crc32(file.read(header_len))
        file.seek(endpos, io.SEEK_SET)
        return startpos, header_len, crc

    def _extract_header_info(self, fp: BinaryIO) -> None:
        pid = fp.read(1)
        if pid == Property.MAIN_STREAMS_INFO:
            self.main_streams = StreamsInfo.retrieve(fp)
            pid = fp.read(1)
        if pid == Property.FILES_INFO:
            self.files_info = FilesInfo.retrieve(fp)
            pid = fp.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % (repr(pid)))  # pragma: no-cover

    @staticmethod
    def build_header(folders):
        header = Header()
        header.files_info = FilesInfo()
        header.main_streams = StreamsInfo()
        header.main_streams.packinfo = PackInfo()
        header.main_streams.packinfo.numstreams = 0
        header.main_streams.packinfo.packpos = 0
        header.main_streams.unpackinfo = UnpackInfo()
        header.main_streams.unpackinfo.numfolders = len(folders)
        header.main_streams.unpackinfo.folders = folders
        header.main_streams.substreamsinfo = SubstreamsInfo()
        header.main_streams.substreamsinfo.num_unpackstreams_folders = [len(folders)]
        header.main_streams.substreamsinfo.unpacksizes = []
        return header


class SignatureHeader:
    """The SignatureHeader class hold information of a signature header of archive."""

    __slots__ = ['version', 'startheadercrc', 'nextheaderofs', 'nextheadersize', 'nextheadercrc']

    def __init__(self) -> None:
        self.version = (P7ZIP_MAJOR_VERSION, P7ZIP_MINOR_VERSION)  # type: Tuple[bytes, ...]
        self.startheadercrc = -1  # type: int
        self.nextheaderofs = -1  # type: int
        self.nextheadersize = -1  # type: int
        self.nextheadercrc = -1  # type: int

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

    def calccrc(self, length: int, header_crc: int):
        self.nextheadersize = length
        self.nextheadercrc = header_crc
        buf = io.BytesIO()
        write_real_uint64(buf, self.nextheaderofs)
        write_real_uint64(buf, self.nextheadersize)
        write_uint32(buf, self.nextheadercrc)
        startdata = buf.getvalue()
        self.startheadercrc = calculate_crc32(startdata)

    def write(self, file: BinaryIO):
        assert self.startheadercrc >= 0
        assert self.nextheadercrc >= 0
        assert self.nextheaderofs >= 0
        assert self.nextheadersize > 0
        file.seek(0, 0)
        write_bytes(file, MAGIC_7Z)
        write_byte(file, self.version[0])
        write_byte(file, self.version[1])
        write_uint32(file, self.startheadercrc)
        write_real_uint64(file, self.nextheaderofs)
        write_real_uint64(file, self.nextheadersize)
        write_uint32(file, self.nextheadercrc)

    def _write_skelton(self, file: BinaryIO):
        file.seek(0, 0)
        write_bytes(file, MAGIC_7Z)
        write_byte(file, self.version[0])
        write_byte(file, self.version[1])
        write_uint32(file, 1)
        write_real_uint64(file, 2)
        write_real_uint64(file, 3)
        write_uint32(file, 4)
