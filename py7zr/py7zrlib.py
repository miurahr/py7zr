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
"""Read 7zip format archives."""

from array import array
from binascii import unhexlify
from struct import pack, unpack
from zlib import crc32

import logging
import lzma
import os
import sys
import traceback

from io import BytesIO, StringIO
from functools import reduce

from py7zr.properties import Property, CompressionMethod, FileAttribute
from py7zr.timestamp import ArchiveTimestamp
from py7zr.exceptions import FormatError, UnsupportedCompressionMethodError, DecompressionError


NEED_BYTESWAP = sys.byteorder != 'little'

if array('L').itemsize == 4:
    ARRAY_TYPE_UINT32 = 'L'
else:
    assert array('I').itemsize == 4
    ARRAY_TYPE_UINT32 = 'I'

READ_BLOCKSIZE = 16384

MAGIC_7Z = unhexlify('377abcaf271c')  # '7z\xbc\xaf\x27\x1c'


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


class Base(object):
    """ base class with support for various basic read/write functions """
    
    def _readReal64Bit(self, file):
        res = file.read(8)
        a, b = unpack('<LL', res)
        return b << 32 | a, res
    
    def _read64Bit(self, file):
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

    def _readBoolean(self, file, count, checkall=0):
        if checkall:
            alldefined = file.read(1)
            if alldefined != unhexlify('00'):
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
        self.propertydata = []
        id = file.read(1)
        if id == Property.ARCHIVE_PROPERTIES:
            while True:
                type = ord(file.read(1))
                if type == 0x0:
                    break
                # retrieve propertydata
                size = self._read64Bit(file)
                property = []
                for i in range(size):
                    b = ord(file.read(1))
                    property.append(b)
                self.propertydata.append(property)


class PackInfo(Base):
    """ information about packed streams """
    
    def __init__(self, file):
        self.packpos = self._read64Bit(file)
        self.numstreams = self._read64Bit(file)
        id = file.read(1)
        if id == Property.SIZE:
            self.packsizes = [self._read64Bit(file) for x in range(self.numstreams)]
            id = file.read(1)
            
            if id == Property.CRC:
                self.crcs = [self._read64Bit(file) for x in range(self.numstreams)]
                id = file.read(1)
            
        if id != Property.END:
            raise FormatError('end id expected but %s found' % repr(id))


class Folder(Base):
    """ a "Folder" represents a stream of compressed data """
    
    solid = False

    def __init__(self, file):
        numcoders = self._read64Bit(file)
        self.coders = []
        self.digestdefined = False
        totalin = 0
        self.totalout = 0
        for i in range(numcoders):
            while True:
                b = ord(file.read(1))
                methodsize = b & 0xf
                issimple = b & 0x10 == 0
                noattributes = b & 0x20 == 0
                last_alternative = b & 0x80 == 0
                c = {}
                c['method'] = file.read(methodsize)
                if not issimple:
                    c['numinstreams'] = self._read64Bit(file)
                    c['numoutstreams'] = self._read64Bit(file)
                else:
                    c['numinstreams'] = 1
                    c['numoutstreams'] = 1
                totalin += c['numinstreams']
                self.totalout += c['numoutstreams']
                if not noattributes:
                    proplen = self._read64Bit(file)
                    c['properties'] = file.read(proplen)
                self.coders.append(c)
                if last_alternative:
                    break
        
        numbindpairs = self.totalout - 1
        self.bindpairs = []
        for i in range(numbindpairs):
            self.bindpairs.append((self._read64Bit(file), self._read64Bit(file), ))
        
        numpackedstreams = totalin - numbindpairs
        self.packed_indexes = []
        if numpackedstreams == 1:
            for i in range(totalin):
                if self.findInBindPair(i) < 0:
                    self.packed_indexes.append(i)
        elif numpackedstreams > 1:
            for i in range(numpackedstreams):
                self.packed_indexes.append(self._read64Bit(file))

    def getUnpackSize(self):
        if not self.unpacksizes:
            return 0
            
        for i in range(len(self.unpacksizes) - 1, -1, -1):
            if self.findOutBindPair(i):
                return self.unpacksizes[i]
        
        raise TypeError('not found')

    def findInBindPair(self, index):
        for idx, (a, b) in enumerate(self.bindpairs):
            if a == index:
                return idx
        return -1

    def findOutBindPair(self, index):
        for idx, (a, b) in enumerate(self.bindpairs):
            if b == index:
                return idx
        return -1

    def is_encrypted(self):
        return CompressionMethod.P7Z_AES256_SHA256 in [x['method'] for x in self.coders]


class Digests(Base):
    """ holds a list of checksums """
    
    def __init__(self, file, count):
        self.defined = self._readBoolean(file, count, checkall=1)
        self.crcs = array(ARRAY_TYPE_UINT32, file.read(4 * count))
        if NEED_BYTESWAP:
            self.crcs.byteswap()


UnpackDigests = Digests


class UnpackInfo(Base):
    """ combines multiple folders """

    def __init__(self, file):
        id = file.read(1)
        if id != Property.FOLDER:
            raise FormatError('folder id expected but %s found' % repr(id))
        self.numfolders = self._read64Bit(file)
        self.folders = []
        external = file.read(1)
        if external == unhexlify('00'):
            self.folders = [Folder(file) for x in range(self.numfolders)]
        elif external == unhexlify('01'):
            self.datastreamidx = self._read64Bit(file)
        else:
            raise FormatError('0x00 or 0x01 expected but %s found' % repr(external))
        
        id = file.read(1)
        if id != Property.CODERS_UNPACK_SIZE:
            raise FormatError('coders unpack size id expected but %s found' % repr(id))
        
        for folder in self.folders:
            folder.unpacksizes = [self._read64Bit(file) for x in range(folder.totalout)]
            
        id = file.read(1)
        if id == Property.CRC:
            digests = UnpackDigests(file, self.numfolders)
            for idx, folder in enumerate(self.folders):
                folder.digestdefined = digests.defined[idx]
                folder.crc = digests.crcs[idx]
                
            id = file.read(1)
        
        if id != Property.END:
            raise FormatError('end id expected but %s found' % repr(id))


class SubstreamsInfo(Base):
    """ defines the substreams of a folder """
    
    def __init__(self, file, numfolders, folders):
        self.digests = []
        self.digestsdefined = []
        id = file.read(1)
        if id == Property.NUM_UNPACK_STREAM:
            self.numunpackstreams = [self._read64Bit(file) for x in range(numfolders)]
            id = file.read(1)
        else:
            self.numunpackstreams = [1] * numfolders
        
        if id == Property.SIZE:
            self.unpacksizes = []
            for i in range(len(self.numunpackstreams)):
                sum = 0
                for j in range(1, self.numunpackstreams[i]):
                    size = self._read64Bit(file)
                    self.unpacksizes.append(size)
                    sum += size
                self.unpacksizes.append(folders[i].getUnpackSize() - sum)
                
            id = file.read(1)

        numdigests = 0
        numdigeststotal = 0
        for i in range(numfolders):
            numsubstreams = self.numunpackstreams[i]
            if numsubstreams != 1 or not folders[i].digestdefined:
                numdigests += numsubstreams
            numdigeststotal += numsubstreams
        
        if id == Property.CRC:
            digests = Digests(file, numdigests)
            didx = 0
            for i in range(numfolders):
                folder = folders[i]
                numsubstreams = self.numunpackstreams[i]
                if numsubstreams == 1 and folder.digestdefined:
                    self.digestsdefined.append(True)
                    self.digests.append(folder.crc)
                else:
                    for j in range(numsubstreams):
                        self.digestsdefined.append(digests.defined[didx])
                        self.digests.append(digests.crcs[didx])
                        didx += 1
                            
            id = file.read(1)
            
        if id != Property.END:
            raise FormatError('end id expected but %r found' % id)

        if not self.digestsdefined:
            self.digestsdefined = [False] * numdigeststotal
            self.digests = [0] * numdigeststotal


class StreamsInfo(Base):
    """ information about compressed streams """
    
    def __init__(self, file):
        id = file.read(1)
        if id == Property.PACK_INFO:
            self.packinfo = PackInfo(file)
            id = file.read(1)
        
        if id == Property.UNPACK_INFO:
            self.unpackinfo = UnpackInfo(file)
            id = file.read(1)
            
        if id == Property.SUBSTREAMS_INFO:
            self.substreamsinfo = SubstreamsInfo(file, self.unpackinfo.numfolders, self.unpackinfo.folders)
            id = file.read(1)
        
        if id != Property.END:
            raise FormatError('end id expected but %s found' % repr(id))


class FilesInfo(Base):
    """ holds file properties """
    
    def _readTimes(self, file, files, name):
        defined = self._readBoolean(file, len(files), checkall=1)
        
        # NOTE: the "external" flag is currently ignored, should be 0x00
        self.external = file.read(1)
        for i in range(len(files)):
            if defined[i]:
                files[i][name] = ArchiveTimestamp(self._readReal64Bit(file)[0])
            else:
                files[i][name] = None

    def __init__(self, file):
        self.numfiles = self._read64Bit(file)
        self.files = [{'emptystream': False} for x in range(self.numfiles)]
        numemptystreams = 0
        while True:
            typ = self._read64Bit(file)
            if typ > 255:
                raise FormatError('invalid type, must be below 256, is %d' % typ)
                
            typ = pack('B', typ)
            if typ == Property.END:
                break
                
            size = self._read64Bit(file)
            if typ == Property.DUMMY:
                # Added by newer versions of 7z to adjust padding.
                file.seek(size, os.SEEK_CUR)
                continue

            buffer = BytesIO(file.read(size))
            if typ == Property.EMPTY_STREAM:
                isempty = self._readBoolean(buffer, self.numfiles)
                list(map(lambda x, y: x.update({'emptystream': y}), self.files, isempty))
                for x in isempty:
                    if x:
                        numemptystreams += 1
                emptyfiles = [False] * numemptystreams
                antifiles = [False] * numemptystreams
            elif typ == Property.EMPTY_FILE:
                emptyfiles = self._readBoolean(buffer, numemptystreams)
            elif typ == Property.ANTI:
                antifiles = self._readBoolean(buffer, numemptystreams)
            elif typ == Property.NAME:
                external = buffer.read(1)
                if external != unhexlify('00'):
                    self.dataindex = self._read64Bit(buffer)
                    # FIXME: evaluate external
                    print("Ignore external: %s" % self.external)
                    exc_buffer = StringIO()
                    traceback.print_exc(file=exc_buffer)
                    logging.error('Ignore external:\n%s', exc_buffer.getvalue())
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
                defined = self._readBoolean(buffer, self.numfiles, checkall=1)
                external = buffer.read(1)
                if external != unhexlify('00'):
                    self.dataindex = self._read64Bit(buffer)
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
                raise FormatError('invalid type %r' % (typ))

        
class Header(Base):
    """ the archive header """
    
    def __init__(self, file):
        id = file.read(1)
        if id == Property.ARCHIVE_PROPERTIES:
            self.properties = ArchiveProperties(file)
            id = file.read(1)
        
        if id == Property.ADDITIONAL_STREAMS_INFO:
            self.additional_streams = StreamsInfo(file)
            id = file.read(1)
        
        if id == Property.MAIN_STREAMS_INFO:
            self.main_streams = StreamsInfo(file)
            id = file.read(1)
            
        if id == Property.FILES_INFO:
            self.files = FilesInfo(file)
            id = file.read(1)
            
        if id != Property.END:
            raise FormatError('end id expected but %s found' % (repr(id)))


class ArchiveFile(Base):
    """ wrapper around a file in the archive """
    
    def __init__(self, info, start, src_start, folder, archive, maxsize=None):
        self.digest = None
        self._archive = archive
        self._file = archive._file
        self._start = start
        self._src_start = src_start
        self._folder = folder
        # maxsize is only valid for solid archives
        self._maxsize = maxsize
        for k, v in info.items():
            setattr(self, k, v)
        self.size = self.uncompressed = self._uncompressed[-1]
        if not hasattr(self, 'filename'):
            # compressed file is stored without a name, generate one
            try:
                basefilename = self._file.name
            except AttributeError:
                # 7z archive file doesn't have a name
                self.filename = 'contents'
            else:
                self.filename = os.path.splitext(os.path.basename(basefilename))[0]
        self.reset()
        self._decoders = {
            CompressionMethod.COPY: '_read_copy',
            CompressionMethod.LZMA: '_read_lzma',
            CompressionMethod.LZMA2: '_read_lzma2',
            CompressionMethod.MISC_ZIP: '_read_unsupported',
            CompressionMethod.MISC_BZIP: '_read_unsupported',
            CompressionMethod.P7Z_AES256_SHA256: '_read_unsupported',
        }

    def _is_encrypted(self):
        return self._folder.isEncrypted()

    def reset(self):
        self.pos = 0
    
    def read(self):
        if not self.size:
            return ''
        elif not self._folder.coders:
            raise TypeError("file has no coder information")
        
        data = None
        num_coders = len(self._folder.coders)
        for level, coder in enumerate(self._folder.coders):
            method = coder['method']
            decoder = None
            while method and decoder is None:
                decoder = self._decoders.get(method, None)
                method = method[:-1]
            
            if decoder is None:
                raise UnsupportedCompressionMethodError(repr(coder['method']))

            data = getattr(self, decoder)(coder, data, level, num_coders)

        return data
    
    def _read_copy(self, coder, input, level, num_coders):
        size = self._uncompressed[level]
        if not input:
            self._file.seek(self._src_start)
            input = self._file.read(size)
        return input[self._start:self._start + size]

    def _read_decompress(self, coder, input, level, num_coders, filter):
        size = self._uncompressed[level]
        is_last_coder = (level + 1) == num_coders
        decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{'id': filter}])
        can_partial_decompress = True
        with_cache = True
        if is_last_coder and not self._folder.solid:
            maxlength = self._start + size
        else:
            maxlength = -1
        try:
            size = self._uncompressed[level]
            properties = coder.get('properties', None)
            if properties:
                try:
                    # FIXME: the method is privte in cpython lzma module in commit a425c3d5a264c556d31bdd88097c79246b533ea3
                    lzma.decode_filter_properties(filter_id=filter, encoded_props=properties)
                except Exception:
                    pass
            total = self.compressed
            is_last_coder = (level + 1) == num_coders
            if not input and is_last_coder:
                remaining = self._start + size
                out = BytesIO()
                cache = getattr(self._folder, '_decompress_cache', None)
                if cache is not None:
                    data, pos, decompressor = cache
                    out.write(data)
                    remaining -= len(data)
                    self._file.seek(pos)
                else:
                    self._file.seek(self._src_start)
                checkremaining = is_last_coder and not self._folder.solid and can_partial_decompress
                while remaining > 0:
                    data = self._file.read(READ_BLOCKSIZE)
                    if checkremaining or (with_cache and len(data) < READ_BLOCKSIZE):
                        tmp = decompressor.decompress(data, max_length=remaining)
                    else:
                        tmp = decompressor.decompress(data, max_length=maxlength)
                    if not tmp and not data:
                        raise DecompressionError('end of stream while decompressing')
                    out.write(tmp)
                    remaining -= len(tmp)

                data = out.getvalue()
                if with_cache and self._folder.solid:
                    # don't decompress start of solid archive for next file
                    # TODO: limit size of cached data
                    self._folder._decompress_cache = (data, self._file.tell(), decompressor)
            else:
                if not input:
                    self._file.seek(self._src_start)
                    input = self._file.read(total)
                if is_last_coder and can_partial_decompress:
                    data = decompressor.decompress(input, max_length=self._start + size)
                else:
                    data = decompressor.decompress(input, max_length=maxlength)
                    if can_partial_decompress and not is_last_coder:
                        return data
        except ValueError:
            if self._is_encrypted():
                raise UnsupportedCompressionMethodError()

        return data[self._start:self._start + size]

    def _read_lzma(self, coder, input, level, num_coders):
        return self._read_decompress(coder, input, level, num_coders, lzma.FILTER_LZMA1)

    def _read_lzma2(self, coder, input, level, num_coders):
        return self._read_decompress(coder, input, level, num_coders, lzma.FILTER_LZMA2)

    def _read_unsupported(self, coder, input, level, num_coders):
        raise UnsupportedCompressionMethodError()
        
    def checkcrc(self):
        if self.digest is None:
            return True
            
        self.reset()
        data = self.read()
        return super(ArchiveFile, self).checkcrc(self.digest, data)
        

class Archive(Base):
    """ the archive itself """
    
    def __init__(self, file):
        self._file = file
        self.header = file.read(len(MAGIC_7Z))
        if self.header != MAGIC_7Z:
            raise FormatError('not a 7z file')
        self.version = unpack('BB', file.read(2))

        self.startheadercrc = unpack('<L', file.read(4))[0]
        self.nextheaderofs, data = self._readReal64Bit(file)
        crc = calculate_crc32(data)
        self.nextheadersize, data = self._readReal64Bit(file)
        crc = calculate_crc32(data, crc)
        data = file.read(4)
        self.nextheadercrc = unpack('<L', data)[0]
        crc = calculate_crc32(data, crc)
        if crc != self.startheadercrc:
            raise FormatError('invalid header data')
        self.afterheader = file.tell()
        
        file.seek(self.nextheaderofs, 1)
        buffer = BytesIO(file.read(self.nextheadersize))
        if not self.checkcrc(self.nextheadercrc, buffer.getvalue()):
            raise FormatError('invalid header data')
        
        while True:
            id = buffer.read(1)
            if not id or id == Property.HEADER:
                break
                
            if id != Property.ENCODED_HEADER:
                raise TypeError('Unknown field: %r' % (id))
            
            streams = StreamsInfo(buffer)
            file.seek(self.afterheader + 0)
            data = bytes('', 'ascii')
            src_start = self.afterheader
            for folder in streams.unpackinfo.folders:
                if folder.isEncrypted():
                    raise UnsupportedCompressionMethodError()

                src_start += streams.packinfo.packpos
                uncompressed = folder.unpacksizes
                if not isinstance(uncompressed, (list, tuple)):
                    uncompressed = [uncompressed] * len(folder.coders)
                info = {
                    'compressed': streams.packinfo.packsizes[0],
                    '_uncompressed': uncompressed,
                }
                tmp = ArchiveFile(info, 0, src_start, folder, self)
                uncompressed_size = uncompressed[-1]
                folderdata = tmp.read()[:uncompressed_size]
                src_start += uncompressed_size

                if folder.digestdefined:
                    if not self.checkcrc(folder.crc, folderdata):
                        raise FormatError('invalid block data')

                data += folderdata

            buffer = BytesIO(data)
        
        self.files = []
        self.files_map = {}
        if not id:
            # empty archive
            self.solid = False
            self.numfiles = 0
            self.filenames = []
            return
        
        self.header = Header(buffer)
        files = self.header.files
        if hasattr(self.header, 'main_streams'):
            folders = self.header.main_streams.unpackinfo.folders
            packinfo = self.header.main_streams.packinfo
            subinfo = self.header.main_streams.substreamsinfo
            packsizes = packinfo.packsizes
            self.solid = packinfo.numstreams == 1
            if hasattr(subinfo, 'unpacksizes'):
                unpacksizes = subinfo.unpacksizes
            else:
                unpacksizes = [x.unpacksizes for x in folders]
        else:
            # TODO(fancycode): is it necessary to provide empty values for folder, packinfo, etc?
            self.solid = False
        
        fidx = 0
        obidx = 0
        streamidx = 0
        src_pos = self.afterheader
        pos = 0
        folder_pos = src_pos
        for info in files.files:
            # Skip all directory entries.
            attributes = info.get('attributes', None)
            if attributes and attributes & FileAttribute.DIRECTORY != 0:
                continue
            
            if not info['emptystream']:
                folder = folders[fidx]
                if streamidx == 0:
                    folder.solid = subinfo.numunpackstreams[fidx] > 1

                maxsize = (folder.solid and packinfo.packsizes[fidx]) or None
                uncompressed = unpacksizes[obidx]
                if not isinstance(uncompressed, (list, tuple)):
                    uncompressed = [uncompressed] * len(folder.coders)
                if pos > 0:
                    # file is part of solid archive
                    assert fidx < len(packsizes), 'Folder outside index for solid archive'
                    info['compressed'] = packsizes[fidx]
                elif fidx < len(packsizes):
                    # file is compressed
                    info['compressed'] = packsizes[fidx]
                else:
                    # file is not compressed
                    info['compressed'] = uncompressed
                info['_uncompressed'] = uncompressed
            else:
                info['compressed'] = 0
                info['_uncompressed'] = [0]
                folder = None
                maxsize = 0

            file = ArchiveFile(info, pos, src_pos, folder, self, maxsize=maxsize)
            if folder is not None and subinfo.digestsdefined[obidx]:
                file.digest = subinfo.digests[obidx]
            self.files.append(file)
            if folder is not None and folder.solid:
                pos += unpacksizes[obidx]
            else:
                src_pos += info['compressed']
            obidx += 1
            streamidx += 1
            if folder is not None and streamidx >= subinfo.numunpackstreams[fidx]:
                pos = 0
                folder_pos += packinfo.packsizes[fidx]
                src_pos = folder_pos
                fidx += 1
                streamidx = 0
        
        self.numfiles = len(self.files)
        self.filenames = list(map(lambda x: x.filename, self.files))
        self.files_map.update([(x.filename, x) for x in self.files])
        
    # interface like TarFile
        
    def getmember(self, name):
        if isinstance(name, (int, int)):
            try:
                return self.files[name]
            except IndexError:
                return None

        return self.files_map.get(name, None)
        
    def getmembers(self):
        return self.files
        
    def getnames(self):
        return self.filenames

    def list(self, verbose=True, file=sys.stdout):
        file.write('total %d files in %sarchive\n' % (self.numfiles, (self.solid and 'solid ') or ''))
        if not verbose:
            file.write('\n'.join(self.filenames) + '\n')
            return
            
        for f in self.files:
            extra = (f.compressed and '%10d ' % (f.compressed)) or ' '
            file.write('%10d%s%.8x %s\n' % (f.size, extra, f.digest, f.filename))

    def extract_all(self, dest=None):
        for name in self.filenames:
            if dest:
                outfilename = os.path.join(dest, name)
            else:
                outfilename = name
            outdir = os.path.dirname(outfilename)
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            outfile = open(outfilename, 'wb')
            outfile.write(self.getmember(name).read())
            outfile.close()
