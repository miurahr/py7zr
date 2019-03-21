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

import lzma
import os
import sys
from binascii import unhexlify
from io import BytesIO
from struct import unpack


from py7zr.py7zrlib import Base, StreamsInfo, Header
from py7zr.exceptions import Bad7zFile, UnsupportedCompressionMethodError, DecompressionError
from py7zr.properties import Property, CompressionMethod, FileAttribute
from py7zr.helper import calculate_crc32

MAGIC_7Z = unhexlify('377abcaf271c')  # '7z\xbc\xaf\x27\x1c'
READ_BLOCKSIZE = 16384


#--------------------
# exported functions
#--------------------
def is_7zfile(filename):
    """Quickly see if a file is a 7Z file by checking the magic number.
    The filename argument may be a file or file-like object too.
    """
    result = False
    try:
        if hasattr(filename, "read"):
            result = SevenZipFile._check_7zfile(fp=filename)
        else:
            with open(filename, "rb") as fp:
                result = SevenZipFile._check_7zfile(fp)
    except OSError:
        pass
    return result


#------------------
# Exported Classes
#------------------
class ArchiveFile(Base):
    """Informational class which holds the details about an
       archive member.
       ArchiveFile objects are returned by SevenZipFile.getmember(),
       SevenZipFile.getmembers() and are usually created internally.
    """

    def __init__(self, info, start, src_start, folder, archive, maxsize=None):
        self.digest = None
        self._archive = archive
        self._file = archive._file
        self._start = start
        self._src_start = src_start
        self.folder = folder
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
            CompressionMethod.COPY: 'read_copy',
            CompressionMethod.LZMA: 'read_lzma',
            CompressionMethod.LZMA2: 'read_lzma2',
            CompressionMethod.MISC_ZIP: 'read_unsupported',
            CompressionMethod.MISC_BZIP: 'read_unsupported',
            CompressionMethod.P7Z_AES256_SHA256: 'read_unsupported',
        }

    def is_encrypted(self):
        return self.folder.is_encrypted()

    def reset(self):
        self.pos = 0

    def read(self):
        if not self.size:
            return ''
        elif not self.folder.coders:
            raise TypeError("file has no coder information")
        data = None
        num_coders = len(self.folder.coders)
        for level, coder in enumerate(self.folder.coders):
            method = coder['method']
            decoder = None
            while method and decoder is None:
                decoder = self._decoders.get(method, None)
                method = method[:-1]
            if decoder is None:
                raise UnsupportedCompressionMethodError(repr(coder['method']))
            data = getattr(self, decoder)(coder, data, level, num_coders)
        return data

    def read_copy(self, coder, input, level, num_coders):
        size = self._uncompressed[level]
        if not input:
            self._file.seek(self._src_start)
            input = self._file.read(size)
        return input[self._start:self._start + size]

    def _read_decompress(self, coder, input, level, num_coders, filter):
        size = self._uncompressed[level]
        is_last_coder = (level + 1) == num_coders
        can_partial_decompress = True
        with_cache = True
        if is_last_coder and not self.folder.solid:
            maxlength = self._start + size
        else:
            maxlength = -1
        try:
            size = self._uncompressed[level]
            properties = coder.get('properties', None)
            if properties:
                decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[
                    lzma._decode_filter_properties(filter, properties)
                ])
            else:
                decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{'id': filter}])
            total = self.compressed
            is_last_coder = (level + 1) == num_coders
            if not input and is_last_coder:
                remaining = self._start + size
                out = BytesIO()
                cache = getattr(self.folder, '_decompress_cache', None)
                if cache is not None:
                    data, pos, decompressor = cache
                    out.write(data)
                    remaining -= len(data)
                    self._file.seek(pos)
                else:
                    self._file.seek(self._src_start)
                checkremaining = is_last_coder and not self.folder.solid and can_partial_decompress
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
                if with_cache and self.folder.solid:
                    # don't decompress start of solid archive for next file
                    # TODO: limit size of cached data
                    self.folder._decompress_cache = (data, self._file.tell(), decompressor)
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
            if self.is_encrypted():
                raise UnsupportedCompressionMethodError()

        return data[self._start:self._start + size]

    def read_lzma(self, coder, input, level, num_coders):
        return self._read_decompress(coder, input, level, num_coders, lzma.FILTER_LZMA1)

    def read_lzma2(self, coder, input, level, num_coders):
        return self._read_decompress(coder, input, level, num_coders, lzma.FILTER_LZMA2)

    def read_unsupported(self, coder, input, level, num_coders):
        raise UnsupportedCompressionMethodError()

    def checkcrc(self):
        if self.digest is None:
            return True
        self.reset()
        data = self.read()
        return super(ArchiveFile, self).checkcrc(self.digest, data)


class SevenZipFile(Base):
    """The SevenZipFile Class provides an interface to 7z archives."""

    def __init__(self, file):
        self._file = file
        self.header = file.read(len(MAGIC_7Z))
        if self.header != MAGIC_7Z:
            raise Bad7zFile('not a 7z file')
        self.version = unpack('BB', file.read(2))

        self.startheadercrc = unpack('<L', file.read(4))[0]
        self.nextheaderofs, data = self._read_real_uint64(file)
        crc = calculate_crc32(data)
        self.nextheadersize, data = self._read_real_uint64(file)
        crc = calculate_crc32(data, crc)
        data = file.read(4)
        self.nextheadercrc = unpack('<L', data)[0]
        crc = calculate_crc32(data, crc)
        if crc != self.startheadercrc:
            raise Bad7zFile('invalid header data')
        self.afterheader = file.tell()

        file.seek(self.nextheaderofs, 1)
        buffer = BytesIO(file.read(self.nextheadersize))
        if not self.checkcrc(self.nextheadercrc, buffer.getvalue()):
            raise Bad7zFile('invalid header data')

        while True:
            pid = buffer.read(1)
            if not pid or pid == Property.HEADER:
                break

            if pid != Property.ENCODED_HEADER:
                raise TypeError('Unknown field: %r' % (id))

            streams = StreamsInfo(buffer)
            file.seek(self.afterheader + 0)
            data = bytes('', 'ascii')
            src_start = self.afterheader
            for folder in streams.unpackinfo.folders:
                if folder.is_encrypted():
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
                        raise Bad7zFile('invalid block data')

                data += folderdata

            buffer = BytesIO(data)

        self.files = []
        self.files_map = {}
        if not pid:
            # empty archive
            self.solid = False
            return

        self.header = Header(buffer)
        files = self.header.files
        if hasattr(self.header, 'main_streams'):
            folders = self.header.main_streams.unpackinfo.folders
            packinfo = self.header.main_streams.packinfo
            subinfo = self.header.main_streams.substreamsinfo
            packsizes = packinfo.packsizes
            self.solid = packinfo.num_streams == 1
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
                    folder.solid = subinfo.num_unpackstreams[fidx] > 1

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
            if folder is not None and streamidx >= subinfo.num_unpackstreams[fidx]:
                pos = 0
                folder_pos += packinfo.packsizes[fidx]
                src_pos = folder_pos
                fidx += 1
                streamidx = 0

        self.files_map.update([(x.filename, x) for x in self.files])

    @classmethod
    def _check_7zfile(cls, fp):
        signature = fp.read(len(MAGIC_7Z))
        fp.seek(0)
        if signature != MAGIC_7Z:
            return False
        return True

    #--------------------------------------------------------------------------
    # The public methods which SevenZipFile provides:
    # interface like TarFile

    def getmember(self, name):
        """Return a SevenZipInfo object for member `name'. If `name' can not be
           found in the archive, KeyError is raised. If a member occurs more
           than once in the archive, its last occurrence is assumed to be the
           most up-to-date version.
        """
        try:
            if isinstance(name, (int, int)):
                return self.files[name]
            else:
                return self.files_map.get(name, None)
        except IndexError:
            raise KeyError("filename %r not found" % name)

    def getmembers(self):
        """Return the members of the archive as a list of SevenZipInfo objects. The
           list has the same order as the members in the archive.
        """
        return self.files

    def getnames(self):
        """Return the members of the archive as a list of their names. It has
           the same order as the list returned by getmembers().
        """
        return list(map(lambda x: x.filename, self.files))

    def list(self, verbose=True, file=sys.stdout):
        """Print a table of contents to sys.stdout. If `verbose' is False, only
           the names of the members are printed. If it is True, an `ls -l'-like
           output is produced.
        """
        file.write('total %d files in %sarchive\n' % (len(self.files), (self.solid and 'solid ') or ''))
        if not verbose:
            file.write('\n'.join(self.getnames()) + '\n')
            return

        for f in self.files:
            extra = (f.compressed and '%10d ' % (f.compressed)) or ' '
            file.write('%10d%s%.8x %s\n' % (f.size, extra, f.digest, f.filename))

    def extractall(self, path=None):
        """Extract all members from the archive to the current working
           directory and set owner, modification time and permissions on
           directories afterwards. `path' specifies a different directory
           to extract to.
        """
        for member in self.files:
            self.extract(member, path=path)

    def extract(self, member, path=""):
        """Extract a member from the archive to the current working directory,
           using its full name. Its file information is extracted as accurately
           as possible. `member' may be a filename or a SevenZipInfo object. You can
           specify a different directory using `path'.
        """
        if isinstance(member, str):
            target = self.getmember(member)
        else:
            target = member
        if path:
            outfilename = os.path.join(path, target.filename)
        else:
            outfilename = target.filename
        outdir = os.path.dirname(outfilename)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        outfile = open(outfilename, 'wb')
        outfile.write(target.read())
        outfile.close()

