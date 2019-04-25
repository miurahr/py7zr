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
import bz2
import lzma
import zlib

from binascii import unhexlify
from struct import pack, unpack

import logging
import os
import traceback
from bringbuf.bringbuf import bRingBuf
from io import BytesIO, StringIO

from py7zr.exceptions import Bad7zFile, UnsupportedCompressionMethodError
from py7zr.helpers import checkcrc, read_crc, calculate_crc32, ArchiveTimestamp, read_boolean, read_real_uint64, read_uint64
from py7zr.properties import Property, CompressionMethod, MAGIC_7Z, QUEUELEN


class ArchiveProperties:

    def __init__(self, file):
        self.property_data = []
        pid = file.read(1)
        if pid == Property.ARCHIVE_PROPERTIES:
            while True:
                type = ord(file.read(1))
                if type == 0x0:
                    break
                # retrieve property
                size = read_uint64(file)
                property = []
                for i in range(size):
                    b = ord(file.read(1))
                    property.append(b)
                self.property_data.append(property)


class PackInfo:
    """ information about packed streams """

    def __init__(self, file):
        self.packpos = read_uint64(file)
        self.numstreams = read_uint64(file)
        pid = file.read(1)
        if pid == Property.SIZE:
            self.packsizes = [read_uint64(file) for x in range(self.numstreams)]
            pid = file.read(1)
            if pid == Property.CRC:
                self.crcs = [read_uint64(file) for x in range(self.numstreams)]
                pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))
        self.packpositions = [sum(self.packsizes[:i]) for i in range(self.numstreams)]


class Folder:
    """ a "Folder" represents a stream of compressed data """

    def __init__(self, file):
        self.unpacksizes = None
        self.solid = False
        self._file = file
        self.consumed = 0
        num_coders = read_uint64(file)
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
                    c['numinstreams'] = read_uint64(file)
                    c['numoutstreams'] = read_uint64(file)
                    # FIXME: only a simple compression method is supported
                    raise UnsupportedCompressionMethodError
                else:
                    c['numinstreams'] = 1
                    c['numoutstreams'] = 1
                self.totalin += c['numinstreams']
                self.totalout += c['numoutstreams']
                if not noattributes:
                    proplen = read_uint64(file)
                    c['properties'] = file.read(proplen)
                self.coders.append(c)
                if last_alternative:
                    break
        num_bindpairs = self.totalout - 1
        self.bindpairs = []
        for i in range(num_bindpairs):
            self.bindpairs.append((read_uint64(file), read_uint64(file),))
        num_packedstreams = self.totalin - num_bindpairs
        self.packed_indices = []
        if num_packedstreams == 1:
            for i in range(self.totalin):
                if self._find_in_bin_pair(i) < 0:  # there is no in_bin_pair
                    self.packed_indices.append(i)
        elif num_packedstreams > 1:
            for i in range(num_packedstreams):
                self.packed_indices.append(read_uint64(file))
        self.queue = bRingBuf(QUEUELEN)

    def get_decompressor(self, size):
        if hasattr(self, 'decompressor'):
            return self.decompressor
        else:
            try:
                self.decompressor, self.can_partial_decompress = get_decompressor(self.coders, size)
            except Exception as e:
                raise e
            return self.decompressor

    def get_unpack_size(self):
        if not hasattr(self, 'unpacksizes'):
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

    def __init__(self, file, count):
        self.defined = read_boolean(file, count, checkall=1)
        self.crcs = read_crc(file, count)


UnpackDigests = Digests


class UnpackInfo:
    """ combines multiple folders """

    def __init__(self, file):
        pid = file.read(1)
        if pid != Property.FOLDER:
            raise Bad7zFile('folder id expected but %s found' % repr(pid))
        self.numfolders = read_uint64(file)
        self.folders = []
        external = file.read(1)
        if external == unhexlify('00'):
            self.folders = [Folder(file) for x in range(self.numfolders)]
        elif external == unhexlify('01'):
            self.datastreamidx = read_uint64(file)
        else:
            raise Bad7zFile('0x00 or 0x01 expected but %s found' % repr(external))
        pid = file.read(1)
        if pid != Property.CODERS_UNPACK_SIZE:
            raise Bad7zFile('coders unpack size id expected but %s found' % repr(pid))
        for folder in self.folders:
            folder.unpacksizes = [read_uint64(file) for x in range(folder.totalout)]
        pid = file.read(1)
        if pid == Property.CRC:
            digests = UnpackDigests(file, self.numfolders)
            for idx, folder in enumerate(self.folders):
                folder.digestdefined = digests.defined[idx]
                folder.crc = digests.crcs[idx]
            pid = file.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % repr(pid))


class SubstreamsInfo:
    """ defines the substreams of a folder """

    def __init__(self, file, numfolders, folders):
        self.digests = []
        self.digestsdefined = []
        pid = file.read(1)
        if pid == Property.NUM_UNPACK_STREAM:
            self.num_unpackstreams_folders = [read_uint64(file) for x in range(numfolders)]
            pid = file.read(1)
        else:
            self.num_unpackstreams_folders = [1] * numfolders
        if pid == Property.SIZE:
            self.unpacksizes = []
            for i in range(len(self.num_unpackstreams_folders)):
                sum = 0
                for j in range(1, self.num_unpackstreams_folders[i]):
                    size = read_uint64(file)
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


class StreamsInfo:
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


class FilesInfo:
    """ holds file properties """

    def _readTimes(self, fp, files, name):
        defined = read_boolean(fp, len(files), checkall=1)
        # NOTE: the "external" flag is currently ignored, should be 0x00
        self.external = fp.read(1)
        for i in range(len(files)):
            if defined[i]:
                files[i][name] = ArchiveTimestamp(read_real_uint64(fp)[0])
            else:
                files[i][name] = None

    def __init__(self, fp):
        self.numfiles = read_uint64(fp)
        self.files = [{'emptystream': False} for x in range(self.numfiles)]
        numemptystreams = 0
        while True:
            typ = read_uint64(fp)
            if typ > 255:
                raise Bad7zFile('invalid type, must be below 256, is %d' % typ)
            typ = pack('B', typ)
            if typ == Property.END:
                break
            size = read_uint64(fp)
            if typ == Property.DUMMY:
                # Added by newer versions of 7z to adjust padding.
                fp.seek(size, os.SEEK_CUR)
                continue
            buffer = BytesIO(fp.read(size))
            if typ == Property.EMPTY_STREAM:
                isempty = read_boolean(buffer, self.numfiles)
                list(map(lambda x, y: x.update({'emptystream': y}), self.files, isempty))
                for x in isempty:
                    if x:
                        numemptystreams += 1
                emptyfiles = [False] * numemptystreams
                antifiles = [False] * numemptystreams
            elif typ == Property.EMPTY_FILE:
                emptyfiles = read_boolean(buffer, numemptystreams)
            elif typ == Property.ANTI:
                antifiles = read_boolean(buffer, numemptystreams)
            elif typ == Property.NAME:
                external = buffer.read(1)
                if external != unhexlify('00'):
                    self.dataindex = read_uint64(buffer)
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
                defined = read_boolean(buffer, self.numfiles, checkall=1)
                external = buffer.read(1)
                if external != unhexlify('00'):
                    self.dataindex = read_uint64(buffer)
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


class Header:
    """ the archive header """

    __slot__ = ['solid', 'properties', 'additional_streams', 'main_streams', 'files_info',
                '_start_pos']

    def __init__(self, fp, buffer, start_pos):
        self._start_pos = start_pos
        fp.seek(self._start_pos)
        self._decode_header(fp, buffer)

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
        streams = StreamsInfo(buffer)
        return self._decode_header(fp, self._get_headerdata_from_streams(fp, streams))

    def _get_headerdata_from_streams(self, fp, streams):
        """get header data from given streams.unpackinfo and packinfo.
        folder data are stored in raw data positioned in afterheader."""
        buffer = BytesIO()
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
            folder_data = folder.get_decompressor(compressed_size).decompress(fp.read(compressed_size))[:uncompressed_size]
            src_start += uncompressed_size
            if folder.digestdefined:
                if not checkcrc(folder.crc, folder_data):
                    raise Bad7zFile('invalid block data')
            buffer.write(folder_data)
        buffer.seek(0, 0)
        return buffer

    def _extract_header_info(self, fp):
        pid = fp.read(1)
        if pid == Property.ARCHIVE_PROPERTIES:
            self.properties = ArchiveProperties(fp)
            pid = fp.read(1)
        if pid == Property.ADDITIONAL_STREAMS_INFO:
            self.additional_streams = StreamsInfo(fp)
            pid = fp.read(1)
        if pid == Property.MAIN_STREAMS_INFO:
            self.main_streams = StreamsInfo(fp)
            pid = fp.read(1)
        if pid == Property.FILES_INFO:
            self.files_info = FilesInfo(fp)
            pid = fp.read(1)
        if pid != Property.END:
            raise Bad7zFile('end id expected but %s found' % (repr(pid)))


class SignatureHeader:
    """The SignatureHeader class hold information of a signature header of archive."""

    def __init__(self, file):
        file.seek(len(MAGIC_7Z), 0)
        self.version = unpack('BB', file.read(2))
        self._startheadercrc = unpack('<L', file.read(4))[0]
        self.nextheaderofs, data = read_real_uint64(file)
        crc = calculate_crc32(data)
        self.nextheadersize, data = read_real_uint64(file)
        crc = calculate_crc32(data, crc)
        data = file.read(4)
        self.nextheadercrc = unpack('<L', data)[0]
        crc = calculate_crc32(data, crc)
        if crc != self._startheadercrc:
            raise Bad7zFile('invalid header data')


FILTER_BZIP2 = 1
FILTER_ZIP = 2
lzma_methods_map = {
    CompressionMethod.LZMA: lzma.FILTER_LZMA1,
    CompressionMethod.LZMA2: lzma.FILTER_LZMA2,
    CompressionMethod.DELTA: lzma.FILTER_DELTA,
    CompressionMethod.P7Z_BCJ: lzma.FILTER_X86,
    CompressionMethod.BCJ_ARM: lzma.FILTER_ARM,
    CompressionMethod.BCJ_ARMT: lzma.FILTER_ARMTHUMB,
    CompressionMethod.BCJ_IA64: lzma.FILTER_IA64,
    CompressionMethod.BCJ_PPC: lzma.FILTER_POWERPC,
    CompressionMethod.BCJ_SPARC: lzma.FILTER_SPARC,
}
alt_methods_map = {
    CompressionMethod.MISC_BZIP2: FILTER_BZIP2,
    CompressionMethod.MISC_ZIP: FILTER_ZIP,
}


class WrappedDecompressor:
    def __init__(self, decompressor, size):
        self.decompressor = decompressor
        self.input_size = size
        self.consumed = 0

    @property
    def needs_input(self):
        return self.decompressor.needs_input

    @property
    def eof(self):
        return self.decompressor.eof

    def decompress(self, data, max_length=None):
        self.consumed += len(data)
        if max_length is not None:
            return self.decompressor.decompress(data, max_length=max_length)
        else:
            return self.decompressor.decompress(data)

    @property
    def unused_data(self):
        return self.decompressor.unused_data

    @property
    def remaining_size(self):
        return self.input_size - self.consumed


def get_decompressor(coders, size):
    decompressor = None
    filters = []
    try:
        for coder in coders:
            filter = lzma_methods_map.get(coder['method'], None)
            if filter is not None:
                properties = coder.get('properties', None)
                if properties is not None:
                    filters[:0] = [lzma._decode_filter_properties(filter, properties)]
                else:
                    filters[:0] = [{'id': filter}]
            else:
                raise UnsupportedCompressionMethodError
    except UnsupportedCompressionMethodError as e:
        filter = alt_methods_map.get(coders[0]['method'], None)
        if len(coders) == 1 and filter is not None:
            if filter == FILTER_BZIP2:
                decompressor = bz2.BZ2Decompressor()
            elif filter == FILTER_ZIP:
                decompressor = zlib.decompressobj(-15)
            can_partial_decompress = False
        else:
            raise e
    else:
        decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
        can_partial_decompress = True
    return WrappedDecompressor(decompressor, size), can_partial_decompress
