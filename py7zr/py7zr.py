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
import functools
import io
import os
import stat
import sys
import threading
from copy import deepcopy
from io import BytesIO

from py7zr import FileAttribute
from py7zr.archiveinfo import Header, SignatureHeader
from py7zr.exceptions import Bad7zFile
from py7zr.helpers import filetime_to_dt, Local, checkcrc, ArchiveTimestamp
from py7zr.properties import MAGIC_7Z, QUEUELEN, READ_BLOCKSIZE


# ------------------
# Exported Classes
# ------------------
class SevenZipFile:
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
        if not self._check_7zfile(fp):
            raise Bad7zFile('not a 7z file')
        self.sig_header = SignatureHeader(self.fp)
        self.afterheader = self.fp.tell()
        buffer = self._read_header_data()
        header = Header(self.fp, buffer, self.afterheader)
        if header is None:
            return
        self.header = header
        buffer.close()
        self.files = ArchiveFilesList(self, header, self.afterheader)
        self.solid = self.files.solid

    def _read_header_data(self):
        self.fp.seek(self.sig_header.nextheaderofs, 1)
        buffer = BytesIO(self.fp.read(self.sig_header.nextheadersize))
        headerrawdata = buffer.getvalue()
        if not checkcrc(self.sig_header.nextheadercrc, headerrawdata):
            raise Bad7zFile('invalid header data')
        return buffer

    def reset(self):
        self.fp.seek(self.afterheader)
        self.worker = Worker(self.files, self.fp, self.afterheader)

    @classmethod
    def _check_7zfile(cls, fp):
        signature = fp.read(len(MAGIC_7Z))[:len(MAGIC_7Z)]
        if signature != MAGIC_7Z:
            return False
        return True

    # --------------------------------------------------------------------------
    # The public methods which SevenZipFile provides:
    def get_num_files(self):
        return self.files.len

    def getnames(self):
        """Return the members of the archive as a list of their names. It has
           the same order as the list returned by getmembers().
        """
        return list(map(lambda x: x.filename, self.files))

    def list(self, file=sys.stdout):
        """Print a table of contents to sys.stdout. If `verbose' is False, only
           the names of the members are printed. If it is True, an `ls -l'-like
           output is produced.
        """
        file.write('total %d files and directories in %sarchive\n' % (self.files.len, (self.solid and 'solid ') or ''))
        file.write('   Date      Time    Attr         Size   Compressed  Name\n')
        file.write('------------------- ----- ------------ ------------  ------------------------\n')
        for f in self.files:
            if f.lastwritetime is not None:
                creationdate = filetime_to_dt(f.lastwritetime).astimezone(Local).strftime("%Y-%m-%d")
                creationtime = filetime_to_dt(f.lastwritetime).astimezone(Local).strftime("%H:%M:%S")
            else:
                creationdate = '         '
                creationtime = '         '
            if f.is_directory:
                attrib = 'D...'
            else:
                attrib = '....'
            if f.archivable:
                attrib += 'A'
            else:
                attrib += '.'
            extra = (f.compressed and '%12d ' % (f.compressed)) or '           0 '
            file.write('%s %s %s %12d %s %s\n' % (creationdate, creationtime, attrib,
                                                  f.uncompressed_size, extra, f.filename))
        file.write('------------------- ----- ------------ ------------  ------------------------\n')

    def _set_file_property(self, outfilename, properties):
        # creation time
        creationtime = ArchiveTimestamp(properties['lastwritetime']).totimestamp()
        if creationtime is not None:
            os.utime(outfilename, times=(creationtime, creationtime))
        if os.name == 'posix':
            st_mode = properties['posix_mode']
            if st_mode is not None:
                os.chmod(outfilename, st_mode)
                return
        # fallback: only set readonly if specified
        if properties['readonly'] and not properties['is_directory']:
            ro_mask = 0o777 ^ (stat.S_IWRITE | stat.S_IWGRP | stat.S_IWOTH)
            os.chmod(outfilename, os.stat(outfilename).st_mode & ro_mask)

    def extractall(self, path=None, crc=False):
        """Extract all members from the archive to the current working
           directory and set owner, modification time and permissions on
           directories afterwards. `path' specifies a different directory
           to extract to.
        """
        target_sym = []
        target_files = []
        self.reset()
        if path is not None and not os.path.exists(path):
            os.mkdir(path)
        for f in self.files:
            if path is not None:
                outfilename = os.path.join(path, f.filename)
            else:
                outfilename = f.filename
            if f.is_directory:
                if not os.path.exists(outfilename):
                    os.mkdir(outfilename)
                    target_files.append((outfilename, f.get_properties()))
                else:
                    pass
            elif f.is_socket:
                pass
            elif f.is_symlink:
                buf = io.BytesIO()
                pair = (buf, f.filename)
                target_sym.append(pair)
                self.worker.register_filelike(f.id, buf)
            else:
                self.worker.register_filelike(f.id, outfilename)
                target_files.append((outfilename, f.get_properties()))
        self.worker.extract(self.fp)
        # Handle symlink before calling close()
        for b, t in target_sym:
            b.seek(0)
            sym_src = b.read().decode(encoding='utf-8')
            dirname = os.path.dirname(t)
            if path:
                sym_src = os.path.join(path, dirname, sym_src)
                sym_dst = os.path.join(path, t)
            else:
                sym_src = os.path.join(dirname, sym_src)
                sym_dst = t
            os.symlink(sym_src, sym_dst)
        self.worker.close()
        for o, p in target_files:
            self._set_file_property(o, p)


class ArchiveFile:
    def __init__(self, fileslist, length):
        self.files_list = fileslist
        self.length = length
        self.iteration_count = 0

    def __next__(self):
        self.iteration_count += 1
        if self.iteration_count > self.length:
            raise StopIteration()
        else:
            return self

    @property
    def id(self):
        if self.iteration_count == 0:
            raise RuntimeError
        return self.iteration_count - 1

    def get_properties(self):
        property = deepcopy(self.files_list[self.id])
        property['readonly'] = self.readonly
        property['posix_mode'] = self.posix_mode
        property['archivable'] = self.archivable
        property['is_directory'] = self.is_directory
        return property

    def _get_property(self, key):
        try:
            return self.files_list[self.id][key]
        except KeyError:
            return None

    @property
    def folder(self):
        return self._get_property('folder')

    @property
    def filename(self):
        return self._get_property('filename')

    @property
    def emptystream(self):
        return self._get_property('emptystream')

    @property
    def uncompressed(self):
        return self._get_property('uncompressed')

    @property
    def uncompressed_size(self):
        return functools.reduce(self._plus, self.uncompressed)

    @property
    def compressed(self):
        return self._get_property('compressed')

    def _plus(self, a, b):
        return a + b

    def _test_attribute(self, target_bit):
        attributes = self._get_property('attributes')
        if attributes is None:
            return False
        return attributes & target_bit == target_bit

    @property
    def archivable(self):
        return self._test_attribute(FileAttribute.ARCHIVE)

    @property
    def is_directory(self):
        return self._test_attribute(FileAttribute.DIRECTORY)

    @property
    def readonly(self):
        return self._test_attribute(FileAttribute.READONLY)

    def _get_unix_extension(self):
        attributes = self._get_property('attributes')
        if self._test_attribute(FileAttribute.UNIX_EXTENSION):
            return attributes >> 16
        return None

    @property
    def executable(self):
        """
        :return: True if unix mode is read+exec, otherwise False
        """
        e = self._get_unix_extension()
        if e is not None:
            if e & 0b0101 == 0b0101:
                return True
        return False

    @property
    def is_symlink(self):
        e = self._get_unix_extension()
        if e is not None:
            return stat.S_ISLNK(e)
        return False

    @property
    def is_socket(self):
        e = self._get_unix_extension()
        if e is not None:
            return stat.S_ISSOCK(e)
        return False

    @property
    def lastwritetime(self):
        return self._get_property('lastwritetime')

    @property
    def posix_mode(self):
        """
        :return: Return file stat mode can be set by os.chmod()
        """
        e = self._get_unix_extension()
        if e is not None:
            return stat.S_IMODE(e)
        return None

    @property
    def st_fmt(self):
        """
        :return: Return the portion of the file mode that describes the file type
        """
        e = self._get_unix_extension()
        if e is not None:
            return stat.S_IFMT(e)
        return None


class ArchiveFilesList:
    def __init__(self, archive, header, src_pos):
        self.header = header
        self._files_list = []
        self.solid = False
        self.iteration_count = 0
        if getattr(header, 'files_info', None) is None:
            return

        # Initialize references for convenience
        if hasattr(header, 'main_streams'):
            folders = header.main_streams.unpackinfo.folders
            packinfo = header.main_streams.packinfo
            subinfo = header.main_streams.substreamsinfo
            packsizes = packinfo.packsizes
            self.solid = packinfo.numstreams == 1
            if hasattr(subinfo, 'unpacksizes'):
                unpacksizes = subinfo.unpacksizes
            else:
                unpacksizes = [x.unpacksizes for x in folders]
        else:
            subinfo = None
            folders = None
            packinfo = None
            packsizes = []
            unpacksizes = [0]

        # Initialize loop index variables
        folder_index = 0
        output_binary_index = 0
        streamidx = 0
        pos = 0
        instreamindex = 0
        folder_pos = src_pos

        for file_info in header.files_info.files:

            if not file_info['emptystream'] and folders is not None:
                folder = folders[folder_index]
                if streamidx == 0:
                    folder.solid = subinfo.num_unpackstreams_folders[folder_index] > 1

                file_info['maxsize'] = (folder.solid and packinfo.packsizes[instreamindex]) or None
                uncompressed = unpacksizes[output_binary_index]
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
                file_info['maxsize'] = 0
                numinstreams = 1

            file_info['folder'] = folder
            file_info['offset'] = pos
            if folder is not None and subinfo.digestsdefined[output_binary_index]:
                file_info['digest'] = subinfo.digests[output_binary_index]

            if 'filename' not in file_info:
                # compressed file is stored without a name, generate one
                try:
                    basefilename = archive.filename
                except AttributeError:
                    # 7z archive file doesn't have a name
                    file_info['filename'] = 'contents'
                else:
                    file_info['filename'] = os.path.splitext(os.path.basename(basefilename))[0]

            self._files_list.append(file_info)

            if folder is not None:
                if folder.solid:
                    pos += unpacksizes[output_binary_index]
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

    def __iter__(self):
        return ArchiveFile(self._files_list, self.len)

    @property
    def len(self):
        if getattr(self.header, 'files_info', None) is not None:
            return len(self.header.files_info.files)
        return 0


# --------------------
# exported functions
# --------------------
def is_7zfile(file):
    """Quickly see if a file is a 7Z file by checking the magic number.
    The filename argument may be a file or file-like object too.
    """
    result = False
    try:
        if hasattr(file, "read"):
            result = SevenZipFile._check_7zfile(fp=file)
            file.seek(-len(MAGIC_7Z), 1)
        else:
            with open(file, "rb") as fp:
                result = SevenZipFile._check_7zfile(fp)
    except OSError:
        pass
    return result


def unpack_7zarchive(archive, path, extra=None):
    """Function for registering with shutil.register_unpack_archive()"""
    arc = SevenZipFile(archive)
    arc.extractall(path)


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


class BufferWriter():

    def __init__(self, target):
        self.buf = target

    def open(self):
        pass

    def write(self, data):
        self.buf.write(data)

    def flush(self):
        pass

    def close(self):
        self.buf.close()


class FileWriter():

    def __init__(self, target):
        self.target = target

    def open(self):
        self.fp = open(self.target, 'wb')

    def write(self, data):
        self.fp.write(data)

    def flush(self):
        self.fp.flush()

    def close(self):
        self.fp.close()


class Worker():
    """Extract worker class to invoke handler"""

    def __init__(self, files, fp, src_start):
        self.handler = {}
        self.files = files
        self.fp = fp
        self.src_start = src_start

    def register_writer(self, index, func):
        self.handler[index] = func

    def extract(self, fp):
        fp.seek(self.src_start)
        for f in self.files:
            if f.emptystream:
                continue
            else:
                fileish = self.handler.get(f.id, None)
                fileish.open()
                for s in f.uncompressed:
                    self.decompress(fp, f.folder, fileish, s, f.compressed)

    def close(self):
        for f in self.files:
            handler = self.handler.get(f.id, None)
            if handler is not None:
                handler.close()

    def decompress(self, fp, folder, fileish, size, compressed_size):
        if folder is None:
            fileish.write(b'')
            return
        out_remaining = size
        decompressor = folder.get_decompressor(compressed_size)
        queue = folder.queue
        queue_maxlength = QUEUELEN
        if queue.len > 0:
            if out_remaining > queue.len:
                out_remaining -= queue.len
                fileish.write(queue.dequeue(queue.len))
            else:
                fileish.write(queue.dequeue(out_remaining))
                return

        while out_remaining > 0:
            if not decompressor.eof:
                if decompressor.needs_input:
                    read_size = min(READ_BLOCKSIZE, decompressor.remaining_size)
                    inp = fp.read(read_size)
                else:
                    inp = b''
                max_length = min(out_remaining, queue_maxlength - queue.len)
                tmp = decompressor.decompress(inp, max_length)
                if out_remaining >= len(tmp):
                    out_remaining -= len(tmp)
                    fileish.write(tmp)
                    if out_remaining <= 0:
                        break
                else:
                    queue.enqueue(tmp)
                    fileish.write(queue.dequeue(out_remaining))
                    break
            else:
                if queue.len >= 0:
                    fileish.write(queue.dequeue(out_remaining))
                break
        return

    def register_filelike(self, id, fileish):
        if isinstance(fileish, io.BytesIO):
            self.register_writer(id, BufferWriter(fileish))
        else:
            self.register_writer(id, FileWriter(fileish))
