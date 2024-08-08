#!/usr/bin/python -u
#
# p7zr library
#
# Copyright (c) 2019-2022 Hiroshi Miura <miurahr@linux.com>
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
import collections.abc
import contextlib
import datetime
import errno
import functools
import io
import os
import pathlib
import queue
import re
import stat
import sys
import time
from multiprocessing import Process
from shutil import ReadError
from threading import Thread
from typing import IO, Any, BinaryIO, Collection, Dict, List, Optional, Tuple, Type, Union

import multivolumefile

from py7zr.archiveinfo import Folder, Header, SignatureHeader
from py7zr.callbacks import ExtractCallback
from py7zr.compressor import SupportedMethods, get_methods_names
from py7zr.exceptions import (
    AbsolutePathError,
    Bad7zFile,
    CrcError,
    DecompressionError,
    InternalError,
    UnsupportedCompressionMethodError,
)
from py7zr.helpers import (
    ArchiveTimestamp,
    MemIO,
    NullIO,
    calculate_crc32,
    check_archive_path,
    filetime_to_dt,
    get_sanitized_output_path,
    is_path_valid,
    readlink,
)
from py7zr.properties import DEFAULT_FILTERS, FILTER_DEFLATE64, MAGIC_7Z, get_default_blocksize, get_memory_limit

if sys.platform.startswith("win"):
    import _winapi

FILE_ATTRIBUTE_UNIX_EXTENSION = 0x8000
FILE_ATTRIBUTE_WINDOWS_MASK = 0x07FFF


class ArchiveFile:
    """Represent each files metadata inside archive file.
    It holds file properties; filename, permissions, and type whether
    it is directory, link or normal file.

    Instances of the :class:`ArchiveFile` class are returned by iterating :attr:`files_list` of
    :class:`SevenZipFile` objects.
    Each object stores information about a single member of the 7z archive. Most of users use :meth:`extractall()`.

    The class also hold an archive parameter where file is exist in
    archive file folder(container)."""

    def __init__(self, id: int, file_info: Dict[str, Any]) -> None:
        self.id = id
        self._file_info = file_info

    def file_properties(self) -> Dict[str, Any]:
        """Return file properties as a hash object. Following keys are included: ‘readonly’, ‘is_directory’,
        ‘posix_mode’, ‘archivable’, ‘emptystream’, ‘filename’, ‘creationtime’, ‘lastaccesstime’,
        ‘lastwritetime’, ‘attributes’
        """
        properties = self._file_info
        if properties is not None:
            properties["readonly"] = self.readonly
            properties["posix_mode"] = self.posix_mode
            properties["archivable"] = self.archivable
            properties["is_directory"] = self.is_directory
        return properties

    def _get_property(self, key: str) -> Any:
        try:
            return self._file_info[key]
        except KeyError:
            return None

    @property
    def origin(self) -> pathlib.Path:
        return self._get_property("origin")

    @property
    def folder(self) -> Folder:
        return self._get_property("folder")

    @property
    def filename(self) -> str:
        """return filename of archive file."""
        return self._get_property("filename")

    @property
    def emptystream(self) -> bool:
        """True if file is empty(0-byte file), otherwise False"""
        return self._get_property("emptystream")

    @property
    def uncompressed(self) -> List[int]:
        return self._get_property("uncompressed")

    @property
    def compressed(self) -> Optional[int]:
        """Compressed size"""
        return self._get_property("compressed")

    @property
    def crc32(self) -> Optional[int]:
        """CRC of archived file(optional)"""
        return self._get_property("digest")

    def _test_attribute(self, target_bit: int) -> bool:
        attributes = self._get_property("attributes")
        if attributes is None:
            return False
        return attributes & target_bit == target_bit

    @property
    def archivable(self) -> bool:
        """File has a Windows `archive` flag."""
        if hasattr(stat, "FILE_ATTRIBUTE_ARCHIVE"):
            return self._test_attribute(getattr(stat, "FILE_ATTRIBUTE_ARCHIVE"))
        return False

    @property
    def is_directory(self) -> bool:
        """True if file is a directory, otherwise False."""
        if hasattr(stat, "FILE_ATTRIBUTE_DIRECTORY"):
            return self._test_attribute(getattr(stat, "FILE_ATTRIBUTE_DIRECTORY"))
        return False

    @property
    def readonly(self) -> bool:
        """True if file is readonly, otherwise False."""
        if hasattr(stat, "FILE_ATTRIBUTE_READONLY"):
            return self._test_attribute(getattr(stat, "FILE_ATTRIBUTE_READONLY"))
        return False

    def _get_unix_extension(self) -> Optional[int]:
        attributes = self._get_property("attributes")
        if self._test_attribute(FILE_ATTRIBUTE_UNIX_EXTENSION):
            return attributes >> 16
        return None

    def data(self) -> Optional[BinaryIO]:
        return self._get_property("data")

    def has_strdata(self) -> bool:
        """True if file content is set by writestr() method otherwise False."""
        return "data" in self._file_info

    @property
    def is_symlink(self) -> bool:
        """True if file is a symbolic link, otherwise False."""
        e = self._get_unix_extension()
        if e is not None:
            return stat.S_ISLNK(e)
        if hasattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT"):
            return self._test_attribute(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT"))
        return False

    @property
    def is_junction(self) -> bool:
        """True if file is a junction/reparse point on windows, otherwise False."""
        if hasattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT"):
            return self._test_attribute(
                getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT") | getattr(stat, "FILE_ATTRIBUTE_DIRECTORY")
            )
        return False

    @property
    def is_socket(self) -> bool:
        """True if file is a socket, otherwise False."""
        e = self._get_unix_extension()
        if e is not None:
            return stat.S_ISSOCK(e)
        return False

    @property
    def lastwritetime(self) -> Optional[ArchiveTimestamp]:
        """Return last written timestamp of a file."""
        return self._get_property("lastwritetime")

    @property
    def posix_mode(self) -> Optional[int]:
        """
        posix mode when a member has a unix extension property, or None
        :return: Return file stat mode can be set by os.chmod()
        """
        e = self._get_unix_extension()
        if e is not None:
            return stat.S_IMODE(e)
        return None

    @property
    def st_fmt(self) -> Optional[int]:
        """
        :return: Return the portion of the file mode that describes the file type
        """
        e = self._get_unix_extension()
        if e is not None:
            return stat.S_IFMT(e)
        return None


class ArchiveFileList(collections.abc.Iterable):
    """Iteratable container of ArchiveFile."""

    def __init__(self, offset: int = 0):
        self.files_list: List[dict] = []
        self.index = 0
        self.offset = offset

    def append(self, file_info: Dict[str, Any]) -> None:
        self.files_list.append(file_info)

    def __len__(self) -> int:
        return len(self.files_list)

    def __iter__(self) -> "ArchiveFileListIterator":
        return ArchiveFileListIterator(self)

    def __getitem__(self, index):
        if index > len(self.files_list):
            raise IndexError
        if index < 0:
            raise IndexError
        res = ArchiveFile(index + self.offset, self.files_list[index])
        return res


class ArchiveFileListIterator(collections.abc.Iterator):
    def __init__(self, archive_file_list):
        self._archive_file_list = archive_file_list
        self._index = 0

    def __next__(self) -> ArchiveFile:
        if self._index == len(self._archive_file_list):
            raise StopIteration
        res = self._archive_file_list[self._index]
        self._index += 1
        return res


# ------------------
# Exported Classes
# ------------------
class ArchiveInfo:
    """Hold archive information"""

    def __init__(
        self,
        filename: str,
        stat: os.stat_result,
        header_size: int,
        method_names: List[str],
        solid: bool,
        blocks: int,
        uncompressed: List[int],
    ):
        self.stat = stat
        self.filename = filename
        self.size = stat.st_size
        self.header_size = header_size
        self.method_names = method_names
        self.solid = solid
        self.blocks = blocks
        self.uncompressed = uncompressed


class FileInfo:
    """Hold archived file information."""

    def __init__(
        self,
        filename,
        compressed,
        uncompressed,
        archivable,
        is_directory,
        creationtime,
        crc32,
    ):
        self.filename = filename
        self.compressed = compressed
        self.uncompressed = uncompressed
        self.archivable = archivable
        self.is_directory = is_directory
        self.creationtime = creationtime
        self.crc32 = crc32


class SevenZipFile(contextlib.AbstractContextManager):
    """The SevenZipFile Class provides an interface to 7z archives."""

    def __init__(
        self,
        file: Union[BinaryIO, str, pathlib.Path],
        mode: str = "r",
        *,
        filters: Optional[List[Dict[str, int]]] = None,
        dereference=False,
        password: Optional[str] = None,
        header_encryption: bool = False,
        blocksize: Optional[int] = None,
        mp: bool = False,
    ) -> None:
        # check invalid mode.
        if mode not in ("r", "w", "x", "a"):
            raise ValueError("ZipFile requires mode 'r', 'w', 'x', or 'a'")
        self.fp: BinaryIO
        self.mp = mp
        self.password_protected = password is not None
        if blocksize:
            self._block_size = blocksize
        else:
            self._block_size = get_default_blocksize()

        # https://github.com/python/cpython/blob/b5e142ba7c2063efe9bb8065c3b0bad33e2a9afa/Lib/zipfile/__init__.py#L1350
        # Check if we were passed a file-like object or not
        if isinstance(file, os.PathLike):
            file = os.fspath(file)
        if isinstance(file, str):
            # No, it's a filename
            self._filePassed = False
            self.filename = file
            modeDict = {
                "r": "rb",
                "w": "w+b",
                "x": "x+b",
                "a": "r+b",
                "r+b": "w+b",
                "w+b": "wb",
                "x+b": "xb",
            }
            filemode = modeDict[mode]

            while True:
                try:
                    self.fp = open(file, filemode)  # type: ignore
                except OSError:
                    if filemode in modeDict:
                        filemode = modeDict[filemode]
                        continue
                    raise
                break
            self.mode = mode
        elif isinstance(file, multivolumefile.MultiVolume):
            self._filePassed = True
            self.fp = file
            self.filename = None
            self.mode = mode  # noqa
        elif isinstance(file, io.IOBase):
            self._filePassed = True
            self.fp = file
            self.filename = getattr(file, "name", None)
            self.mode = mode  # noqa
        else:
            raise TypeError("invalid file: {}".format(type(file)))
        self.encoded_header_mode = True
        self.header_encryption = header_encryption
        self._fileRefCnt = 1
        try:
            if mode == "r":
                self._real_get_contents(password)
                self.fp.seek(self.afterheader)  # seek into start of payload and prepare worker to extract
                self.worker = Worker(self.files, self.afterheader, self.header, self.mp)
            elif mode == "w":
                self._prepare_write(filters, password)
            elif mode == "x":
                self._prepare_write(filters, password)
            elif mode == "a":
                try:
                    # Append if it's an existing 7zip file
                    self._real_get_contents(password)
                    self._prepare_append(filters, password)
                except Bad7zFile:
                    # Not an existing 7zip file, write instead
                    self._prepare_write(filters, password)
            else:
                raise ValueError("Mode must be 'r', 'w', 'x', or 'a'")  # never come here
        except Exception as e:
            self._fpclose()
            raise e
        self._dict: Dict[str, IO[Any]] = {}
        self.dereference = dereference
        self.reporterd: Optional[Thread] = None
        self.q: queue.Queue[Any] = queue.Queue()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _fpclose(self) -> None:
        assert self._fileRefCnt > 0
        self._fileRefCnt -= 1
        if not self._fileRefCnt and not self._filePassed:
            self.fp.close()

    def _real_get_contents(self, password) -> None:
        if not self._check_7zfile(self.fp):
            raise Bad7zFile("not a 7z file")
        self.sig_header = SignatureHeader.retrieve(self.fp)
        self.afterheader: int = self.fp.tell()
        self.fp.seek(self.sig_header.nextheaderofs, os.SEEK_CUR)
        buffer = io.BytesIO(self.fp.read(self.sig_header.nextheadersize))
        if self.sig_header.nextheadercrc != calculate_crc32(buffer.getvalue()):
            raise Bad7zFile("invalid header data")
        header = Header.retrieve(self.fp, buffer, self.afterheader, password)
        if header is None:
            return
        header._initilized = True
        self.header = header
        header.size += 32 + self.sig_header.nextheadersize
        buffer.close()
        self.files = ArchiveFileList()
        if getattr(self.header, "files_info", None) is None:
            return
        # Initialize references for convenience
        if hasattr(self.header, "main_streams") and self.header.main_streams is not None:
            folders = self.header.main_streams.unpackinfo.folders
            for folder in folders:
                folder.password = password
            packinfo = self.header.main_streams.packinfo
            packsizes = packinfo.packsizes
            subinfo = self.header.main_streams.substreamsinfo
            if subinfo is not None and subinfo.unpacksizes is not None:
                unpacksizes = subinfo.unpacksizes
            else:
                unpacksizes = [x.unpacksizes[-1] for x in folders]
        else:
            subinfo = None
            folders = None
            packinfo = None
            packsizes = []
            unpacksizes = [0]

        pstat = self.ParseStatus()
        pstat.src_pos = self.afterheader
        file_in_solid = 0

        for file_id, file_info in enumerate(self.header.files_info.files):
            if not file_info["emptystream"] and folders is not None:
                folder = folders[pstat.folder]
                numinstreams = max([coder.get("numinstreams", 1) for coder in folder.coders])
                (maxsize, compressed, uncompressed, packsize, solid) = self._get_fileinfo_sizes(
                    pstat, subinfo, packinfo, folder, packsizes, unpacksizes, file_in_solid, numinstreams
                )
                pstat.input += 1
                folder.solid = solid
                file_info["folder"] = folder
                file_info["maxsize"] = maxsize
                file_info["compressed"] = compressed
                file_info["uncompressed"] = uncompressed
                file_info["packsizes"] = packsize
                if subinfo.digestsdefined[pstat.outstreams]:
                    file_info["digest"] = subinfo.digests[pstat.outstreams]
                if folder is None:
                    pstat.src_pos += file_info["compressed"]
                else:
                    if folder.solid:
                        file_in_solid += 1
                    pstat.outstreams += 1
                    if folder.files is None:
                        folder.files = ArchiveFileList(offset=file_id)
                    folder.files.append(file_info)
                    if pstat.input >= subinfo.num_unpackstreams_folders[pstat.folder]:
                        file_in_solid = 0
                        pstat.src_pos += sum(packinfo.packsizes[pstat.stream : pstat.stream + numinstreams])
                        pstat.folder += 1
                        pstat.stream += numinstreams
                        pstat.input = 0
            else:
                file_info["folder"] = None
                file_info["maxsize"] = 0
                file_info["compressed"] = 0
                file_info["uncompressed"] = 0
                file_info["packsizes"] = [0]

            if "filename" not in file_info:
                # compressed file is stored without a name, generate one
                try:
                    basefilename = self.filename
                except AttributeError:
                    # 7z archive file doesn't have a name
                    file_info["filename"] = "contents"
                else:
                    if basefilename is not None:
                        fn, ext = os.path.splitext(os.path.basename(basefilename))
                        file_info["filename"] = fn
                    else:
                        file_info["filename"] = "contents"
            self.files.append(file_info)
        if not self.password_protected and self.header.main_streams is not None:
            # Check specified coders have a crypt method or not.
            self.password_protected = any(
                [SupportedMethods.needs_password(folder.coders) for folder in self.header.main_streams.unpackinfo.folders]
            )

    def _extract(
        self,
        path: Optional[Any] = None,
        targets: Optional[Collection[str]] = None,
        return_dict: bool = False,
        callback: Optional[ExtractCallback] = None,
        recursive: Optional[bool] = False,
    ) -> Optional[Dict[str, IO[Any]]]:
        if callback is None:
            pass
        elif isinstance(callback, ExtractCallback):
            self.reporterd = Thread(target=self.reporter, args=(callback,), daemon=True)
            self.reporterd.start()
        else:
            raise ValueError("Callback specified is not an instance of subclass of py7zr.callbacks.ExtractCallback class")
        target_files: List[Tuple[pathlib.Path, Dict[str, Any]]] = []
        target_dirs: List[pathlib.Path] = []
        if path is not None:
            if isinstance(path, str):
                path = pathlib.Path(path)
            try:
                if not path.exists():
                    path.mkdir(parents=True)
                else:
                    pass
            except OSError as e:
                if e.errno == errno.EEXIST and path.is_dir():
                    pass
                else:
                    raise e
        if targets is not None:
            # faster lookups
            targets = set(targets)
        fnames: Dict[str, int] = {}  # check duplicated filename in one archive?
        self.q.put(("pre", None, None))
        for f in self.files:
            if targets is not None and recursive is False:
                if f.filename not in targets:
                    self.worker.register_filelike(f.id, None)
                    continue
            elif targets is not None and recursive is True:
                if f.filename not in targets and not any([f.filename.startswith(target) for target in targets]):
                    self.worker.register_filelike(f.id, None)
                    continue

            # When archive has a multiple files which have same name
            # To guarantee order of archive, multi-thread decompression becomes off.
            # Currently always overwrite by latter archives.
            # TODO: provide option to select overwrite or skip.
            if f.filename not in fnames:
                outname = f.filename
                fnames[f.filename] = 0
            else:
                outname = f.filename + "_%d" % fnames[f.filename]
                fnames[f.filename] += 1
            if path is None or path.is_absolute():
                outfilename = get_sanitized_output_path(outname, path)
            else:
                outfilename = get_sanitized_output_path(outname, pathlib.Path(os.getcwd()).joinpath(path))
            if return_dict:
                if f.is_directory or f.is_socket:
                    # ignore special files and directories
                    pass
                else:
                    fname = outfilename.as_posix()
                    _buf = io.BytesIO()
                    self._dict[fname] = _buf
                    self.worker.register_filelike(f.id, MemIO(_buf))
            elif f.is_directory:
                if not outfilename.exists():
                    target_dirs.append(outfilename)
                    target_files.append((outfilename, f.file_properties()))
                else:
                    pass
            elif f.is_socket:
                pass  # TODO: implement me.
            elif f.is_symlink or f.is_junction:
                self.worker.register_filelike(f.id, outfilename)
            else:
                self.worker.register_filelike(f.id, outfilename)
                target_files.append((outfilename, f.file_properties()))
        for target_dir in sorted(target_dirs):
            try:
                target_dir.mkdir(parents=True)
            except FileExistsError:
                if target_dir.is_dir():
                    pass
                elif target_dir.is_file():
                    raise DecompressionError("Directory {} is existed as a normal file.".format(str(target_dir)))
                else:
                    raise DecompressionError("Directory {} making fails on unknown condition.".format(str(target_dir)))

        if callback is not None:
            self.worker.extract(
                self.fp,
                path,
                parallel=(not self.password_protected and not self._filePassed),
                q=self.q,
            )
        else:
            self.worker.extract(
                self.fp,
                path,
                parallel=(not self.password_protected and not self._filePassed),
            )

        self.q.put(("post", None, None))
        # early return when dict specified
        if return_dict:
            return self._dict
        # set file properties
        for outfilename, properties in target_files:
            # mtime
            lastmodified = None
            try:
                lastmodified = ArchiveTimestamp(properties["lastwritetime"]).totimestamp()
            except KeyError:
                pass
            if lastmodified is not None:
                os.utime(str(outfilename), times=(lastmodified, lastmodified))
            if os.name == "posix":
                st_mode = properties["posix_mode"]
                if st_mode is not None:
                    outfilename.chmod(st_mode)
                    continue
            # fallback: only set readonly if specified
            if properties["readonly"] and not properties["is_directory"]:
                ro_mask = 0o777 ^ (stat.S_IWRITE | stat.S_IWGRP | stat.S_IWOTH)
                outfilename.chmod(outfilename.stat().st_mode & ro_mask)
        return None

    def _prepare_append(self, filters, password):
        if password is not None and filters is None:
            filters = DEFAULT_FILTERS.ENCRYPTED_ARCHIVE_FILTER
        elif filters is None:
            filters = DEFAULT_FILTERS.ARCHIVE_FILTER
        else:
            for f in filters:
                if f["id"] == FILTER_DEFLATE64:
                    raise UnsupportedCompressionMethodError(filters, "Compression with deflate64 is not supported.")
        self.header.filters = filters
        self.header.password = password
        if self.header.main_streams is not None:
            pos = self.afterheader + self.header.main_streams.packinfo.packpositions[-1]
        else:
            pos = self.afterheader
        self.fp.seek(pos)
        self.worker = Worker(self.files, pos, self.header, self.mp)

    def _prepare_write(self, filters, password):
        if password is not None and filters is None:
            filters = DEFAULT_FILTERS.ENCRYPTED_ARCHIVE_FILTER
        elif filters is None:
            filters = DEFAULT_FILTERS.ARCHIVE_FILTER
        self.files = ArchiveFileList()
        self.sig_header = SignatureHeader()
        self.sig_header._write_skelton(self.fp)
        self.afterheader = self.fp.tell()
        self.header = Header.build_header(filters, password)
        self.fp.seek(self.afterheader)
        self.worker = Worker(self.files, self.afterheader, self.header, self.mp)

    def _write_flush(self):
        if self.header is not None:
            if self.header._initialized:
                folder = self.header.main_streams.unpackinfo.folders[-1]
                self.worker.flush_archive(self.fp, folder)
            self._write_header()

    def _write_header(self):
        """Write header and update signature header."""
        (header_pos, header_len, header_crc) = self.header.write(
            self.fp,
            self.afterheader,
            encoded=self.encoded_header_mode,
            encrypted=self.header_encryption,
        )
        self.sig_header.nextheaderofs = header_pos - self.afterheader
        self.sig_header.calccrc(header_len, header_crc)
        self.sig_header.write(self.fp)

    def _writeall(self, path, arcname):
        try:
            if path.is_symlink() and not self.dereference:
                self.write(path, arcname)
            elif path.is_file():
                self.write(path, arcname)
            elif path.is_dir():
                if not path.samefile("."):
                    self.write(path, arcname)
                for nm in sorted(os.listdir(str(path))):
                    arc = os.path.join(arcname, nm) if arcname is not None else None
                    self._writeall(path.joinpath(nm), arc)
            else:
                return  # pathlib ignores ELOOP and return False for is_*().
        except OSError as ose:
            if self.dereference and ose.errno in [errno.ELOOP]:
                return  # ignore ELOOP here, this resulted to stop looped symlink reference.
            elif self.dereference and sys.platform == "win32" and ose.errno in [errno.ENOENT]:
                return  # ignore ENOENT which is happened when a case of ELOOP on windows.
            else:
                raise

    class ParseStatus:
        def __init__(self, src_pos=0):
            self.src_pos = src_pos
            self.folder = 0  # 7zip folder where target stored
            self.outstreams = 0  # output stream count
            self.input = 0  # unpack stream count in each folder
            self.stream = 0  # target input stream position

    def _get_fileinfo_sizes(
        self,
        pstat,
        subinfo,
        packinfo,
        folder,
        packsizes,
        unpacksizes,
        file_in_solid,
        numinstreams,
    ):
        if pstat.input == 0:
            folder.solid = subinfo.num_unpackstreams_folders[pstat.folder] > 1
        maxsize = (folder.solid and packinfo.packsizes[pstat.stream]) or None
        uncompressed = unpacksizes[pstat.outstreams]
        if file_in_solid > 0:
            compressed = None
        elif pstat.stream < len(packsizes):  # file is compressed
            compressed = packsizes[pstat.stream]
        else:  # file is not compressed
            compressed = uncompressed
        packsize = packsizes[pstat.stream : pstat.stream + numinstreams]
        return maxsize, compressed, uncompressed, packsize, folder.solid

    def set_encoded_header_mode(self, mode: bool) -> None:
        if mode:
            self.encoded_header_mode = True
        else:
            self.encoded_header_mode = False
            self.header_encryption = False

    def set_encrypted_header(self, mode: bool) -> None:
        if mode:
            self.encoded_header_mode = True
            self.header_encryption = True
        else:
            self.header_encryption = False

    @staticmethod
    def _check_7zfile(fp: Union[BinaryIO, io.BufferedReader, io.IOBase]) -> bool:
        try:
            result = MAGIC_7Z == fp.read(len(MAGIC_7Z))[: len(MAGIC_7Z)]
            fp.seek(-len(MAGIC_7Z), 1)
            return result
        except OSError:
            # A new empty file raises OSError
            return False

    def _get_method_names(self) -> List[str]:
        try:
            return get_methods_names([folder.coders for folder in self.header.main_streams.unpackinfo.folders])
        except KeyError:
            raise UnsupportedCompressionMethodError(self.header.main_streams.unpackinfo.folders, "Unknown method")

    def _read_digest(self, pos: int, size: int) -> int:
        self.fp.seek(pos)
        remaining_size = size
        digest = 0
        while remaining_size > 0:
            block = min(self._block_size, remaining_size)
            digest = calculate_crc32(self.fp.read(block), digest)
            remaining_size -= block
        return digest

    def _is_solid(self):
        for f in self.header.main_streams.substreamsinfo.num_unpackstreams_folders:
            if f > 1:
                return True
        return False

    def _var_release(self):
        self._dict = {}
        self.worker.close()
        del self.worker
        del self.files
        del self.header
        del self.sig_header

    @staticmethod
    def _make_file_info(target: pathlib.Path, arcname: Optional[str] = None, dereference=False) -> Dict[str, Any]:
        f: Dict[str, Any] = {}
        f["origin"] = target
        if arcname is not None:
            f["filename"] = pathlib.Path(arcname).as_posix()
        else:
            f["filename"] = target.as_posix()
        if sys.platform == "win32":
            fstat = target.lstat()
            if target.is_symlink():
                if dereference:
                    fstat = target.stat()
                    if stat.S_ISDIR(fstat.st_mode):
                        f["emptystream"] = True
                        f["attributes"] = fstat.st_file_attributes & FILE_ATTRIBUTE_WINDOWS_MASK  # noqa
                    else:
                        f["emptystream"] = False
                        f["attributes"] = stat.FILE_ATTRIBUTE_ARCHIVE  # noqa
                        f["uncompressed"] = fstat.st_size
                else:
                    f["emptystream"] = False
                    f["attributes"] = fstat.st_file_attributes & FILE_ATTRIBUTE_WINDOWS_MASK  # noqa
                    # TODO: handle junctions
                    # f['attributes'] |= stat.FILE_ATTRIBUTE_REPARSE_POINT  # noqa
            elif target.is_dir():
                f["emptystream"] = True
                f["attributes"] = fstat.st_file_attributes & FILE_ATTRIBUTE_WINDOWS_MASK  # noqa
            elif target.is_file():
                f["emptystream"] = False
                f["attributes"] = stat.FILE_ATTRIBUTE_ARCHIVE  # noqa
                f["uncompressed"] = fstat.st_size
        elif (
            sys.platform == "darwin"
            or sys.platform.startswith("linux")
            or sys.platform.startswith("freebsd")
            or sys.platform.startswith("netbsd")
            or sys.platform.startswith("sunos")
            or sys.platform == "aix"
        ):
            fstat = target.lstat()
            if target.is_symlink():
                if dereference:
                    fstat = target.stat()
                    if stat.S_ISDIR(fstat.st_mode):
                        f["emptystream"] = True
                        f["attributes"] = getattr(stat, "FILE_ATTRIBUTE_DIRECTORY")
                        f["attributes"] |= FILE_ATTRIBUTE_UNIX_EXTENSION | (stat.S_IFDIR << 16)
                        f["attributes"] |= stat.S_IMODE(fstat.st_mode) << 16
                    else:
                        f["emptystream"] = False
                        f["attributes"] = getattr(stat, "FILE_ATTRIBUTE_ARCHIVE")
                        f["attributes"] |= FILE_ATTRIBUTE_UNIX_EXTENSION | (stat.S_IMODE(fstat.st_mode) << 16)
                else:
                    f["emptystream"] = False
                    f["attributes"] = getattr(stat, "FILE_ATTRIBUTE_ARCHIVE") | getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT")
                    f["attributes"] |= FILE_ATTRIBUTE_UNIX_EXTENSION | (stat.S_IFLNK << 16)
                    f["attributes"] |= stat.S_IMODE(fstat.st_mode) << 16
            elif target.is_dir():
                f["emptystream"] = True
                f["attributes"] = getattr(stat, "FILE_ATTRIBUTE_DIRECTORY")
                f["attributes"] |= FILE_ATTRIBUTE_UNIX_EXTENSION | (stat.S_IFDIR << 16)
                f["attributes"] |= stat.S_IMODE(fstat.st_mode) << 16
            elif target.is_file():
                f["emptystream"] = False
                f["uncompressed"] = fstat.st_size
                f["attributes"] = getattr(stat, "FILE_ATTRIBUTE_ARCHIVE")
                f["attributes"] |= FILE_ATTRIBUTE_UNIX_EXTENSION | (stat.S_IMODE(fstat.st_mode) << 16)
        else:
            fstat = target.stat()
            if target.is_dir():
                f["emptystream"] = True
                f["attributes"] = stat.FILE_ATTRIBUTE_DIRECTORY
            elif target.is_file():
                f["emptystream"] = False
                f["uncompressed"] = fstat.st_size
                f["attributes"] = stat.FILE_ATTRIBUTE_ARCHIVE

        f["creationtime"] = ArchiveTimestamp.from_datetime(fstat.st_ctime)
        f["lastwritetime"] = ArchiveTimestamp.from_datetime(fstat.st_mtime)
        f["lastaccesstime"] = ArchiveTimestamp.from_datetime(fstat.st_atime)
        return f

    def _make_file_info_from_name(self, bio, size: int, arcname: str) -> Dict[str, Any]:
        f: Dict[str, Any] = {}
        f["origin"] = None
        f["data"] = bio
        f["filename"] = pathlib.Path(arcname).as_posix()
        f["uncompressed"] = size
        f["emptystream"] = False
        f["attributes"] = getattr(stat, "FILE_ATTRIBUTE_ARCHIVE")
        f["creationtime"] = ArchiveTimestamp.from_now()
        f["lastwritetime"] = ArchiveTimestamp.from_now()
        return f

    def _sanitize_archive_arcname(self, arcname):
        if isinstance(arcname, str):
            path = arcname
        else:
            path = str(arcname)
        # Strip leading / (tar's directory separator) from filenames.
        # Include os.sep (target OS directory separator) as well.
        if path.startswith(("/", os.sep)):
            path = path.lstrip("/" + os.sep)
        if re.match("^[a-zA-Z]:", path):
            path = path[2:]
            # strip again
            if path.startswith(("/", os.sep)):
                path = path.lstrip("/" + os.sep)
        if os.path.isabs(path) or re.match("^[a-zA-Z]:", path):
            # Path is absolute even after stripping.
            raise AbsolutePathError(arcname)
        return path

    def _is_none_or_collection(self, t):
        if t is None:
            return True
        if isinstance(t, str):
            return False
        if isinstance(t, tuple):
            return False
        if isinstance(t, list) or isinstance(t, set):
            return True
        return False

    # --------------------------------------------------------------------------
    # The public methods which SevenZipFile provides:
    def getnames(self) -> List[str]:
        """Return the members of the archive as a list of their names. It has
        the same order as the list returned by getmembers().
        """
        return self.namelist()

    def namelist(self) -> List[str]:
        """Return a list of archive members by name."""
        return list(map(lambda x: x.filename, self.files))

    def archiveinfo(self) -> ArchiveInfo:
        total_uncompressed = functools.reduce(lambda x, y: x + y, [f.uncompressed for f in self.files])
        if isinstance(self.fp, multivolumefile.MultiVolume):
            fname = self.fp.name
            fstat = self.fp.stat()
        else:
            fname = self.filename
            assert fname is not None
            fstat = os.stat(fname)
        return ArchiveInfo(
            fname,
            fstat,
            self.header.size,
            self._get_method_names(),
            self._is_solid(),
            len(self.header.main_streams.unpackinfo.folders),
            total_uncompressed,
        )

    def needs_password(self) -> bool:
        return self.password_protected

    def list(self) -> List[FileInfo]:
        """Returns contents information"""
        alist: List[FileInfo] = []
        lastmodified: Optional[datetime.datetime] = None
        for f in self.files:
            if f.lastwritetime is not None:
                lastmodified = filetime_to_dt(f.lastwritetime)
            alist.append(
                FileInfo(
                    f.filename,
                    f.compressed,
                    f.uncompressed,
                    f.archivable,
                    f.is_directory,
                    lastmodified,
                    f.crc32,
                )
            )
        return alist

    def readall(self) -> Optional[Dict[str, IO[Any]]]:
        self._dict = {}
        return self._extract(path=None, return_dict=True)

    def extractall(self, path: Optional[Any] = None, callback: Optional[ExtractCallback] = None) -> None:
        """Extract all members from the archive to the current working
        directory and set owner, modification time and permissions on
        directories afterwards. ``path`` specifies a different directory
        to extract to.
        """
        self._extract(path=path, return_dict=False, callback=callback)

    def read(self, targets: Optional[Collection[str]] = None) -> Optional[Dict[str, IO[Any]]]:
        if not self._is_none_or_collection(targets):
            raise TypeError("Wrong argument type given.")
        self._dict = {}
        return self._extract(path=None, targets=targets, return_dict=True)

    def extract(
        self, path: Optional[Any] = None, targets: Optional[Collection[str]] = None, recursive: Optional[bool] = False
    ) -> None:
        if not self._is_none_or_collection(targets):
            raise TypeError("Wrong argument type given.")
        self._extract(path, targets, return_dict=False, recursive=recursive)

    def reporter(self, callback: ExtractCallback):
        while True:
            try:
                item: Optional[Tuple[str, str, str]] = self.q.get(timeout=1)
            except queue.Empty:
                pass
            else:
                if item is None:
                    break
                elif item[0] == "s":
                    callback.report_start(item[1], item[2])
                elif item[0] == "u":
                    callback.report_update(item[2])
                elif item[0] == "e":
                    callback.report_end(item[1], item[2])
                elif item[0] == "pre":
                    callback.report_start_preparation()
                elif item[0] == "post":
                    callback.report_postprocess()
                elif item[0] == "w":
                    callback.report_warning(item[1])
                else:
                    pass
                self.q.task_done()

    def writeall(self, path: Union[pathlib.Path, str], arcname: Optional[str] = None):
        """Write files in target path into archive."""
        if isinstance(path, str):
            path = pathlib.Path(path)
        if not path.exists():
            raise ValueError("specified path does not exist.")
        if path.is_dir() or path.is_file():
            self._writeall(path, arcname)
        else:
            raise ValueError("specified path is not a directory or a file")

    def write(self, file: Union[pathlib.Path, str], arcname: Optional[str] = None):
        """Write single target file into archive."""
        if not isinstance(file, str) and not isinstance(file, pathlib.Path):
            raise ValueError("Unsupported file type.")
        if arcname is None:
            arcname = self._sanitize_archive_arcname(file)
        else:
            arcname = self._sanitize_archive_arcname(arcname)
        if isinstance(file, str):
            path = pathlib.Path(file)
        else:
            path = file
        folder = self.header.initialize()
        file_info = self._make_file_info(path, arcname, self.dereference)
        self.header.files_info.files.append(file_info)
        self.header.files_info.emptyfiles.append(file_info["emptystream"])
        self.files.append(file_info)
        self.worker.archive(self.fp, self.files, folder, deref=self.dereference)

    def writed(self, targets: Dict[str, IO[Any]]) -> None:
        for target, input in targets.items():
            self.writef(input, target)

    def writef(self, bio: IO[Any], arcname: str):
        if not check_archive_path(arcname):
            raise ValueError(f"Specified path is bad: {arcname}")
        return self._writef(bio, arcname)

    def _writef(self, bio: IO[Any], arcname: str):
        if isinstance(bio, io.BytesIO):
            size = bio.getbuffer().nbytes
        elif isinstance(bio, io.TextIOBase):
            # First check whether is it Text?
            raise ValueError("Unsupported file object type: please open file with Binary mode.")
        elif isinstance(bio, io.BufferedIOBase):
            # come here when subtype of io.BufferedIOBase that don't have __sizeof__ (eg. pypy)
            # alternative for `size = bio.__sizeof__()`
            current = bio.tell()
            bio.seek(0, os.SEEK_END)
            last = bio.tell()
            bio.seek(current, os.SEEK_SET)
            size = last - current
        else:
            raise ValueError("Wrong argument passed for argument bio.")
        if size >= 0:
            folder = self.header.initialize()
            file_info = self._make_file_info_from_name(bio, size, arcname)
            self.header.files_info.files.append(file_info)
            self.header.files_info.emptyfiles.append(file_info["emptystream"])
            self.files.append(file_info)
            self.worker.archive(self.fp, self.files, folder, deref=False)
        else:
            file_info = self._make_file_info_from_name(bio, size, arcname)
            self.header.files_info.files.append(file_info)
            self.header.files_info.emptyfiles.append(file_info["emptystream"])
            self.files.append(file_info)

    def writestr(self, data: Union[str, bytes, bytearray, memoryview], arcname: str):
        if not check_archive_path(arcname):
            raise ValueError(f"Specified path is bad: {arcname}")
        return self._writestr(data, arcname)

    def _writestr(self, data: Union[str, bytes, bytearray, memoryview], arcname: str):
        if not isinstance(arcname, str):
            raise ValueError("Unsupported arcname")
        if isinstance(data, str):
            self._writef(io.BytesIO(data.encode("UTF-8")), arcname)
        elif isinstance(data, bytes) or isinstance(data, bytearray) or isinstance(data, memoryview):
            self._writef(io.BytesIO(bytes(data)), arcname)
        else:
            raise ValueError("Unsupported data type.")

    def close(self):
        """Flush all the data into archive and close it.
        When close py7zr start reading target and writing actual archive file.
        """
        if "w" in self.mode:
            self._write_flush()
        if "a" in self.mode:
            self._write_flush()
        if "r" in self.mode:
            if self.reporterd is not None:
                self.q.put_nowait(None)
                self.reporterd.join(1)
                if self.reporterd.is_alive():
                    raise InternalError("Progress report thread terminate error.")
                self.reporterd = None
        self._fpclose()
        self._var_release()

    def reset(self) -> None:
        """
        When read mode, it reset file pointer, decompress worker and decompressor
        """
        if self.mode == "r":
            self.fp.seek(self.afterheader)
            self.worker = Worker(self.files, self.afterheader, self.header, self.mp)
            if self.header.main_streams is not None and self.header.main_streams.unpackinfo.numfolders > 0:
                for i, folder in enumerate(self.header.main_streams.unpackinfo.folders):
                    folder.decompressor = None

    def test(self) -> Optional[bool]:
        self.fp.seek(self.afterheader)
        self.worker = Worker(self.files, self.afterheader, self.header, self.mp)
        crcs: Optional[List[int]] = self.header.main_streams.packinfo.crcs
        if crcs is None or len(crcs) == 0:
            return None
        packpos = self.afterheader + self.header.main_streams.packinfo.packpos
        packsizes = self.header.main_streams.packinfo.packsizes
        digestdefined = self.header.main_streams.packinfo.digestdefined
        j = 0
        for i, d in enumerate(digestdefined):
            if d:
                if self._read_digest(packpos, packsizes[i]) != crcs[j]:
                    return False
                j += 1
            packpos += packsizes[i]
        return True

    def testzip(self) -> Optional[str]:
        self.fp.seek(self.afterheader)
        self.worker = Worker(self.files, self.afterheader, self.header, self.mp)
        for f in self.files:
            self.worker.register_filelike(f.id, None)
        try:
            self.worker.extract(
                self.fp, None, parallel=(not self.password_protected), skip_notarget=False
            )  # TODO: print progress
        except CrcError as crce:
            return crce.args[2]
        else:
            return None


# --------------------
# exported functions
# --------------------
def is_7zfile(file: Union[BinaryIO, str, pathlib.Path]) -> bool:
    """Quickly see if a file is a 7Z file by checking the magic number.
    The file argument may be a filename or file-like object too.
    """
    result = False
    try:
        if (isinstance(file, BinaryIO) or isinstance(file, io.BufferedReader) or isinstance(file, io.IOBase)) and hasattr(
            file, "read"
        ):
            result = SevenZipFile._check_7zfile(file)
        elif isinstance(file, str):
            with open(file, "rb") as fp:
                result = SevenZipFile._check_7zfile(fp)
        elif isinstance(file, pathlib.Path) or isinstance(file, pathlib.PosixPath) or isinstance(file, pathlib.WindowsPath):
            with file.open(mode="rb") as fp:  # noqa
                result = SevenZipFile._check_7zfile(fp)
        else:
            raise TypeError("invalid type: file should be str, pathlib.Path or BinaryIO, but {}".format(type(file)))
    except OSError:
        pass
    return result


def unpack_7zarchive(archive, path, extra=None):
    """
    Function for registering with shutil.register_unpack_format().
    """
    if not is_7zfile(archive):
        raise ReadError(f"{archive} is not a 7zip file.")
    with SevenZipFile(archive) as arc:
        arc.extractall(path)


def pack_7zarchive(base_name, base_dir, owner=None, group=None, dry_run=None, logger=None):
    """
    Function for registering with shutil.register_archive_format().
    """
    target_name = "{}.7z".format(base_name)
    with SevenZipFile(target_name, mode="w") as archive:
        archive.writeall(path=base_dir)
    return target_name


class Worker:
    """
    Extract worker class to invoke handler.
    """

    def __init__(self, files, src_start: int, header, mp=False) -> None:
        self.target_filepath: Dict[int, Union[MemIO, pathlib.Path, None]] = {}
        self.files = files
        self.src_start = src_start
        self.header = header
        self.current_file_index = len(self.files)
        self.last_file_index = len(self.files) - 1
        if mp:
            self.concurrent: Union[Type[Thread], Type[Process]] = Process
        else:
            self.concurrent = Thread

    def extract(self, fp: BinaryIO, path: Optional[pathlib.Path], parallel: bool, skip_notarget=True, q=None) -> None:
        """Extract worker method to handle 7zip folder and decompress each files."""
        if hasattr(self.header, "main_streams") and self.header.main_streams is not None:
            src_end = self.src_start + self.header.main_streams.packinfo.packpositions[-1]
            numfolders = self.header.main_streams.unpackinfo.numfolders
            if numfolders == 1:
                self.extract_single(
                    fp,
                    self.files,
                    path,
                    self.src_start,
                    src_end,
                    q,
                    skip_notarget=skip_notarget,
                )
            else:
                folders = self.header.main_streams.unpackinfo.folders
                positions = self.header.main_streams.packinfo.packpositions
                empty_files = [f for f in self.files if f.emptystream]
                if not parallel:
                    self.extract_single(fp, empty_files, path, 0, 0, q)
                    for i in range(numfolders):
                        if skip_notarget:
                            if not any([self.target_filepath.get(f.id, None) for f in folders[i].files]):
                                continue
                        self.extract_single(
                            fp,
                            folders[i].files,
                            path,
                            self.src_start + positions[i],
                            self.src_start + positions[i + 1],
                            q,
                            skip_notarget=skip_notarget,
                        )
                else:
                    if getattr(fp, "name", None) is None:
                        raise InternalError("Caught unknown variable status error")
                    filename: str = getattr(fp, "name", "")  # do not become "" but it is for type check.
                    self.extract_single(open(filename, "rb"), empty_files, path, 0, 0, q)
                    concurrent_tasks = []
                    exc_q: queue.Queue = queue.Queue()
                    for i in range(numfolders):
                        if skip_notarget:
                            if not any([self.target_filepath.get(f.id, None) for f in folders[i].files]):
                                continue
                        p = self.concurrent(
                            target=self.extract_single,
                            args=(
                                filename,
                                folders[i].files,
                                path,
                                self.src_start + positions[i],
                                self.src_start + positions[i + 1],
                                q,
                                exc_q,
                                skip_notarget,
                            ),
                        )
                        p.start()
                        concurrent_tasks.append(p)
                    for p in concurrent_tasks:
                        p.join()
                    if exc_q.empty():
                        pass
                    else:
                        exc_info = exc_q.get()
                        raise exc_info[1].with_traceback(exc_info[2])
        else:
            empty_files = [f for f in self.files if f.emptystream]
            self.extract_single(fp, empty_files, path, 0, 0, q)

    def extract_single(
        self,
        fp: Union[BinaryIO, str],
        files,
        path,
        src_start: int,
        src_end: int,
        q: Optional[queue.Queue],
        exc_q: Optional[queue.Queue] = None,
        skip_notarget=True,
    ) -> None:
        """
        Single thread extractor that takes file lists in single 7zip folder.
        """
        if files is None:
            return
        try:
            if isinstance(fp, str):
                fp = open(fp, "rb")
            fp.seek(src_start)
            self._extract_single(fp, files, path, src_end, q, skip_notarget)
        except Exception as e:
            if exc_q is None:
                raise e
            else:
                exc_tuple = sys.exc_info()
                exc_q.put(exc_tuple)

    def _extract_single(
        self,
        fp: BinaryIO,
        files,
        path,
        src_end: int,
        q: Optional[queue.Queue],
        skip_notarget=True,
    ) -> None:
        """
        Single thread extractor that takes file lists in single 7zip folder.
        this may raise exception.
        """
        just_check: List[ArchiveFile] = []
        for f in files:
            if q is not None:
                q.put(
                    (
                        "s",
                        str(f.filename),
                        str(f.compressed) if f.compressed is not None else "0",
                    )
                )
            fileish = self.target_filepath.get(f.id, None)
            if fileish is None:
                if not f.emptystream:
                    just_check.append(f)
            else:
                # delayed execution of crc check.
                self._check(fp, just_check, src_end)
                just_check = []
                fileish.parent.mkdir(parents=True, exist_ok=True)
                if not f.emptystream:
                    if f.is_junction and not isinstance(fileish, MemIO) and sys.platform == "win32":
                        with io.BytesIO() as ofp:
                            self.decompress(fp, f.folder, ofp, f.uncompressed, f.compressed, src_end, q)
                            dst: str = ofp.read().decode("utf-8")
                            if is_path_valid(fileish.parent.joinpath(dst), path):
                                # fileish.unlink(missing_ok=True) > py3.7
                                if fileish.exists():
                                    fileish.unlink()
                                if sys.platform == "win32":  # hint for mypy
                                    _winapi.CreateJunction(str(fileish), dst)  # noqa
                            else:
                                raise Bad7zFile("Junction point out of target directory.")
                    elif f.is_symlink and not isinstance(fileish, MemIO):
                        with io.BytesIO() as omfp:
                            self.decompress(fp, f.folder, omfp, f.uncompressed, f.compressed, src_end, q)
                            omfp.seek(0)
                            dst = omfp.read().decode("utf-8")
                            # check sym_target points inside an archive target?
                            if is_path_valid(fileish.parent.joinpath(dst), path):
                                sym_target = pathlib.Path(dst)
                                # fileish.unlink(missing_ok=True) > py3.7
                                if fileish.exists():
                                    fileish.unlink()
                                fileish.symlink_to(sym_target)
                            else:
                                raise Bad7zFile("Symlink point out of target directory.")
                    else:
                        with fileish.open(mode="wb") as obfp:
                            crc32 = self.decompress(fp, f.folder, obfp, f.uncompressed, f.compressed, src_end, q)
                            obfp.seek(0)
                            if f.crc32 is not None and crc32 != f.crc32:
                                raise CrcError(crc32, f.crc32, f.filename)
                else:
                    # just create empty file
                    if not isinstance(fileish, MemIO):
                        fileish.touch()
                    else:
                        with fileish.open() as ofp:
                            pass
            if q is not None:
                q.put(("e", str(f.filename), str(f.uncompressed)))
        if not skip_notarget:
            # delayed execution of crc check.
            self._check(fp, just_check, src_end)

    def _check(self, fp, check_target, src_end):
        """
        delayed execution of crc check.
        """
        for f in check_target:
            with NullIO() as ofp:
                crc32 = self.decompress(fp, f.folder, ofp, f.uncompressed, f.compressed, src_end)
            if f.crc32 is not None and crc32 != f.crc32:
                raise CrcError(crc32, f.crc32, f.filename)

    def decompress(
        self,
        fp: BinaryIO,
        folder,
        fq: IO[Any],
        size: int,
        compressed_size: Optional[int],
        src_end: int,
        q: Optional[queue.Queue] = None,
    ) -> int:
        """
        decompressor wrapper called from extract method.

        :parameter fp: archive source file pointer
        :parameter folder: Folder object that have decompressor object.
        :parameter fq: output file pathlib.Path
        :parameter size: uncompressed size of target file.
        :parameter compressed_size: compressed size of target file.
        :parameter src_end: end position of the folder
        :parameter q: the queue for the reporter

        :returns None

        """
        assert folder is not None
        out_remaining = size
        max_block_size = get_memory_limit()
        crc32 = 0
        decompressor = folder.get_decompressor(compressed_size)
        previous_update_at = time.time()
        decompressed_bytes = 0
        while out_remaining > 0:
            tmp = decompressor.decompress(fp, min(out_remaining, max_block_size))
            if len(tmp) > 0:
                out_remaining -= len(tmp)
                fq.write(tmp)
                crc32 = calculate_crc32(tmp, crc32)
            if q is not None:
                time_delta = time.time() - previous_update_at
                decompressed_bytes += len(tmp)
                if out_remaining <= 0 or time_delta >= 1:
                    q.put(("u", None, str(decompressed_bytes)))
                    previous_update_at += time_delta
                    decompressed_bytes = 0
            if out_remaining <= 0:
                break
        if fp.tell() >= src_end:
            if decompressor.crc is not None and not decompressor.check_crc():
                raise CrcError(decompressor.crc, decompressor.digest, None)
        return crc32

    def _find_link_target(self, target):
        """
        Find the target member of a symlink or hardlink member in the archive.
        """
        targetname: str = target.as_posix()
        linkname: Union[str, pathlib.Path] = readlink(targetname)
        # Check windows full path symlinks
        if str(linkname).startswith("\\\\?\\"):
            linkname = str(linkname)[4:]
        # normalize as posix style
        linkname = pathlib.Path(linkname).as_posix()
        member = None
        for j in range(len(self.files)):
            if linkname == self.files[j].origin.as_posix():
                # FIXME: when API user specify arcname, it will break
                member = os.path.relpath(linkname, os.path.dirname(targetname))
                break
        if member is None:
            member = linkname
        return member

    def _after_write(self, insize, foutsize, crc):
        self.header.main_streams.substreamsinfo.digestsdefined.append(True)
        self.header.main_streams.substreamsinfo.digests.append(crc)
        if self.header.main_streams.substreamsinfo.unpacksizes is None:
            self.header.main_streams.substreamsinfo.unpacksizes = [insize]
        else:
            self.header.main_streams.substreamsinfo.unpacksizes.append(insize)
        if self.header.main_streams.substreamsinfo.num_unpackstreams_folders is None:
            self.header.main_streams.substreamsinfo.num_unpackstreams_folders = [1]
        else:
            self.header.main_streams.substreamsinfo.num_unpackstreams_folders[-1] += 1
        return foutsize, crc

    def write(self, fp: BinaryIO, f, assym, folder):
        compressor = folder.get_compressor()
        if assym:
            link_target: str = self._find_link_target(f.origin)
            tgt: bytes = link_target.encode("utf-8")
            fd = io.BytesIO(tgt)
            insize, foutsize, crc = compressor.compress(fd, fp)
            fd.close()
        else:
            with f.origin.open(mode="rb") as fd:
                insize, foutsize, crc = compressor.compress(fd, fp)
        return self._after_write(insize, foutsize, crc)

    def writestr(self, fp: BinaryIO, f, folder):
        compressor = folder.get_compressor()
        insize, foutsize, crc = compressor.compress(f.data(), fp)
        return self._after_write(insize, foutsize, crc)

    def flush_archive(self, fp, folder):
        compressor = folder.get_compressor()
        foutsize = compressor.flush(fp)
        if len(self.files) > 0:
            if "maxsize" in self.header.files_info.files[self.last_file_index]:
                self.header.files_info.files[self.last_file_index]["maxsize"] += foutsize
            else:
                self.header.files_info.files[self.last_file_index]["maxsize"] = foutsize
        # Update size data in header
        self.header.main_streams.packinfo.numstreams += 1
        if self.header.main_streams.packinfo.enable_digests:
            self.header.main_streams.packinfo.crcs.append(compressor.digest)
            self.header.main_streams.packinfo.digestdefined.append(True)
        self.header.main_streams.packinfo.packsizes.append(compressor.packsize)
        folder.unpacksizes = compressor.unpacksizes

    def archive(self, fp: BinaryIO, files, folder, deref=False):
        """Run archive task for specified 7zip folder."""
        f = files[self.current_file_index]
        if f.has_strdata():
            foutsize, crc = self.writestr(fp, f, folder)
            self.header.files_info.files[self.current_file_index]["maxsize"] = foutsize
            self.header.files_info.files[self.current_file_index]["digest"] = crc
            self.last_file_index = self.current_file_index
        elif (f.is_symlink and not deref) or not f.emptystream:
            foutsize, crc = self.write(fp, f, (f.is_symlink and not deref), folder)
            self.header.files_info.files[self.current_file_index]["maxsize"] = foutsize
            self.header.files_info.files[self.current_file_index]["digest"] = crc
            self.last_file_index = self.current_file_index
        self.current_file_index += 1

    def register_filelike(self, id: int, fileish: Union[MemIO, pathlib.Path, None]) -> None:
        """register file-ish to worker."""
        self.target_filepath[id] = fileish

    def close(self):
        del self.header
        del self.files
        del self.concurrent
