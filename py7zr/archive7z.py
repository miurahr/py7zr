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

import os
import sys
from binascii import unhexlify
from io import BytesIO
from struct import unpack

from py7zr.py7zrlib import Base, StreamsInfo, Header, ArchiveFile, calculate_crc32
from py7zr.exceptions import FormatError, UnsupportedCompressionMethodError
from py7zr.properties import Property, FileAttribute

MAGIC_7Z = unhexlify('377abcaf271c')  # '7z\xbc\xaf\x27\x1c'



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
            outfilename = os.path.join(dest, name)
            outdir = os.path.dirname(outfilename)
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            outfile = open(outfilename, 'wb')
            outfile.write(self.getmember(name).read())
            outfile.close()