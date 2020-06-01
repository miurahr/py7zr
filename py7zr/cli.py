#!/usr/bin/env python
#
#    Pure python p7zr implementation
#    Copyright (C) 2019, 2020 Hiroshi Miura
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import argparse
import getpass
import os
import pathlib
import re
import shutil
import sys
from lzma import CHECK_CRC64, CHECK_SHA256, is_check_supported
from typing import Any, List, Optional

import texttable  # type: ignore

import py7zr
from py7zr.callbacks import ExtractCallback
from py7zr.helpers import Local
from py7zr.properties import READ_BLOCKSIZE, SupportedMethods


class CliExtractCallback(ExtractCallback):

    def __init__(self, total_bytes, ofd=sys.stdout):
        self.ofd = ofd
        self.archive_total = total_bytes
        self.total_bytes = 0
        self.columns, _ = shutil.get_terminal_size(fallback=(80, 24))
        self.pwidth = 0

    def report_start_preparation(self):
        pass

    def report_start(self, processing_file_path, processing_bytes):
        self.ofd.write('- {}'.format(processing_file_path))
        self.pwidth += len(processing_file_path) + 2

    def report_end(self, processing_file_path, wrote_bytes):
        self.total_bytes += int(wrote_bytes)
        plest = self.columns - self.pwidth
        progress = self.total_bytes / self.archive_total
        msg = '({:.0%})\n'.format(progress)
        if plest - len(msg) > 0:
            self.ofd.write(msg.rjust(plest))
        else:
            self.ofd.write(msg)
        self.pwidth = 0

    def report_postprocess(self):
        pass

    def report_warning(self, message):
        pass


class Cli():

    dunits = {'b': 1, 'B': 1, 'k': 1024, 'K': 1024, 'm': 1024 * 1024, 'M': 1024 * 1024,
              'g': 1024 * 1024 * 1024, 'G': 1024 * 1024 * 1024}

    def __init__(self):
        self.parser = self._create_parser()
        self.unit_pattern = re.compile(r'^([0-9]+)([bkmg]?)$', re.IGNORECASE)

    def run(self, arg: Optional[Any] = None) -> int:
        args = self.parser.parse_args(arg)
        return args.func(args)

    def _create_parser(self):
        parser = argparse.ArgumentParser(prog='py7zr', description='py7zr',
                                         formatter_class=argparse.RawTextHelpFormatter, add_help=True)
        subparsers = parser.add_subparsers(title='subcommands', help='subcommand for py7zr l .. list, x .. extract,'
                                                                     ' t .. check integrity, i .. information')
        list_parser = subparsers.add_parser('l')
        list_parser.set_defaults(func=self.run_list)
        list_parser.add_argument("arcfile", help="7z archive file")
        list_parser.add_argument("--verbose", action="store_true", help="verbose output")
        extract_parser = subparsers.add_parser('x')
        extract_parser.set_defaults(func=self.run_extract)
        extract_parser.add_argument("arcfile", help="7z archive file")
        extract_parser.add_argument("odir", nargs="?", help="output directory")
        extract_parser.add_argument("-P", "--password", action="store_true",
                                    help="Password protected archive(you will be asked a password).")
        extract_parser.add_argument("--verbose", action="store_true", help="verbose output")
        create_parser = subparsers.add_parser('c')
        create_parser.set_defaults(func=self.run_create)
        create_parser.add_argument("arcfile", help="7z archive file")
        create_parser.add_argument("filenames", nargs="+", help="filenames to archive")
        create_parser.add_argument("-v", "--volume", nargs=1, help="Create volumes.")
        test_parser = subparsers.add_parser('t')
        test_parser.set_defaults(func=self.run_test)
        test_parser.add_argument("arcfile", help="7z archive file")
        info_parser = subparsers.add_parser("i")
        info_parser.set_defaults(func=self.run_info)
        parser.set_defaults(func=self.show_help)
        return parser

    def show_help(self, args):
        self.parser.print_help()
        return(0)

    def run_info(self, args):
        print("py7zr version {} {}".format(py7zr.__version__, py7zr.__copyright__))
        print("Formats:")
        table = texttable.Texttable()
        table.set_deco(texttable.Texttable.HEADER)
        table.set_cols_dtype(['t', 't'])
        table.set_cols_align(["l", "r"])
        for f in SupportedMethods.formats:
            m = ''.join(' {:02x}'.format(x) for x in f['magic'])
            table.add_row([f['name'], m])
        print(table.draw())
        print("\nCodecs:")
        table = texttable.Texttable()
        table.set_deco(texttable.Texttable.HEADER)
        table.set_cols_dtype(['t', 't'])
        table.set_cols_align(["l", "r"])
        for c in SupportedMethods.codecs:
            m = ''.join('{:02x}'.format(x) for x in c['id'])
            table.add_row([m, c['name']])
        print(table.draw())
        print("\nChecks:")
        print("CHECK_NONE")
        print("CHECK_CRC32")
        if is_check_supported(CHECK_CRC64):
            print("CHECK_CRC64")
        if is_check_supported(CHECK_SHA256):
            print("CHECK_SHA256")

    def run_list(self, args):
        """Print a table of contents to file. """
        target = args.arcfile
        verbose = args.verbose
        if not py7zr.is_7zfile(target):
            print('not a 7z file')
            return(1)
        with open(target, 'rb') as f:
            a = py7zr.SevenZipFile(f)
            file = sys.stdout
            archive_info = a.archiveinfo()
            archive_list = a.list()
            if verbose:
                file.write("Listing archive: {}\n".format(target))
                file.write("--\n")
                file.write("Path = {}\n".format(archive_info.filename))
                file.write("Type = 7z\n")
                fstat = os.stat(archive_info.filename)
                file.write("Phisical Size = {}\n".format(fstat.st_size))
                file.write("Headers Size = {}\n".format(archive_info.header_size))
                file.write("Method = {}\n".format(archive_info.method_names))
                if archive_info.solid:
                    file.write("Solid = {}\n".format('+'))
                else:
                    file.write("Solid = {}\n".format('-'))
                file.write("Blocks = {}\n".format(archive_info.blocks))
                file.write('\n')
            file.write(
                'total %d files and directories in %sarchive\n' % (len(archive_list),
                                                                   (archive_info.solid and 'solid ') or ''))
            file.write('   Date      Time    Attr         Size   Compressed  Name\n')
            file.write('------------------- ----- ------------ ------------  ------------------------\n')
            for f in archive_list:
                if f.creationtime is not None:
                    creationdate = f.creationtime.astimezone(Local).strftime("%Y-%m-%d")
                    creationtime = f.creationtime.astimezone(Local).strftime("%H:%M:%S")
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
                                                      f.uncompressed, extra, f.filename))
            file.write('------------------- ----- ------------ ------------  ------------------------\n')

        return(0)

    @staticmethod
    def print_archiveinfo(archive, file):
        file.write("--\n")
        file.write("Path = {}\n".format(archive.filename))
        file.write("Type = 7z\n")
        fstat = os.stat(archive.filename)
        file.write("Phisical Size = {}\n".format(fstat.st_size))
        file.write("Headers Size = {}\n".format(archive.header.size))  # fixme.
        file.write("Method = {}\n".format(archive._get_method_names()))
        if archive._is_solid():
            file.write("Solid = {}\n".format('+'))
        else:
            file.write("Solid = {}\n".format('-'))
        file.write("Blocks = {}\n".format(len(archive.header.main_streams.unpackinfo.folders)))

    def run_test(self, args):
        target = args.arcfile
        if not py7zr.is_7zfile(target):
            print('not a 7z file')
            return(1)
        with open(target, 'rb') as f:
            a = py7zr.SevenZipFile(f)
            file = sys.stdout
            file.write("Testing archive: {}\n".format(a.filename))
            self.print_archiveinfo(archive=a, file=file)
            file.write('\n')
            if a.test():
                file.write('Everything is Ok\n')
                return(0)
            else:
                file.write('Bad 7zip file\n')
                return(1)

    def run_extract(self, args: argparse.Namespace) -> int:
        target = args.arcfile
        verbose = args.verbose
        if not py7zr.is_7zfile(target):
            print('not a 7z file')
            return(1)
        if not args.password:
            password = None  # type: Optional[str]
        else:
            try:
                password = getpass.getpass()
            except getpass.GetPassWarning:
                sys.stderr.write('Warning: your password may be shown.\n')
                return(1)
        a = py7zr.SevenZipFile(target, 'r', password=password)
        cb = None  # Optional[ExtractCallback]
        if verbose:
            archive_info = a.archiveinfo()
            cb = CliExtractCallback(total_bytes=archive_info.uncompressed, ofd=sys.stderr)
        if args.odir:
            a.extractall(path=args.odir, callback=cb)
        else:
            a.extractall(callback=cb)
        return(0)

    def _check_volumesize_valid(self, size: str) -> bool:
        if self.unit_pattern.match(size):
            return True
        else:
            return False

    def _volumesize_unitconv(self, size: str) -> int:
        m = self.unit_pattern.match(size)
        num = m.group(1)
        unit = m.group(2)
        return int(num) if unit is None else int(num) * self.dunits[unit]

    def run_create(self, args):
        sztarget = args.arcfile  # type: str
        filenames = args.filenames  # type: List[str]
        volume_size = args.volume[0] if getattr(args, 'volume', None) is not None else None
        if volume_size is not None and not self._check_volumesize_valid(volume_size):
            sys.stderr.write('Error: Specified volume size is invalid.\n')
            self.show_help(args)
            exit(1)
        if not sztarget.endswith('.7z'):
            sztarget += '.7z'
        target = pathlib.Path(sztarget)
        if target.exists():
            sys.stderr.write('Archive file exists!\n')
            self.show_help(args)
            exit(1)
        with py7zr.SevenZipFile(target, 'w') as szf:
            for path in filenames:
                src = pathlib.Path(path)
                if src.is_dir():
                    szf.writeall(src)
                else:
                    szf.write(src)
        if volume_size is None:
            return (0)
        size = self._volumesize_unitconv(volume_size)
        self._split_file(target, size)
        target.unlink()
        return(0)

    def _split_file(self, filepath, size):
        chapters = 0
        written = [0, 0]
        total_size = filepath.stat().st_size
        with filepath.open('rb') as src:
            while written[0] <= total_size:
                with open(str(filepath) + '.%03d' % chapters, 'wb') as tgt:
                    written[1] = 0
                    while written[1] < size:
                        read_size = min(READ_BLOCKSIZE, size - written[1])
                        tgt.write(src.read(read_size))
                        written[1] += read_size
                        written[0] += read_size
                chapters += 1
