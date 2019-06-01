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

import functools
import io
import operator
import os
import stat
import sys
import threading

from py7zr.archiveinfo import Header, SignatureHeader
from py7zr.compression import Worker
from py7zr.exceptions import Bad7zFile
from py7zr.helpers import filetime_to_dt, Local, ArchiveTimestamp, calculate_crc32
from py7zr.properties import FileAttribute, MAGIC_7Z


class ArchiveFile:
    def __init__(self, id, file_info):
        self.id = id
        self._file_info = file_info

    def file_properties(self):
        properties = self._file_info
        if properties is not None:
            properties['readonly'] = self.readonly
            properties['posix_mode'] = self.posix_mode
            properties['archivable'] = self.archivable
            properties['is_directory'] = self.is_directory
        return properties

    def _get_property(self, key):
        try:
            return self._file_info[key]
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
        return functools.reduce(operator.add, self.uncompressed)

    @property
    def compressed(self):
        return self._get_property('compressed')

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


class ArchiveFileList:

    def __init__(self):
        self.files_list = []
        self.index = 0

    def append(self, file_info):
        self.files_list.append(file_info)

    @property
    def len(self):
        return len(self.files_list)

    def __iter__(self):
        self.index = 0
        return self

    def __next__(self):
        if self.index == len(self.files_list):
            raise StopIteration
        id = self.index
        self.index += 1
        return ArchiveFile(id, self.files_list[id])


# ------------------
# Exported Classes
# ------------------
class SevenZipFile:
    """The SevenZipFile Class provides an interface to 7z archives."""

    def __init__(self, file, mode='r'):
        if mode not in ('r', 'w', 'x', 'a'):
            raise ValueError("ZipFile requires mode 'r', 'w', 'x', or 'a'")
        self.files = []
        self.files_map = {}
        # Check if we were passed a file-like object or not
        if isinstance(file, str):
            self._filePassed = False
            self.filename = file
            modes = {'r': 'rb', 'w': 'w+b', 'x': 'x+b', 'a': 'r+b',
                     'r+b': 'w+b', 'w+b': 'wb', 'x+b': 'xb'}
            try:
                filemode = modes[mode]
            except KeyError:
                raise ValueError("Mode must be 'r', 'w', 'x', or 'a'")
            while True:
                try:
                    self.fp = io.open(file, filemode)
                except OSError:
                    if filemode in modes:
                        filemode = modes[filemode]
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
        self.sig_header = SignatureHeader.retrieve(self.fp)
        self.afterheader = self.fp.tell()
        buffer = self._read_header_data()
        header = Header.retrieve(self.fp, buffer, self.afterheader)
        if header is None:
            return
        self.header = header
        buffer.close()
        self.solid = False
        self.files = ArchiveFileList()
        if getattr(self.header, 'files_info', None) is not None:
            self._filelist_retrieve()

    def _read_header_data(self):
        self.fp.seek(self.sig_header.nextheaderofs, 1)
        buffer = io.BytesIO(self.fp.read(self.sig_header.nextheadersize))
        if self.sig_header.nextheadercrc != calculate_crc32(buffer.getvalue()):
            raise Bad7zFile('invalid header data')
        return buffer

    def _filelist_retrieve(self):
        src_pos = self.afterheader
        # Initialize references for convenience
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

        for file_info in self.header.files_info.files:

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
                    basefilename = self.filename
                except AttributeError:
                    # 7z archive file doesn't have a name
                    file_info['filename'] = 'contents'
                else:
                    file_info['filename'] = os.path.splitext(os.path.basename(basefilename))[0]

            self.files.append(file_info)

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

    def _num_files(self):
        if getattr(self.header, 'files_info', None) is not None:
            return len(self.header.files_info.files)
        return 0

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

    def reset(self):
        self.fp.seek(self.afterheader)
        self.worker = Worker(self.files, self.fp, self.afterheader)

    @classmethod
    def _check_7zfile(cls, fp):
        return MAGIC_7Z == fp.read(len(MAGIC_7Z))[:len(MAGIC_7Z)]

    # --------------------------------------------------------------------------
    # The public methods which SevenZipFile provides:
    def getnames(self):
        """Return the members of the archive as a list of their names. It has
           the same order as the list returned by getmembers().
        """
        return list(map(lambda x: x.filename, self.files))

    def list(self, file=None):
        """Print a table of contents to sys.stdout. If `verbose' is False, only
           the names of the members are printed. If it is True, an `ls -l'-like
           output is produced.
        """
        if file is None:
            file = sys.stdout
        file.write('total %d files and directories in %sarchive\n' % (self._num_files(), (self.solid and 'solid ') or ''))
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

    def extractall(self, path=None, crc=False):
        """Extract all members from the archive to the current working
           directory and set owner, modification time and permissions on
           directories afterwards. `path' specifies a different directory
           to extract to.
        """
        target_sym = []
        target_files = []
        target_dirs = []
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
                    target_dirs.append(outfilename)
                    target_files.append((outfilename, f.file_properties()))
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
                target_files.append((outfilename, f.file_properties()))
        for target_dir in sorted(target_dirs):
            if not os.path.exists(target_dir):
                os.mkdir(target_dir)
            elif os.path.isdir(target_dir):
                pass
            elif os.path.isfile(target_dir):
                raise("Directory name is existed as a normal file.")
            else:
                raise
        self.worker.extract(self.fp)
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
        for o, p in target_files:
            self._set_file_property(o, p)

    def testzip(self):
        raise NotImplementedError

    def write(self, filename, arcname=None):
        raise NotImplementedError

    def _make_file_info(self, target):
        f = {}
        f['filename'] = target
        if os.path.isdir(target):
            f['emptystream'] = True
            f['attributes'] = FileAttribute.DIRECTORY
            if os.name == 'posix':
                f['attributes'] |= FileAttribute.UNIX_EXTENSION | (stat.S_IFDIR << 16)
        elif os.path.islink(target):
            f['emptystream'] = True
            if os.name == 'posix':
                f['attributes'] = FileAttribute.UNIX_EXTENSION | (stat.S_IFLNK << 16)
            else:
                f['attributes'] = 0x0  # FIXME
        elif os.path.isfile(target):
            f['emptystream'] = False
            f['attributes'] = 0x0
        return f

    def close(self):
        raise NotImplementedError


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
