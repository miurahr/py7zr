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

import argparse
import io
import os
import stat
import sys
import threading
from functools import reduce
from io import BytesIO

from py7zr.writerworker import Worker, FileWriter, BufferWriter
from py7zr.archiveinfo import Base, Header, SignatureHeader
from py7zr.exceptions import Bad7zFile, DecompressionError
from py7zr.properties import FileAttribute, MAGIC_7Z, READ_BLOCKSIZE
from py7zr.helper import calculate_crc32, filetime_to_dt, Local


# ------------------
# Exported Classes
# ------------------
class ArchiveFile(Base):
    """Informational class which holds the details about an
       archive member.
       ArchiveFile objects are returned by SevenZipFile.getmember(),
       SevenZipFile.getmembers() and are usually created internally.
    """

    __slots__ = ['digest', 'attributes', 'folder', 'size', 'uncompressed',
                 'filename']

    def __init__(self, info, archive, folder, maxsize):
        self.digest = None
        self.attributes = None
        self.folder = folder
        self.maxsize = maxsize
        for k, v in info.items():
            setattr(self, k, v)
        if hasattr(self, 'uncompressed'):
            self.size = reduce(self._plus, self.uncompressed)
        else:
            self.size = 0
        if not hasattr(self, 'filename'):
            # when compressed file is stored without a name
            try:
                basefilename = archive.filename
            except AttributeError:
                self.filename = 'contents'
            else:
                self.filename = os.path.splitext(os.path.basename(basefilename))[0]

    def _plus(self, a, b):
        return a + b

    def _test_attribute(self, target_bit):
        if not self.attributes:
            return False
        return self.attributes & target_bit == target_bit

    def is_archivable(self):
        return self._test_attribute(FileAttribute.ARCHIVE)

    def is_directory(self):
        return self._test_attribute(FileAttribute.DIRECTORY)

    def is_readonly(self):
        return self._test_attribute(FileAttribute.READONLY)

    def is_executable(self):
        """
        :return: True if unix mode is read+exec, otherwise False
        """
        if self._test_attribute(FileAttribute.UNIX_EXTENSION):
            st_mode = self.attributes >> 16
            if (st_mode & 0b0101 == 0b0101):
                return True
        return False

    def is_symlink(self):
        if self._test_attribute(FileAttribute.UNIX_EXTENSION):
            st_mode = self.attributes >> 16
            return stat.S_ISLNK(st_mode)
        return False

    def get_posix_mode(self):
        """
        :return: Return file stat mode can be set by os.chmod()
        """
        if self._test_attribute(FileAttribute.UNIX_EXTENSION):
            st_mode = self.attributes >> 16
            return stat.S_IMODE(st_mode)
        return None

    def get_st_fmt(self):
        """
        :return: Return the portion of the file mode that describes the file type
        """
        if self._test_attribute(FileAttribute.UNIX_EXTENSION):
            st_mode = self.attributes >> 16
            return stat.S_IFMT(st_mode)
        return None

    def decompress(self, input, fp, can_partial_decompress=False):
        decompressor = self.folder.decompressor
        if not input:
            remaining = self.size
            out = io.BytesIO()
            cache = getattr(self.folder, '_decompress_cache', None)
            if cache is not None:
                data, pos = cache
                out.write(data)
                remaining -= len(data)
                fp.seek(pos)
            checkremaining = not self.folder.solid and can_partial_decompress
            while remaining > 0:
                data = fp.read(READ_BLOCKSIZE)
                if checkremaining or len(data) < READ_BLOCKSIZE:
                    tmp = decompressor.decompress(data, remaining)
                else:
                    tmp = decompressor.decompress(data)
                if not tmp and not data:
                    raise DecompressionError('end of stream while decompressing')
                out.write(tmp)
                remaining -= len(tmp)

            data = out.getvalue()
            if self.folder.solid:
                # don't decompress start of solid archive for next file
                # TODO: limit size of cached data
                self.folder._decompress_cache = (data, fp.tell())
        else:
            if can_partial_decompress:
                data = decompressor.decompress(input, self.size)
            else:
                data = decompressor.decompress(input)
        return data[: self.size]


class SevenZipFile(Base):
    """The SevenZipFile Class provides an interface to 7z archives."""

    def __init__(self, file, mode='r'):
        # Check if we were passed a file-like object or not
        self.files = []
        self.files_map = {}
        if isinstance(file, str):
            self._filePassed = False
            self.filename = file
            modeDict = {'r': 'rb', 'w': 'w+b', 'x': 'x+b', 'a': 'r+b',
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
        self.solid = False
        try:
            if mode == "r":
                self._real_get_contents(self.fp)
            elif mode in ('w', 'x'):
                raise NotImplementedError
            elif mode == 'a':
                raise NotImplementedError
            else:
                raise ValueError("Mode must be 'r', 'w', 'x', or 'a'")
        except Exception as e:
            fp = self.fp
            self.fp = None
            self._fpclose(fp)
            raise e
        self.reset()

    def _fpclose(self, fp):
        assert self._fileRefCnt > 0
        self._fileRefCnt -= 1
        if not self._fileRefCnt and not self._filePassed:
            fp.close()

    def _real_get_contents(self, fp):
        if MAGIC_7Z != fp.read(len(MAGIC_7Z)):
            raise Bad7zFile('not a 7z file')
        self.sig_header = SignatureHeader(self.fp)
        self.afterheader = self.fp.tell()
        self.fp.seek(self.sig_header.nextheaderofs, 1)
        buffer = BytesIO(self.fp.read(self.sig_header.nextheadersize))
        headerrawdata = buffer.getvalue()
        if not self.checkcrc(self.sig_header.nextheadercrc, headerrawdata):
            raise Bad7zFile('invalid header data')
        header = Header(fp, buffer, self.afterheader)
        if header is None:
            return
        files_list = self._decode_file_info(header)
        # Set retrieved archive properties into SevenZipFile properties
        self.numfiles = len(files_list)
        self.header = header
        self.filenames = list(map(lambda x: x.filename, files_list))
        self.files_map.update([(x.filename, x) for x in files_list])
        self.files = files_list
        buffer.close()

    def _decode_file_info(self, header):
        files_list = []
        self.unpacksizes = [0]
        if hasattr(header, 'main_streams'):
            folders = header.main_streams.unpackinfo.folders
            packinfo = header.main_streams.packinfo
            subinfo = header.main_streams.substreamsinfo
            packsizes = packinfo.packsizes
            self.solid = packinfo.numstreams == 1
            if hasattr(subinfo, 'unpacksizes'):
                self.unpacksizes = subinfo.unpacksizes
            else:
                self.unpacksizes = [x.unpacksizes for x in folders]
        else:
            subinfo = None
            folders = None
            packinfo = None
            packsizes = []

        src_pos = self.afterheader
        folder_index = 0
        output_binary_index = 0
        streamidx = 0
        pos = 0
        instreamindex = 0
        folder_pos = src_pos

        if getattr(header, 'files_info', None) is None:
            return files_list

        for file_info in header.files_info.files:
            if not file_info['emptystream'] or folders is None:
                folder = folders[folder_index]
                if streamidx == 0:
                    folder.solid = subinfo.num_unpackstreams_folders[folder_index] > 1

                maxsize = (folder.solid and packinfo.packsizes[instreamindex]) or None
                uncompressed = self.unpacksizes[output_binary_index]
                if not isinstance(uncompressed, (list, tuple)):
                    uncompressed = [uncompressed] * len(folder.coders)
                if pos > 0:
                    # file is part of solid archive
                    assert instreamindex < len(packsizes), 'Folder outside index for solid archive'
                    file_info['compressed'] = packsizes[instreamindex]
                elif instreamindex < len(packsizes):
                    # file is compressed
                    file_info['compressed'] = packsizes[instreamindex]
                else:
                    # file is not compressed
                    file_info['compressed'] = uncompressed
                file_info['uncompressed'] = uncompressed
                numinstreams = 1
                for coder in folder.coders:
                    numinstreams = max(numinstreams, coder.get('numinstreams', 1))
                file_info['packsizes'] = packsizes[instreamindex:instreamindex + numinstreams]
                streamidx += 1
            else:
                file_info['compressed'] = 0
                file_info['uncompressed'] = [0]
                file_info['packsizes'] = [0]
                folder = None
                maxsize = 0
                numinstreams = 1

            file_info['folder'] = folder
            file_info['offset'] = pos

            archive_file = ArchiveFile(file_info, self, folder, maxsize)
            if folder is not None and subinfo.digestsdefined[output_binary_index]:
                archive_file.digest = subinfo.digests[output_binary_index]
            files_list.append(archive_file)

            if folder is not None:
                if folder.solid:
                    pos += self.unpacksizes[output_binary_index]
                output_binary_index += 1
            else:
                src_pos += file_info['compressed']
            if folder is not None and streamidx >= subinfo.num_unpackstreams_folders[folder_index]:
                pos = 0
                for x in range(numinstreams):
                    folder_pos += packinfo.packsizes[instreamindex + x]
                src_pos = folder_pos
                folder_index += 1
                instreamindex += numinstreams
                streamidx = 0

        return files_list

    @classmethod
    def _check_7zfile(cls, fp):
        signature = fp.peek(len(MAGIC_7Z))[:len(MAGIC_7Z)]
        if signature != MAGIC_7Z:
            return False
        return True

    # --------------------------------------------------------------------------
    # The public methods which SevenZipFile provides:
    # interface like TarFile

    def getnames(self):
        """Return the members of the archive as a list of their names. It has
           the same order as the list returned by getmembers().
        """
        return list(map(lambda x: x.filename, self.files))

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

    def reset(self):
        self.fp.seek(self.afterheader)
        self.worker = Worker(self.files, self.fp)

    def get(self, member, buf):
        if not isinstance(buf, io.BytesIO):
            raise DecompressionError
        if not isinstance(member, ArchiveFile):
            raise DecompressionError
        self.worker.register_reader(member.filename, BufferWriter(buf))

    def list(self, verbose=True, file=sys.stdout):
        """Print a table of contents to sys.stdout. If `verbose' is False, only
           the names of the members are printed. If it is True, an `ls -l'-like
           output is produced.
        """
        file.write('total %d files and directories in %sarchive\n' % (self.numfiles, (self.solid and 'solid ') or ''))
        if not verbose:
            file.write('\n'.join(self.getnames()) + '\n')
            return
        file.write('   Date      Time    Attr         Size   Compressed  Name\n')
        file.write('------------------- ----- ------------ ------------  ------------------------\n')
        for f in self.files:
            if getattr(f, 'lastwritetime', None) is not None:
                creationdate = filetime_to_dt(f.lastwritetime).astimezone(Local).strftime("%Y-%m-%d")
                creationtime = filetime_to_dt(f.lastwritetime).astimezone(Local).strftime("%H:%M:%S")
            else:
                creationdate = '         '
                creationtime = '         '
            if f.is_directory():
                attrib = 'D...'
            else:
                attrib = '....'
            if f.is_archivable():
                attrib += 'A'
            else:
                attrib += '.'
            extra = (f.compressed and '%12d ' % (f.compressed)) or '           0 '
            file.write('%s %s %s %12d %s %s\n' % (creationdate, creationtime, attrib, f.size, extra, f.filename))
        file.write('------------------- ----- ------------ ------------  ------------------------\n')

    def extract(self):
        self.worker.extract(self.fp)

    def extractall(self, path=None, crc=False):
        """Extract all members from the archive to the current working
           directory and set owner, modification time and permissions on
           directories afterwards. `path' specifies a different directory
           to extract to.
        """
        target_sym = []
        self.reset()
        if path is not None and not os.path.exists(path):
            os.mkdir(path)
        for f in self.files:
            if path is not None:
                outfilename = os.path.join(path, f.filename)
            else:
                outfilename = f.filename
            if f.is_directory():
                os.mkdir(outfilename)
            elif f.is_symlink():
                sym_src = f.link_target()
                if path:
                    sym_src = os.path.join(path, sym_src)
                pair = (sym_src, outfilename)
                target_sym.append(pair)
            else:
                self.worker.register_reader(f.filename, FileWriter(open(outfilename, 'wb')))
        self.worker.extract(self.fp)
        self.worker.close()
        for s, t in target_sym:
            os.symlink(s.sym_src, s.outfilename)


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


def main():
    parser = argparse.ArgumentParser(prog='py7zr', description='py7zr',
                                     formatter_class=argparse.RawTextHelpFormatter, add_help=True)
    parser.add_argument('subcommand', choices=['l', 'x'], help="command l list, x extract")
    parser.add_argument('-o', nargs='?', help="output directory")
    parser.add_argument("file", help="7z archive file")

    args = parser.parse_args()
    com = args.subcommand
    target = args.file
    if not is_7zfile(target):
        print('not a 7z file')
        exit(1)

    if com == 'l':
        with open(target, 'rb') as f:
            a = SevenZipFile(f)
            a.list()
        exit(0)

    if com == 'x':
        with open(target, 'rb') as f:
            a = SevenZipFile(f)
            if args.o:
                a.extractall(path=args.o)
            else:
                a.extractall()
        exit(0)
