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
#

from array import array
from binascii import unhexlify
from struct import pack, unpack

import logging
import lzma
import os
import traceback
from io import BytesIO, StringIO
from functools import reduce

from py7zr.altmethods import get_compressor
from py7zr.properties import Property, CompressionMethod, lzma_methods_map, alt_methods_map
from py7zr.timestamp import ArchiveTimestamp
from py7zr.exceptions import Bad7zFile, UnsupportedCompressionMethodError
from py7zr.helper import ARRAY_TYPE_UINT32, NEED_BYTESWAP, calculate_crc32

READ_BLOCKSIZE=16384


class Base(object):
    """ base class with support for various basic read/write functions """

    def _read_real_uint64(self, file):
        res = file.read(8)
        a, b = unpack('<LL', res)
        return b << 32 | a, res

    def _read_uint64(self, file):
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

    def _read_boolean(self, file, count, checkall=0):
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

    def checkcrc(self, crc, data):
        check = calculate_crc32(data)
        return crc == check


class ArchiveProperties(Base):

    def __init__(self, file):
        self.property_data = []
        pid = file.read(1)
        if pid == Property.ARCHIVE_PROPERTIES:
            while True:
                type = ord(file.read(1))
                if type == 0x0:
                    break
                # retrieve propertydata
                size = self._read_uint64(file)
                property = []
                for i in range(size):
                    b = ord(file.read(1))
                    property.append(b)
                self.property_data.append(property)


class PackInfo(Base):
    """ information about packed streams """

    def __init__(self, file):
        self.packpos = self._read_uint64(file)
        self.numstreams = self._read_uint64(file)
        pid = file.read(1)
        if pid == Property.SIZE:
            self.packsizes = [self._read_uint64(file) for x in range(self.numstreams)]
            pid = file.read(1)
            if pid == Property.CRC:
                self.crcs = [self._read_uint64(file) for x in range(self.numstreams)]
                pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))
        self.packpositions = [ sum(self.packsizes[:i]) for i in range(self.numstreams)]


class Folder(Base):
    """ a "Folder" represents a stream of compressed data """

    def __init__(self, file):
        self.solid = False
        self._file = file
        self.consumed = 0
        num_coders = self._read_uint64(file)
        self.coders = []
        self.digestdefined = False
        self.totalin = 0
        self.totalout = 0
        for i in range(num_coders):
            while True:
                b = ord(file.read(1))
                methodsize = b & 0xf
                issimple = b & 0x10 == 0
                noattributes = b & 0x20 == 0
                last_alternative = b & 0x80 == 0
                c = {}
                c['method'] = file.read(methodsize)
                if not issimple:
                    c['numinstreams'] = self._read_uint64(file)
                    c['numoutstreams'] = self._read_uint64(file)
                    # FIXME: only a simple compression method is supported
                    raise UnsupportedCompressionMethodError
                else:
                    c['numinstreams'] = 1
                    c['numoutstreams'] = 1
                self.totalin += c['numinstreams']
                self.totalout += c['numoutstreams']
                if not noattributes:
                    proplen = self._read_uint64(file)
                    c['properties'] = file.read(proplen)
                self.coders.append(c)
                if last_alternative:
                    break
        num_bindpairs = self.totalout - 1
        self.bindpairs = []
        for i in range(num_bindpairs):
            self.bindpairs.append((self._read_uint64(file), self._read_uint64(file),))
        num_packedstreams = self.totalin - num_bindpairs
        self.packed_indices = []
        if num_packedstreams == 1:
            for i in range(self.totalin):
                if self._find_in_bin_pair(i) < 0: #  there is no in_bin_pair
                    self.packed_indices.append(i)
        elif num_packedstreams > 1:
            for i in range(num_packedstreams):
                self.packed_indices.append(self._read_uint64(file))
        try:
            self._get_decompressor()
        except:
            raise

    def _get_decompressor(self):
        filters = []
        try:
            for coder in self.coders:
                filter = lzma_methods_map.get(coder['method'], None)
                if filter is not None:
                    properties = coder.get('properties', None)
                    if properties is not None:
                        filters.append(lzma._decode_filter_properties(filter, properties))
                    else:
                        filters.append({'id': filter})
                else:
                    raise UnsupportedCompressionMethodError
        except UnsupportedCompressionMethodError as e:
            filter = alt_methods_map.get(self.coders[0]['method'], None)
            if len(self.coders) == 1 and filter is not None:
                self.decompressor = get_compressor(filter=filter)
                self.can_partial_decompress = False
            else:
                raise e
        else:
            self.decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
            self.can_partial_decompress = True

    def read(self, data, max_length=None):
        if max_length is None:
            return self.decompressor.decompress(data)
        elif self.can_partial_decompress:
            return self.decompressor.decompress(data, max_length=max_length)

    def get_unpack_size(self):
        if not self.unpacksizes:
            return 0
        for i in range(len(self.unpacksizes) - 1, -1, -1):
            if self._find_out_bin_pair(i):
                return self.unpacksizes[i]
        raise TypeError('not found')

    def _find_in_bin_pair(self, index):
        for idx, (a, b) in enumerate(self.bindpairs):
            if a == index:
                return idx
        return -1

    def _find_out_bin_pair(self, index):
        for idx, (a, b) in enumerate(self.bindpairs):
            if b == index:
                return idx
        return -1

    def is_encrypted(self):
        return CompressionMethod.P7Z_AES256_SHA256 in [x['method'] for x in self.coders]


class Digests(Base):
    """ holds a list of checksums """

    def __init__(self, file, count):
        self.defined = self._read_boolean(file, count, checkall=1)
        self.crcs = array(ARRAY_TYPE_UINT32, file.read(4 * count))
        if NEED_BYTESWAP:
            self.crcs.byteswap()


UnpackDigests = Digests


class UnpackInfo(Base):
    """ combines multiple folders """

    def __init__(self, file):
        pid = file.read(1)
        if pid != Property.FOLDER:
            raise Bad7zFile('folder id expected but %s found' % repr(pid))
        self.numfolders = self._read_uint64(file)
        self.folders = []
        external = file.read(1)
        if external == unhexlify('00'):
            self.folders = [Folder(file) for x in range(self.numfolders)]
        elif external == unhexlify('01'):
            self.datastreamidx = self._read_uint64(file)
        else:
            raise Bad7zFile('0x00 or 0x01 expected but %s found' % repr(external))
        pid = file.read(1)
        if pid != Property.CODERS_UNPACK_SIZE:
            raise Bad7zFile('coders unpack size id expected but %s found' % repr(pid))
        for folder in self.folders:
            folder.unpacksizes = [self._read_uint64(file) for x in range(folder.totalout)]
        pid = file.read(1)
        if pid == Property.CRC:
            digests = UnpackDigests(file, self.numfolders)
            for idx, folder in enumerate(self.folders):
                folder.digestdefined = digests.defined[idx]
                folder.crc = digests.crcs[idx]
            pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))


class SubstreamsInfo(Base):
    """ defines the substreams of a folder """

    def __init__(self, file, numfolders, folders):
        self.digests = []
        self.digestsdefined = []
        pid = file.read(1)
        if pid == Property.NUM_UNPACK_STREAM:
            self.num_unpackstreams_folders = [self._read_uint64(file) for x in range(numfolders)]
            pid = file.read(1)
        else:
            self.num_unpackstreams_folders = [1] * numfolders
        if pid == Property.SIZE:
            self.unpacksizes = []
            for i in range(len(self.num_unpackstreams_folders)):
                sum = 0
                for j in range(1, self.num_unpackstreams_folders[i]):
                    size = self._read_uint64(file)
                    self.unpacksizes.append(size)
                    sum += size
                self.unpacksizes.append(folders[i].get_unpack_size() - sum)
            pid = file.read(1)
        num_digests = 0
        num_digests_total = 0
        for i in range(numfolders):
            numsubstreams = self.num_unpackstreams_folders[i]
            if numsubstreams != 1 or not folders[i].digestdefined:
                num_digests += numsubstreams
            num_digests_total += numsubstreams
        if pid == Property.CRC:
            digests = Digests(file, num_digests)
            didx = 0
            for i in range(numfolders):
                folder = folders[i]
                numsubstreams = self.num_unpackstreams_folders[i]
                if numsubstreams == 1 and folder.digestdefined:
                    self.digestsdefined.append(True)
                    self.digests.append(folder.crc)
                else:
                    for j in range(numsubstreams):
                        self.digestsdefined.append(digests.defined[didx])
                        self.digests.append(digests.crcs[didx])
                        didx += 1
            pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %r found' % pid)
        if not self.digestsdefined:
            self.digestsdefined = [False] * num_digests_total
            self.digests = [0] * num_digests_total


class StreamsInfo(Base):
    """ information about compressed streams """

    def __init__(self, file):
        pid = file.read(1)
        if pid == Property.PACK_INFO:
            self.packinfo = PackInfo(file)
            pid = file.read(1)
        if pid == Property.UNPACK_INFO:
            self.unpackinfo = UnpackInfo(file)
            pid = file.read(1)
        if pid == Property.SUBSTREAMS_INFO:
            self.substreamsinfo = SubstreamsInfo(file, self.unpackinfo.numfolders, self.unpackinfo.folders)
            pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))


class FilesInfo(Base):
    """ holds file properties """

    def _readTimes(self, file, files, name):
        defined = self._read_boolean(file, len(files), checkall=1)
        # NOTE: the "external" flag is currently ignored, should be 0x00
        self.external = file.read(1)
        for i in range(len(files)):
            if defined[i]:
                files[i][name] = ArchiveTimestamp(self._read_real_uint64(file)[0])
            else:
                files[i][name] = None

    def __init__(self, file):
        self.numfiles = self._read_uint64(file)
        self.files = [{'emptystream': False} for x in range(self.numfiles)]
        numemptystreams = 0
        while True:
            typ = self._read_uint64(file)
            if typ > 255:
                raise Bad7zFile('invalid type, must be below 256, is %d' % typ)
            typ = pack('B', typ)
            if typ == Property.END:
                break
            size = self._read_uint64(file)
            if typ == Property.DUMMY:
                # Added by newer versions of 7z to adjust padding.
                file.seek(size, os.SEEK_CUR)
                continue
            buffer = BytesIO(file.read(size))
            if typ == Property.EMPTY_STREAM:
                isempty = self._read_boolean(buffer, self.numfiles)
                list(map(lambda x, y: x.update({'emptystream': y}), self.files, isempty))
                for x in isempty:
                    if x:
                        numemptystreams += 1
                emptyfiles = [False] * numemptystreams
                antifiles = [False] * numemptystreams
            elif typ == Property.EMPTY_FILE:
                emptyfiles = self._read_boolean(buffer, numemptystreams)
            elif typ == Property.ANTI:
                antifiles = self._read_boolean(buffer, numemptystreams)
            elif typ == Property.NAME:
                external = buffer.read(1)
                if external != unhexlify('00'):
                    self.dataindex = self._read_uint64(buffer)
                    # FIXME: evaluate external
                    raise NotImplementedError

                for f in self.files:
                    name = ''
                    while True:
                        ch = buffer.read(2)
                        if ch == unhexlify('0000'):
                            f['filename'] = name
                            break
                        name += ch.decode('utf-16')
            elif typ == Property.CREATION_TIME:
                self._readTimes(buffer, self.files, 'creationtime')
            elif typ == Property.LAST_ACCESS_TIME:
                self._readTimes(buffer, self.files, 'lastaccesstime')
            elif typ == Property.LAST_WRITE_TIME:
                self._readTimes(buffer, self.files, 'lastwritetime')
            elif typ == Property.ATTRIBUTES:
                defined = self._read_boolean(buffer, self.numfiles, checkall=1)
                external = buffer.read(1)
                if external != unhexlify('00'):
                    self.dataindex = self._read_uint64(buffer)
                    # FIXME: evaluate external
                    print("Ignore external: %s" % self.external)
                    exc_buffer = StringIO()
                    traceback.print_exc(file=exc_buffer)
                    logging.error('Ignore external:\n%s', exc_buffer.getvalue())
                    raise NotImplementedError
                for idx, f in enumerate(self.files):
                    if defined[idx]:
                        f['attributes'] = unpack('<L', buffer.read(4))[0]
                    else:
                        f['attributes'] = None
            else:
                raise Bad7zFile('invalid type %r' % (typ))


class Header(Base):
    """ the archive header """

    __slot__ = ['properties', 'additional_streams', 'main_streams', 'files_info']

    def __init__(self, file):
        pid = file.read(1)
        if pid == Property.ARCHIVE_PROPERTIES:
            self.properties = ArchiveProperties(file)
            pid = file.read(1)
        if pid == Property.ADDITIONAL_STREAMS_INFO:
            self.additional_streams = StreamsInfo(file)
            pid = file.read(1)
        if pid == Property.MAIN_STREAMS_INFO:
            self.main_streams = StreamsInfo(file)
            pid = file.read(1)
        if pid == Property.FILES_INFO:
            self.files_info = FilesInfo(file)
            pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % (repr(pid)))
