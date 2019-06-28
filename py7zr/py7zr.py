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

import errno
import functools
import io
import operator
import os
import stat
import sys
import threading
from io import BytesIO
from typing import Any, BinaryIO, Dict, List, Optional, Union

from py7zr.archiveinfo import Folder, Header, SignatureHeader
from py7zr.compression import Worker, get_methods_names
from py7zr.exceptions import Bad7zFile
from py7zr.helpers import (ArchiveTimestamp, Local, calculate_crc32,
                           filetime_to_dt)
from py7zr.properties import MAGIC_7Z, Configuration, FileAttribute


class ArchiveFile:
    def __init__(self, id: int, file_info: Dict[str, Any]) -> None:
        self.id = id
        self._file_info = file_info

    def file_properties(self) -> Dict[str, Any]:
        properties = self._file_info
        if properties is not None:
            properties['readonly'] = self.readonly
            properties['posix_mode'] = self.posix_mode
            properties['archivable'] = self.archivable
            properties['is_directory'] = self.is_directory
        return properties

    def _get_property(self, key: str) -> Any:
        try:
            return self._file_info[key]
        except KeyError:
            return None

    @property
    def folder(self) -> Folder:
        return self._get_property('folder')

    @property
    def filename(self) -> str:
        return self._get_property('filename')

    @property
    def emptystream(self) -> bool:
        return self._get_property('emptystream')

    @property
    def uncompressed(self) -> List[int]:
        return self._get_property('uncompressed')

    @property
    def uncompressed_size(self):
        return functools.reduce(operator.add, self.uncompressed)

    @property
    def compressed(self) -> Optional[int]:
        return self._get_property('compressed')

    def _test_attribute(self, target_bit: FileAttribute) -> bool:
        attributes = self._get_property('attributes')
        if attributes is None:
            return False
        return attributes & target_bit == target_bit

    @property
    def archivable(self) -> bool:
        return self._test_attribute(FileAttribute.ARCHIVE)

    @property
    def is_directory(self) -> bool:
        return self._test_attribute(FileAttribute.DIRECTORY)

    @property
    def readonly(self) -> bool:
        return self._test_attribute(FileAttribute.READONLY)

    def _get_unix_extension(self) -> Optional[int]:
        attributes = self._get_property('attributes')
        if self._test_attribute(FileAttribute.UNIX_EXTENSION):
            return attributes >> 16
        return None

    @property
    def is_symlink(self) -> bool:
        e = self._get_unix_extension()
        if e is not None:
            return stat.S_ISLNK(e)
        return False

    @property
    def is_socket(self) -> bool:
        e = self._get_unix_extension()
        if e is not None:
            return stat.S_ISSOCK(e)
        return False

    @property
    def lastwritetime(self):
        return self._get_property('lastwritetime')

    @property
    def posix_mode(self) -> Optional[int]:
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

    def __init__(self, offset: int = 0):
        self.files_list = []  # type: List[dict]
        self.index = 0
        self.offset = offset

    def append(self, file_info: Dict[str, Any]) -> None:
        self.files_list.append(file_info)

    @property
    def len(self) -> int:
        return len(self.files_list)

    def __iter__(self) -> 'ArchiveFileList':
        self.index = 0
        return self

    def __next__(self) -> ArchiveFile:
        if self.index == len(self.files_list):
            raise StopIteration
        res = ArchiveFile(self.index + self.offset, self.files_list[self.index])
        self.index += 1
        return res


# ------------------
# Exported Classes
# ------------------
class SevenZipFile:
    """The SevenZipFile Class provides an interface to 7z archives."""

    def __init__(self, file: BinaryIO, mode: str = 'r') -> None:
        if mode not in ('r', 'w', 'x', 'a'):
            raise ValueError("ZipFile requires mode 'r', 'w', 'x', or 'a'")
        # Check if we were passed a file-like object or not
        if isinstance(file, str):
            self._filePassed = False  # type: bool
            self.filename = file  # type: Optional[str]
            modes = {'r': 'rb', 'w': 'w+b', 'x': 'x+b', 'a': 'r+b',
                     'r+b': 'w+b', 'w+b': 'wb', 'x+b': 'xb'}
            try:
                filemode = modes[mode]
            except KeyError:
                raise ValueError("Mode must be 'r', 'w', 'x', or 'a'")
            while True:
                try:
                    self.fp = open(file, filemode)  # type: BinaryIO
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
                self.reset()
            elif mode in 'w':
                self.files = ArchiveFileList()
            elif mode in 'x':
                raise NotImplementedError
            elif mode == 'a':
                raise NotImplementedError
            else:
                raise ValueError("Mode must be 'r', 'w', 'x', or 'a'")
        except Exception as e:
            fp = self.fp
            self._fpclose(fp)
            raise e

    def _fpclose(self, fp):
        assert self._fileRefCnt > 0
        self._fileRefCnt -= 1
        if not self._fileRefCnt and not self._filePassed:
            fp.close()

    def _real_get_contents(self, fp: BinaryIO) -> None:
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

    def _read_header_data(self) -> BytesIO:
        self.fp.seek(self.sig_header.nextheaderofs, 1)
        buffer = io.BytesIO(self.fp.read(self.sig_header.nextheadersize))
        if self.sig_header.nextheadercrc != calculate_crc32(buffer.getvalue()):
            raise Bad7zFile('invalid header data')
        return buffer

    def _filelist_retrieve(self) -> None:
        src_pos = self.afterheader
        # Initialize references for convenience
        if hasattr(self.header, 'main_streams'):
            folders = self.header.main_streams.unpackinfo.folders
            packinfo = self.header.main_streams.packinfo
            subinfo = self.header.main_streams.substreamsinfo
            packsizes = packinfo.packsizes
            self.solid = packinfo.numstreams == 1
            if subinfo.unpacksizes is not None:
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
        file_in_solid = 0
        instreamindex = 0
        folder_pos = src_pos

        for file_id, file_info in enumerate(self.header.files_info.files):

            if not file_info['emptystream'] and folders is not None:
                folder = folders[folder_index]
                if streamidx == 0:
                    folder.solid = subinfo.num_unpackstreams_folders[folder_index] > 1

                file_info['maxsize'] = (folder.solid and packinfo.packsizes[instreamindex]) or None
                uncompressed = unpacksizes[output_binary_index]
                if not isinstance(uncompressed, (list, tuple)):
                    uncompressed = [uncompressed] * len(folder.coders)
                if file_in_solid > 0:
                    # file is part of solid archive
                    # assert instreamindex < len(packsizes), 'Folder outside index for solid archive'
                    # file_info['compressed'] = packsizes[instreamindex]
                    file_info['compressed'] = None
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
                    if basefilename is not None:
                        fn, ext = os.path.splitext(os.path.basename(basefilename))
                        file_info['filename'] = fn
                    else:
                        file_info['filename'] = 'contents'

            self.files.append(file_info)

            if folder is not None:
                if folder.solid:
                    # file_in_solid += unpacksizes[output_binary_index]
                    file_in_solid = 1
                output_binary_index += 1
            else:
                src_pos += file_info['compressed']
            if folder is not None:
                if folder.files is None:
                    folder.files = ArchiveFileList(offset=file_id)
                folder.files.append(file_info)
            if folder is not None and streamidx >= subinfo.num_unpackstreams_folders[folder_index]:
                file_in_solid = 0
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

    def _set_file_property(self, outfilename: str, properties: Dict[str, Any]) -> None:
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

    def reset(self) -> None:
        self.fp.seek(self.afterheader)
        self.worker = Worker(self.files, self.afterheader, self.header)

    @classmethod
    def _check_7zfile(cls, fp: BinaryIO) -> bool:
        return MAGIC_7Z == fp.read(len(MAGIC_7Z))[:len(MAGIC_7Z)]

    def _print_archiveinfo(self, file=None):
        if file is None:
            file = sys.stdout
        file.write("--\n")
        file.write("Path = {}\n".format(self.filename))
        file.write("Type = 7z\n")
        fstat = os.stat(self.filename)
        file.write("Phisical Size = {}\n".format(fstat.st_size))
        file.write("Headers Size = {}\n".format(self.header.size))  # fixme.
        file.write("Method = {}\n".format(self._print_methods()))
        if self.solid:
            file.write("Solid = {}\n".format('+'))
        else:
            file.write("Solid = {}\n".format('-'))
        file.write("Blocks = {}\n".format(len(self.header.main_streams.unpackinfo.folders)))

    def _print_methods(self):
        methods_names = []
        for folder in self.header.main_streams.unpackinfo.folders:
            methods_names += get_methods_names(folder.coders)
        return ', '.join(str(x) for x in methods_names)

    def _test_digest_raw(self, pos, size, crc):
        self.fp.seek(pos)
        remaining_size = size
        digest = None
        while remaining_size > 0:
            block = min(Configuration.read_blocksize, remaining_size)
            digest = calculate_crc32(self.fp.read(block), digest)
            remaining_size -= block
        return digest == crc

    def _test_pack_digest(self):
        self.reset()
        crcs = self.header.main_streams.packinfo.crcs
        if crcs is not None and len(crcs) > 0:
            # check packed stream's crc
            for i, p in enumerate(self.header.main_streams.packinfo.packpositions):
                if not self._test_digest_raw(p, self.header.main_streams.packinfo.packsizes[i], crcs[i]):
                    return False
        return True

    def _test_unpack_digest(self):
        self.reset()
        for f in self.files:
            self.worker.register_filelike(f.id, None)
        try:
            self.worker.extract(self.fp)  # TODO: print progress
        except Bad7zFile:
            return False
        else:
            return True

    def _test_digests(self):
        if self._test_pack_digest():
            if self._test_unpack_digest():
                return True
        return False

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

    # --------------------------------------------------------------------------
    # The public methods which SevenZipFile provides:
    def getnames(self):
        """Return the members of the archive as a list of their names. It has
           the same order as the list returned by getmembers().
        """
        return list(map(lambda x: x.filename, self.files))

    def list(self, file=None, verbose=False):
        """Print a table of contents to sys.stdout. If `verbose' is False, only
           the names of the members are printed. If it is True, an `ls -l'-like
           output is produced.
        """
        if file is None:
            file = sys.stdout
        if verbose:
            file.write("Listing archive: {}\n".format(self.filename))
            self._print_archiveinfo(file=file)
            file.write('\n')
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
            if f.is_directory:
                extra = '           0 '
            elif f.compressed is None:
                extra = '             '
            else:
                extra = '%12d ' % (f.compressed)
            file.write('%s %s %s %12d %s %s\n' % (creationdate, creationtime, attrib,
                                                  f.uncompressed_size, extra, f.filename))
        file.write('------------------- ----- ------------ ------------  ------------------------\n')

    def test(self, file=None):
        if file is None:
            file = sys.stdout
        file.write("Testing archive: {}\n".format(self.filename))
        self._print_archiveinfo(file=file)
        file.write('\n')
        if self._test_digests():
            file.write('Everything is Ok\n')
            return True
        else:
            file.write('Bad 7zip file\n')
            return False
        # TODO: print number of folders, files and sizes

    def extractall(self, path: Optional[Any] = None) -> None:
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
            try:
                os.makedirs(path)
            except OSError as e:
                if e.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    raise

        multi_thread = self.header.main_streams.unpackinfo.numfolders > 1 and \
            self.header.main_streams.packinfo.numstreams == self.header.main_streams.unpackinfo.numfolders
        fnames = []  # type: List[str]
        for f in self.files:
            # TODO: sanity check
            # check whether f.filename with invalid characters: '../'
            if f.filename.startswith('../'):
                raise Bad7zFile
            # When archive has a multiple files which have same name.
            # To guarantee order of archive, multi-thread decompression becomes off.
            # Currently always overwrite by latter archives.
            # TODO: provide option to select overwrite or skip.
            if f.filename in fnames:
                multi_thread = False
            fnames.append(f.filename)
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
                raise Exception("Directory name is existed as a normal file.")
            else:
                raise Exception()
        self.worker.extract(self.fp, multithread=multi_thread)
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

    def writeall(self, path, arcname=None):
        if os.path.isfile(path):
            self.write(path, arcname)
        elif os.path.isdir(path):
            if arcname:
                self.write(path, arcname)
            for nm in sorted(os.listdir(path)):
                self.writeall(os.path.join(path, nm), os.path.join(arcname, nm))

    def write(self, file, arcname=None):
        file_info = {}
        if os.path.isfile(file):
            file_info['filename'] = arcname
            fstat = os.stat(file)
            file_info['uncompressed'] = fstat.st_size
        self.files.append(file_info)
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


# --------------------
# exported functions
# --------------------
def is_7zfile(file: Union[BinaryIO, str]) -> bool:
    """Quickly see if a file is a 7Z file by checking the magic number.
    The filename argument may be a file or file-like object too.
    """
    result = False
    try:
        if isinstance(file, io.IOBase) and hasattr(file, "read"):
            result = SevenZipFile._check_7zfile(file)
            file.seek(-len(MAGIC_7Z), 1)
        elif isinstance(file, str):
            with open(file, "rb") as fp:
                result = SevenZipFile._check_7zfile(fp)
        else:
            raise
    except OSError:
        pass
    return result


def unpack_7zarchive(archive, path, extra=None):
    """Function for registering with shutil.register_unpack_archive()"""
    arc = SevenZipFile(archive)
    arc.extractall(path)
