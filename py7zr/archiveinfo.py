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
import binascii
import functools
import io
import os
import struct
from bringbuf.bringbuf import bRingBuf

from py7zr.compression import SevenZipDecompressor
from py7zr.exceptions import Bad7zFile, UnsupportedCompressionMethodError
from py7zr.helpers import calculate_crc32, ArchiveTimestamp
from py7zr.io import read_byte, read_bytes, read_crcs, read_real_uint64, read_uint32, read_uint64, read_boolean
from py7zr.io import write_byte, write_bytes, write_uint32, write_uint64, write_boolean, write_crcs
from py7zr.properties import Property, CompressionMethod, MAGIC_7Z, QUEUELEN


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
            file.write(Property.ARCHIVE_PROPERTIES)
            for data in self.property_data:
                write_uint64(file, len(data))
                write_bytes(file, data)
            file.write(Property.END)


class PackInfo:
    """ information about packed streams """

    __slots__ = ['packpos', 'numstreams', 'packsizes', 'packpositions', 'crcs']

    def __init__(self):
        self.packpos = None
        self.numstreams = None
        self.packsizes = []
        self.crcs = None

    @classmethod
    def retrieve(cls, file):
        return cls()._read(file)

    def _read(self, file):
        self.packpos = read_uint64(file)
        self.numstreams = read_uint64(file)
        pid = file.read(1)
        if pid == Property.SIZE:
            self.packsizes = [read_uint64(file) for x in range(self.numstreams)]  # nopa
            pid = file.read(1)
            if pid == Property.CRC:
                self.crcs = [read_uint64(file) for x in range(self.numstreams)]  # noqa
                pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))
        self.packpositions = [sum(self.packsizes[:i]) for i in range(self.numstreams)]
        return self

    def write(self, file):
        assert self.packpos is not None
        assert self.numstreams is not None
        assert len(self.packsizes) == self.numstreams
        write_uint64(file, self.packpos)
        write_uint64(file, self.numstreams)
        write_bytes(file, Property.SIZE)
        for i in range(self.numstreams):
            write_uint64(file, self.packsizes[i])
        if self.crcs is not None:
            write_bytes(file, Property.CRC)
            for i in range(self.numstreams):
                write_uint64(file, self.crcs[i])
        write_bytes(file, Property.END)


class Folder:
    """ a "Folder" represents a stream of compressed data.
    coders: list of coder
    num_coders: length of coders
    coder: hash list
        keys:  method, numinstreams, numoutstreams, properties
    unpacksizes: uncompressed sizes of outstreams
    """

    __slots__ = ['unpacksizes', 'solid', 'num_coders', 'coders', 'digestdefined', 'totalin', 'totalout',
                 'bindpairs', 'packed_indices', 'queue', 'crc', 'decompressor', 'compressor']

    def __init__(self):
        self.unpacksizes = None
        self.coders = []
        self.bindpairs = []
        self.packed_indices = []
        # calculated values
        self.totalin = 0
        self.totalout = 0
        # internal values
        self.solid = False
        self.digestdefined = False
        self.crc = None
        # compress/decompress objects
        self.decompressor = None
        self.compressor = None
        self.queue = bRingBuf(QUEUELEN)

    @classmethod
    def retrieve(cls, file):
        obj = cls()
        obj._read(file)
        return obj

    def _read(self, file):
        num_coders = read_uint64(file)
        for i in range(num_coders):
            while True:
                b = read_byte(file)
                methodsize = b & 0xf
                iscomplex = b & 0x10 == 0x10
                hasattributes = b & 0x20 == 0x20
                last_alternative = b & 0x80 == 0
                c = {'method': file.read(methodsize)}
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

    def write(self, file):
        num_coders = len(self.coders)
        write_uint64(file, num_coders)
        for i, c in enumerate(self.coders):
            method = c['method']
            method_size = len(method)
            numinstreams = c['numinstreams']
            numoutstreams = c['numoutstreams']
            iscomplex = 0x00 if numinstreams == 1 and numoutstreams == 1 else 0x10
            last_alternative = 0x80 if i < self.num_coders else 0x00
            if c['properties'] is not None:
                hasattributes = 0x20
                properties = c['properties']
            else:
                hasattributes = 0x00
                properties = None
            write_byte(file, method_size & 0xf | iscomplex | hasattributes | last_alternative)
            write_bytes(file, method)
            if iscomplex:
                write_uint64(file, numinstreams)
                write_uint64(file, numoutstreams)
            if properties is not None:
                write_uint64(file, len(properties))
                write_uint64(file, properties)
        num_bindpairs = self.totalout - 1
        assert len(self.bindpairs) == num_bindpairs
        num_packedstreams = self.totalin - num_bindpairs
        for bp in self.bindpairs:
            write_uint64(file, bp[0])
            write_uint64(file, bp[1])
        if num_packedstreams > 1:
            for pi in self.packed_indices:
                write_uint64(file, pi)

    def get_decompressor(self, size):
        if self.decompressor is not None:
            return self.decompressor
        else:
            try:
                self.decompressor = SevenZipDecompressor(self.coders, size)
            except Exception as e:
                raise e
            return self.decompressor

    def get_unpack_size(self):
        if self.unpacksizes is None:
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
        return CompressionMethod.CRYPT_AES256_SHA256 in [x['method'] for x in self.coders]


class Digests:
    """ holds a list of checksums """

    @classmethod
    def retrieve(cls, file, count):
        obj = cls()
        obj._read(file, count)
        return obj

    def _read(self, file, count):
        self.defined = read_boolean(file, count, checkall=1)
        self.crcs = read_crcs(file, count)

    def write(self, file):
        write_boolean(file, self.defined, all_defined=True)
        write_crcs(file, self.crcs)


UnpackDigests = Digests


class UnpackInfo:
    """ combines multiple folders """

    __slots__ = ['numfolders', 'folders', 'datastreamidx']

    @classmethod
    def retrieve(cls, file):
        obj = cls()
        obj._read(file)
        return obj

    def __init__(self):
        self.numfolders = None
        self.folders = []
        self.datastreamidx = None

    def _read(self, file):
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

    def _retrieve_coders_info(self, file):
        pid = file.read(1)
        if pid != Property.CODERS_UNPACK_SIZE:
            raise Bad7zFile('coders unpack size id expected but %s found' % repr(pid))
        for folder in self.folders:
            folder.unpacksizes = [read_uint64(file) for _ in range(folder.totalout)]
        pid = file.read(1)
        if pid == Property.CRC:
            digests = UnpackDigests.retrieve(file, self.numfolders)
            for idx, folder in enumerate(self.folders):
                folder.digestdefined = digests.defined[idx]
                folder.crc = digests.crcs[idx]
            pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))

    def write(self, file):
        file.write(Property.FOLDER)
        write_uint64(file, self.numfolders)
        external = False
        if external:
            write_byte(file, 0x00)
            for i in range(self.numfolders):
                for f in self.folders:
                    f.write(file)
        else:
            write_byte(file, 0x01)
            assert self.datastreamidx is not None
            write_uint64(file, self.datastreamidx)
        write_byte(file, Property.CODERS_UNPACK_SIZE)
        for folder in self.folders:
            for i in range(folder.totalout):
                write_uint64(file, folder.unpacksizes[i])
        write_byte(file, Property.END)


class SubstreamsInfo:
    """ defines the substreams of a folder """

    @classmethod
    def retrieve(cls, file, numfolders, folders):
        obj = cls()
        obj._read(file, numfolders, folders)
        return obj

    def _read(self, file, numfolders, folders):
        self.digests = []
        self.digestsdefined = []
        pid = file.read(1)
        if pid == Property.NUM_UNPACK_STREAM:
            self.num_unpackstreams_folders = [read_uint64(file) for _ in range(numfolders)]
            pid = file.read(1)
        else:
            self.num_unpackstreams_folders = [1] * numfolders
        if pid == Property.SIZE:
            self.unpacksizes = []
            for i in range(len(self.num_unpackstreams_folders)):
                totalsize = 0
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
            digests = Digests.retrieve(file, num_digests)
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

    def set_digests(self, folders):
        digests = Digests()
        fidx = 0
        for crc in self.digests:
            numsubstreams = self.num_unpackstreams_folders[fidx]
            if numsubstreams != 1 or not folders[fidx].digestdefined:
                # only when folders don't define digests
                digests.crcs.append(crc)
            else:
                pass

    def write(self, file):
        if self.num_unpackstreams_folders is None or len(self.num_unpackstreams_folders) == 0:
            # nothing to write
            return
        #   BYTE NID::kSubStreamsInfo; (0x08)
        write_byte(file, Property.SUBSTREAMS_INFO)
        #   []
        #   BYTE NID::kNumUnPackStream; (0x0D)
        #   UINT64 NumUnPackStreamsInFolders[NumFolders];
        #   []
        if not functools.reduce(lambda x, y: x & y == 1, self.num_unpackstreams_folders, True):
            write_byte(file, Property.NUM_UNPACK_STREAM)
            for n in self.num_unpackstreams_folders:
                write_uint64(file, n)
        #   []
        #   BYTE NID::kSize  (0x09)
        #   UINT64 UnPackSizes[]
        #   []
        write_byte(file, Property.SIZE)
        for size in self.unpacksizes:
            write_uint64(file, size)
        #   []
        #   BYTE NID::kCRC  (0x0A)
        #   Digests[Number of streams with unknown CRC]
        #   []
        write_byte(file, Property.CRC)
        # TODO: impelemnt me.

        #   BYTE NID::kEnd
        write_byte(file, Property.END)


class StreamsInfo:
    """ information about compressed streams """

    __slots__ = ['packinfo', 'unpackinfo', 'substreamsinfo']

    def __init__(self):
        self.packinfo = None
        self.unpackinfo = None
        self.substreamsinfo = None

    @classmethod
    def retrieve(cls, file):
        obj = cls()
        obj.read(file)
        return obj

    def read(self, file):
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

    def write(self, file):
        if self.packinfo is not None:
            write_byte(file, Property.PACK_INFO)
            self.packinfo.write(file)
        if self.unpackinfo is not None:
            write_byte(file, Property.UNPACK_INFO)
            self.unpackinfo.write(file)
        if self.substreamsinfo is not None:
            write_byte(file, Property.SUBSTREAMS_INFO)
            self.substreamsinfo.write(file)
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
    def retrieve(cls, file):
        obj = cls()
        obj._read(file)
        return obj

    def _read(self, fp):
        self.numfiles = read_uint64(fp)
        self.files = [{'emptystream': False} for _ in range(self.numfiles)]
        numemptystreams = 0
        while True:
            typ = read_uint64(fp)
            if typ > 255:
                raise Bad7zFile('invalid type, must be below 256, is %d' % typ)
            typ = struct.pack('B', typ)
            if typ == Property.END:
                break
            size = read_uint64(fp)
            if typ == Property.DUMMY:
                # Added by newer versions of 7z to adjust padding.
                fp.seek(size, os.SEEK_CUR)
                continue
            buffer = io.BytesIO(fp.read(size))
            if typ == Property.EMPTY_STREAM:
                isempty = read_boolean(buffer, self.numfiles)
                list(map(lambda x, y: x.update({'emptystream': y}), self.files, isempty))
                for x in isempty:
                    if x:
                        numemptystreams += 1
                self.emptyfiles = [False] * numemptystreams
                self.antifiles = [False] * numemptystreams
            elif typ == Property.EMPTY_FILE:
                self.emptyfiles = read_boolean(buffer, numemptystreams)
            elif typ == Property.ANTI:
                self.antifiles = read_boolean(buffer, numemptystreams)
            elif typ == Property.NAME:
                external = buffer.read(1)
                if external != b'\x00':
                    self.dataindex = read_uint64(buffer)
                    current_pos = fp.tell()
                    fp.seek(self.dataindex, 0)
                    self._read_name(buffer)
                    fp.seek(current_pos, 0)
                else:
                    self._read_name(buffer)
            elif typ == Property.CREATION_TIME:
                self._readTimes(buffer, self.files, 'creationtime')
            elif typ == Property.LAST_ACCESS_TIME:
                self._readTimes(buffer, self.files, 'lastaccesstime')
            elif typ == Property.LAST_WRITE_TIME:
                self._readTimes(buffer, self.files, 'lastwritetime')
            elif typ == Property.ATTRIBUTES:
                defined = read_boolean(buffer, self.numfiles, checkall=1)
                external = buffer.read(1)
                if external != b'\x00':
                    self.dataindex = read_uint64(buffer)
                    current_pos = fp.tell()
                    fp.seek(self.dataindex, 0)
                    self._read_attributes(fp, defined)
                    fp.seek(current_pos, 0)
                else:
                    self._read_attributes(buffer, defined)
            else:
                raise Bad7zFile('invalid type %r' % (typ))

    def _read_name(self, buffer):
        for f in self.files:
            name = ''
            while True:
                ch = buffer.read(2)
                if ch == binascii.unhexlify('0000'):
                    f['filename'] = name
                    break
                name += ch.decode('utf-16')

    def _read_attributes(self, buffer, defined):
        for idx, f in enumerate(self.files):
            if defined[idx]:
                f['attributes'], _ = read_uint32(buffer)
            else:
                f['attributes'] = None

    def _readTimes(self, fp, files, name):
        defined = read_boolean(fp, len(files), checkall=1)
        # NOTE: the "external" flag is currently ignored, should be 0x00
        self.external = fp.read(1)
        for i in range(len(files)):
            if defined[i]:
                files[i][name] = ArchiveTimestamp(read_real_uint64(fp)[0])
            else:
                files[i][name] = None


class Header:
    """ the archive header """

    __slot__ = ['solid', 'properties', 'additional_streams', 'main_streams', 'files_info',
                '_start_pos']

    @classmethod
    def retrieve(cls, fp, buffer, start_pos):
        obj = cls()
        obj._read(fp, buffer, start_pos)
        return obj

    def _read(self, fp, buffer, start_pos):
        self._start_pos = start_pos
        fp.seek(self._start_pos)
        self._decode_header(fp, buffer)

    def write(self, file, encoded=True):
        if encoded:
            buf = io.BytesIO()
            self._encode_header(buf)
            write_byte(file, Property.ENCODED_HEADER)
            file.write(buf.getvalue())
        else:
            write_byte(file, Property.HEADER)
            # TODO: implement me.

    def _encode_header(self, buffer):
        encoded_header = StreamsInfo()
        encoded_header.packinfo = PackInfo()
        encoded_header.packinfo.packpos = 0 # fixme
        encoded_header.packinfo.packsizes = []  # fixme
        encoded_header.write(buffer)

    def _decode_header(self, fp, buffer):
        """
        Decode header data or encoded header data from buffer.
        When buffer consist of encoded buffer, it get stream data
        from it and call itself recursively
        """
        pid = buffer.read(1)
        if not pid:
            # empty archive
            return None
        elif pid == Property.HEADER:
            return self._extract_header_info(buffer)
        elif pid != Property.ENCODED_HEADER:
            raise TypeError('Unknown field: %r' % (id))
        # get from encoded header
        streams = StreamsInfo.retrieve(buffer)
        return self._decode_header(fp, self._get_headerdata_from_streams(fp, streams))

    def _get_headerdata_from_streams(self, fp, streams):
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

    def _extract_header_info(self, fp):
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

    # proxy functions
    def get_files(self):
        return self.files_info.files

    def get_decompress_info(self):
        decompress_info = []
        packsizes = self.main_streams.packinfo.packsizes
        for i in range(self.main_streams.unpackinfo.numfolders):
            coders = self.main_streams.unpackinfo.folders[i].coders
            unpacksize = self.main_streams.unpackinfo.folders[i].get_unpack_size()
            packsize = 0
            for j in range(self.main_streams.unpackinfo.folders[i].totalin):
                packsize += packsizes[j]
            decompress_info.append((coders, unpacksize, packsize))
        return decompress_info

    def get_packpositions(self):
        return self.main_streams.packinfo.packpositions


class SignatureHeader:
    """The SignatureHeader class hold information of a signature header of archive."""

    __slots__ = ['version', 'startheadercrc', 'nextheaderofs', 'nextheadersize', 'nextheadercrc']

    def __init__(self):
        self.version = (0, 4)
        self.startheadercrc = None
        self.nextheaderofs = None
        self.nextheadersize = None
        self.nextheadercrc = None

    @classmethod
    def retrieve(cls, file):
        obj = cls()
        obj._read(file)
        return obj

    def _read(self, file):
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

    def calccrc(self, header):
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

    def write(self, file):
        assert self.startheadercrc is not None
        assert self.nextheadercrc is not None
        file.seek(0, 0)
        write_bytes(file, MAGIC_7Z)
        write_bytes(file, self.version)
        write_uint32(file, self.startheadercrc)
        write_uint64(file, self.nextheaderofs)
        write_uint64(file, self.nextheadersize)
        write_uint32(file, self.nextheadercrc)
