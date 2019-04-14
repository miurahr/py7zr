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
import sys
import threading
from io import BytesIO

from py7zr.decompressors import BufferWriter, FileWriter, Worker, decode_file_info, ArchiveFile
from py7zr.archiveinfo import Header, SignatureHeader
from py7zr.exceptions import Bad7zFile, DecompressionError
from py7zr.properties import MAGIC_7Z
from py7zr.helpers import filetime_to_dt, Local, checkcrc


# ------------------
# Exported Classes
# ------------------
class SevenZipFile():
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
        self.files, self.solid = decode_file_info(header, self.afterheader)

    def _read_header_data(self):
        self.fp.seek(self.sig_header.nextheaderofs, 1)
        buffer = BytesIO(self.fp.read(self.sig_header.nextheadersize))
        headerrawdata = buffer.getvalue()
        if not checkcrc(self.sig_header.nextheadercrc, headerrawdata):
            raise Bad7zFile('invalid header data')
        return buffer

    @classmethod
    def _check_7zfile(cls, fp):
        signature = fp.read(len(MAGIC_7Z))[:len(MAGIC_7Z)]
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
        return self.files[name]

    def reset(self):
        self.fp.seek(self.afterheader)
        self.worker = Worker(self.files, self.fp, self.afterheader)

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
        file.write('total %d files and directories in %sarchive\n' % (len(self.files), (self.solid and 'solid ') or ''))
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
