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

import io
import lzma
import os
import sys
import threading
from binascii import unhexlify
from io import BytesIO
from struct import unpack


from py7zr.py7zrlib import Base, StreamsInfo, Header
from py7zr.exceptions import Bad7zFile, UnsupportedCompressionMethodError, DecompressionError
from py7zr.properties import Property, CompressionMethod, FileAttribute
from py7zr.helper import calculate_crc32

MAGIC_7Z = unhexlify('377abcaf271c')  # '7z\xbc\xaf\x27\x1c'
READ_BLOCKSIZE = 16384


# ------------------
# Exported Classes
# ------------------
class ArchiveFile(Base):
    """Informational class which holds the details about an
       archive member.
       ArchiveFile objects are returned by SevenZipFile.getmember(),
       SevenZipFile.getmembers() and are usually created internally.
    """

    __slots__ = ["folder", "filename", "size", "compressed", "uncompressed",
                 "creationtime", "lastaccesstime", "lastwritetime", "attributes",
                 "digest", "pos", "emptystream",
                 "_file", "_start", "_src_start", "_maxsize",
                 "_uncompressed", "_decoders"]

    def __init__(self, info, start, src_start, folder, file, maxsize=None):
        self.digest = None
        self._file = file
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
            CompressionMethod.COPY: '_read_copy',
            CompressionMethod.LZMA: '_read_lzma',
            CompressionMethod.LZMA2: '_read_lzma2',
        }

    def _read_copy(self, coder, input, level, num_coders):
        size = self._uncompressed[level]
        if not input:
            self._file.seek(self._src_start)
            input = self._file.read(size)
        return input[self._start:self._start + size]

    def _get_decompressor(self, coder, filter):
        properties = coder.get('properties', None)
        if properties:
            decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[
                lzma._decode_filter_properties(filter, properties)
            ])
        else:
            decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{'id': filter}])
        return decompressor

    def _read_decompress(self, coder, input, level, num_coders, filter):
        size = self._uncompressed[level]
        is_last_coder = (level + 1) == num_coders
        can_partial_decompress = True
        with_cache = True
        total = self.compressed
        if is_last_coder and not self.folder.solid:
            maxlength = self._start + size
        else:
            maxlength = -1
        try:
            decompressor = self._get_decompressor(coder, filter)
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
                check_remaining = is_last_coder and not self.folder.solid and can_partial_decompress
                while remaining > 0:
                    read_data = self._file.read(READ_BLOCKSIZE)
                    if check_remaining or (with_cache and len(read_data) < READ_BLOCKSIZE):
                        tmp = decompressor.decompress(read_data, max_length=remaining)
                    else:
                        tmp = decompressor.decompress(read_data, max_length=maxlength)
                    out.write(tmp)
                    remaining -= len(tmp)
                    if decompressor.eof:
                        break
                    if decompressor.needs_input:
                        pass
                data = out.getvalue()
                if with_cache and self.folder.solid:
                    # don't decompress start of solid archive for next file
                    # TODO: limit size of cached data
                    self.folder._decompress_cache = (data, self._file.tell(), decompressor)
            else:
                if not input:
                    self._file.seek(self._src_start)
                    read_data = self._file.read(total)
                else:
                    read_data = input
                if is_last_coder and can_partial_decompress:
                    data = decompressor.decompress(read_data, max_length=self._start + size)
                else:
                    data = decompressor.decompress(read_data, max_length=maxlength)
                    if can_partial_decompress and not is_last_coder:
                        return data
        except ValueError:
            if self.is_encrypted():
                raise UnsupportedCompressionMethodError()

        return data[self._start:self._start + size]

    def _read_lzma(self, coder, input, level, num_coders):
        return self._read_decompress(coder, input, level, num_coders, lzma.FILTER_LZMA1)

    def _read_lzma2(self, coder, input, level, num_coders):
        return self._read_decompress(coder, input, level, num_coders, lzma.FILTER_LZMA2)

    # --------------------------------------------------------------------------
    # The public methods which ArchiveFile provides:

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

    def checkcrc(self):
        if self.digest is None:
            return True
        self.reset()
        return super(ArchiveFile, self).checkcrc(self.digest, self.read())

class SignatureHeader(Base):
    """The SignatureHeader class hold information of a signature header of archive."""

    def __init__(self, file):
        file.seek(len(MAGIC_7Z), 0)
        self.version = unpack('BB', file.read(2))
        self._startheadercrc = unpack('<L', file.read(4))[0]
        self.nextheaderofs, data = self._read_real_uint64(file)
        crc = calculate_crc32(data)
        self.nextheadersize, data = self._read_real_uint64(file)
        crc = calculate_crc32(data, crc)
        data = file.read(4)
        self.nextheadercrc = unpack('<L', data)[0]
        crc = calculate_crc32(data, crc)
        if crc != self._startheadercrc:
            raise Bad7zFile('invalid header data')


class SevenZipFile(Base):
    """The SevenZipFile Class provides an interface to 7z archives."""

    _fileRefCnt = ...  # type: int

    def __init__(self, file, mode='r'):
        # Check if we were passed a file-like object or not
        if isinstance(file, str):
            self._filePassed = False
            self.filename = file
            modeDict = {'r' : 'rb', 'w': 'w+b', 'x': 'x+b', 'a' : 'r+b',
                        'r+b': 'w+b', 'w+b': 'wb', 'x+b': 'xb'}
            filemode = modeDict[mode]
            while True:
                try:
                    self.fp = io.open(file, filemode)
                except OSError:
                    if filemode in modeDict:
                        filemode = modeDict[filemode]
                        continue
                    raise
                break
        else:
            self._filePassed = True
            self.fp = file
            self.filename = getattr(file, 'name', None)
        self._fileRefCnt = 1
        self._lock = threading.RLock()
        try:
            if mode == "r":
                self._real_get_contents()
            elif mode in ('w', 'x'):
                raise NotImplementedError
            elif mode == 'a':
                raise NotImplementedError
            else:
                raise ValueError("Mode must be 'r', 'w', 'x', or 'a'")
        except:
            fp = self.fp
            self.fp = None
            self._fpclose(fp)
            raise

    def _fpclose(self, fp):
        assert self._fileRefCnt > 0
        self._fileRefCnt -= 1
        if not self._fileRefCnt and not self._filePassed:
            fp.close()

    def _real_get_contents(self):
        if MAGIC_7Z != self.fp.read(len(MAGIC_7Z)):
            raise Bad7zFile('not a 7z file')
        self._sig_header = SignatureHeader(self.fp)
        self._afterheader = self.fp.tell()
        self.fp.seek(self._sig_header.nextheaderofs, 1)
        buffer = BytesIO(self.fp.read(self._sig_header.nextheadersize))
        if not self.checkcrc(self._sig_header.nextheadercrc, buffer.getvalue()):
            raise Bad7zFile('invalid header data')
        self.files = []
        self.files_map = {}
        while True:
            pid = buffer.read(1)
            if not pid or pid == Property.HEADER:
                break

            if pid != Property.ENCODED_HEADER:
                raise TypeError('Unknown field: %r' % (id))

            streams = StreamsInfo(buffer)
            self.fp.seek(self._afterheader + 0)
            buffer = self._get_folder_data(streams)
        if not pid:
            # empty archive
            self.solid = False
            return
        self.header = Header(buffer)
        self._get_files_information()
        self.files_map.update([(x.filename, x) for x in self.files])

    def _get_files_information(self):
        if hasattr(self.header, 'main_streams'):
            self.solid = self.header.main_streams.packinfo.num_streams == 1
            if hasattr(self.header.main_streams.substreamsinfo, 'unpacksizes'):
                self._unpacksizes = self.header.main_streams.substreamsinfo.unpacksizes
            else:
                self._unpacksizes = [x.unpacksizes for x in self.header.main_streams.unpackinfo.folders]
        else:
            self.solid = False

        fidx = 0
        obidx = 0
        streamidx = 0
        src_pos = self._afterheader
        pos = 0
        folder_pos = src_pos
        for info in self.header.files.files:
            # Skip all directory entries.
            attributes = info.get('attributes', None)
            if attributes and attributes & FileAttribute.DIRECTORY != 0:
                continue

            if not info['emptystream']:
                folder = self.header.main_streams.unpackinfo.folders[fidx]
                if streamidx == 0:
                    folder.solid = self.header.main_streams.substreamsinfo.num_unpackstreams[fidx] > 1

                maxsize = (folder.solid and self.header.main_streams.packinfo.packsizes[fidx]) or None
                uncompressed = self._unpacksizes[obidx]
                if not isinstance(uncompressed, (list, tuple)):
                    uncompressed = [uncompressed] * len(folder.coders)
                if pos > 0:
                    # file is part of solid archive
                    assert fidx < len(self.header.main_streams.packinfo.packsizes), 'Folder outside index for solid archive'
                    info['compressed'] = self.header.main_streams.packinfo.packsizes[fidx]
                elif fidx < len(self.header.main_streams.packinfo.packsizes):
                    # file is compressed
                    info['compressed'] = self.header.main_streams.packinfo.packsizes[fidx]
                else:
                    # file is not compressed
                    info['compressed'] = uncompressed
                info['_uncompressed'] = uncompressed
            else:
                info['compressed'] = 0
                info['_uncompressed'] = [0]
                folder = None
                maxsize = 0

            archive_file = ArchiveFile(info, pos, src_pos, folder, self.fp, maxsize=maxsize)
            if folder is not None and self.header.main_streams.substreamsinfo.digestsdefined[obidx]:
                archive_file.digest = self.header.main_streams.substreamsinfo.digests[obidx]
            self.files.append(archive_file)
            if folder is not None and folder.solid:
                pos += self._unpacksizes[obidx]
            else:
                src_pos += info['compressed']
            obidx += 1
            streamidx += 1
            if folder is not None and streamidx >= self.header.main_streams.substreamsinfo.num_unpackstreams[fidx]:
                pos = 0
                folder_pos += self.header.main_streams.packinfo.packsizes[fidx]
                src_pos = folder_pos
                fidx += 1
                streamidx = 0


    def _get_folder_data(self, streams):
            data = bytes('', 'ascii')
            src_start = self._afterheader
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
                tmp = ArchiveFile(info, 0, src_start, folder, self.fp)
                uncompressed_size = uncompressed[-1]
                folderdata = tmp.read()[:uncompressed_size]
                src_start += uncompressed_size

                if folder.digestdefined:
                    if not self.checkcrc(folder.crc, folderdata):
                        raise Bad7zFile('invalid block data')

                data += folderdata

            return BytesIO(data)

    @classmethod
    def _check_7zfile(cls, fp):
        signature = fp.read(len(MAGIC_7Z))
        if signature != MAGIC_7Z:
            return False
        return True

    # --------------------------------------------------------------------------
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

    def close(self):
        """Close the file, and for mode 'w', 'x' and 'a' write the ending
        records."""
        raise NotImplementedError

    def write(self, filename, arcname=None):
        """Put the bytes from filename into the archive under the name
        arcname."""
        raise NotImplementedError

    def testzip(self):
        raise NotImplementedError


# --------------------
# exported functions
# --------------------
def is_7zfile(filename):
    """Quickly see if a file is a 7Z file by checking the magic number.
    The filename argument may be a file or file-like object too.
    """
    result = False
    try:
        if hasattr(filename, "read"):
            result = SevenZipFile._check_7zfile(fp=filename)
            filename.seek(0)
        else:
            with open(filename, "rb") as fp:
                result = SevenZipFile._check_7zfile(fp)
    except OSError:
        pass
    return result
