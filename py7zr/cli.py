#!/usr/bin/env python
#
#    Pure python p7zr implementation
#    Copyright (C) 2019-2021 Hiroshi Miura
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
import inspect
import io
import lzma
import os
import pathlib
import platform
import re
import shutil
import sys
from lzma import CHECK_CRC64, CHECK_SHA256, is_check_supported
from typing import Any, List, Optional

import _lzma  # type: ignore
import multivolumefile
import texttable  # type: ignore

import py7zr
from py7zr.callbacks import ExtractCallback
from py7zr.compressor import SupportedMethods
from py7zr.helpers import Local
from py7zr.properties import COMMAND_HELP_STRING


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
        self.ofd.write("- {}".format(processing_file_path))
        self.pwidth += len(processing_file_path) + 2

    def report_update(self, decompressed_bytes):
        pass

    def report_end(self, processing_file_path, wrote_bytes):
        self.total_bytes += int(wrote_bytes)
        plest = self.columns - self.pwidth
        progress = self.total_bytes / self.archive_total
        msg = "({:.0%})\n".format(progress)
        if plest - len(msg) > 0:
            self.ofd.write(msg.rjust(plest))
        else:
            self.ofd.write(msg)
        self.pwidth = 0

    def report_postprocess(self):
        pass

    def report_warning(self, message):
        pass


class Cli:
    dunits = {
        "b": 1,
        "B": 1,
        "k": 1024,
        "K": 1024,
        "m": 1024 * 1024,
        "M": 1024 * 1024,
        "g": 1024 * 1024 * 1024,
        "G": 1024 * 1024 * 1024,
    }

    def __init__(self):
        self.parser = self._create_parser()
        self.unit_pattern = re.compile(r"^([0-9]+)([bkmg]?)$", re.IGNORECASE)

    def run(self, arg: Optional[Any] = None) -> int:
        args = self.parser.parse_args(arg)
        if args.version:
            return self.show_version()
        return args.func(args)

    def _create_parser(self):
        parser = argparse.ArgumentParser(
            prog="py7zr",
            description="py7zr",
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=True,
        )
        subparsers = parser.add_subparsers(title="subcommands", help=COMMAND_HELP_STRING)
        list_parser = subparsers.add_parser("l")
        list_parser.set_defaults(func=self.run_list)
        list_parser.add_argument("arcfile", type=pathlib.Path, help="7z archive file")
        list_parser.add_argument("--verbose", action="store_true", help="verbose output")
        extract_parser = subparsers.add_parser("x")
        extract_parser.set_defaults(func=self.run_extract)
        extract_parser.add_argument("arcfile", type=pathlib.Path, help="7z archive file")
        extract_parser.add_argument("odir", nargs="?", help="output directory")
        extract_parser.add_argument(
            "-P",
            "--password",
            action="store_true",
            help="Password protected archive(you will be asked a password).",
        )
        extract_parser.add_argument("--verbose", action="store_true", help="verbose output")
        create_parser = subparsers.add_parser("c")
        create_parser.set_defaults(func=self.run_create)
        create_parser.add_argument("arcfile", help="7z archive file")
        create_parser.add_argument("filenames", nargs="+", help="filenames to archive")
        create_parser.add_argument("-v", "--volume", nargs=1, help="Create volumes.")
        create_parser.add_argument(
            "-P",
            "--password",
            action="store_true",
            help="Password protected archive(you will be asked a password).",
        )
        append_parser = subparsers.add_parser("a")
        append_parser.set_defaults(func=self.run_append)
        append_parser.add_argument("arcfile", help="7z archive file")
        append_parser.add_argument("filenames", nargs="+", help="filenames to archive")
        test_parser = subparsers.add_parser("t")
        test_parser.set_defaults(func=self.run_test)
        test_parser.add_argument("arcfile", help="7z archive file")
        info_parser = subparsers.add_parser("i")
        info_parser.set_defaults(func=self.run_info)
        parser.add_argument("--version", action="store_true", help="Show version")
        parser.set_defaults(func=self.show_help)
        return parser

    def show_version(self):
        print(self._get_version())

    @staticmethod
    def _get_version():
        s = inspect.stack()
        _module = inspect.getmodule(s[0][0])
        module_name = _module.__name__ if _module is not None else "unknown"
        py_version = platform.python_version()
        py_impl = platform.python_implementation()
        py_build = platform.python_compiler()
        return "{} Version {} : {} (Python {} [{} {}])".format(
            module_name,
            py7zr.__version__,
            py7zr.__copyright__,
            py_version,
            py_impl,
            py_build,
        )

    def show_help(self, args):
        self.show_version()
        self.parser.print_help()
        return 0

    def run_info(self, args):
        self.show_version()
        print("\nFormats:")
        table = texttable.Texttable()
        table.set_deco(texttable.Texttable.HEADER)
        table.set_cols_dtype(["t", "t"])
        table.set_cols_align(["l", "r"])
        for f in SupportedMethods.formats:
            m = "".join(" {:02x}".format(x) for x in f["magic"])
            table.add_row([str(f["name"]), m])
        print(table.draw())
        print("\nCodecs and hashes:")
        table = texttable.Texttable()
        table.set_deco(texttable.Texttable.HEADER)
        table.set_cols_dtype(["t", "t"])
        table.set_cols_align(["l", "r"])
        for c in SupportedMethods.methods:
            method_id: bytes = c["id"]
            m = "".join("{:02x}".format(x) for x in method_id)
            method_name: str = c["name"]
            table.add_row([m, method_name])
        table.add_row(["0", "CRC32"])
        if is_check_supported(CHECK_SHA256):
            table.add_row(["0", "SHA256"])
        if is_check_supported(CHECK_CRC64):
            table.add_row(["0", "CRC64"])
        print(table.draw())

    def run_list(self, args):
        """Print a table of contents to file."""
        target = args.arcfile
        verbose = args.verbose
        if re.fullmatch(r"[.]0+1?", target.suffix):
            mv_target = pathlib.Path(target.parent, target.stem)
            ext_start = int(target.suffix[-1])
            with multivolumefile.MultiVolume(
                mv_target, mode="rb", ext_digits=len(target.suffix) - 1, ext_start=ext_start
            ) as mvf:
                setattr(mvf, "name", str(mv_target))
                return self._run_list(mvf, verbose)
        else:
            return self._run_list(target, verbose)

    def _run_list(self, target, verbose):
        if not py7zr.is_7zfile(target):
            print("not a 7z file")
            return 1
        with py7zr.SevenZipFile(target, "r") as a:
            file = sys.stdout
            archive_info = a.archiveinfo()
            archive_list = a.list()
            if verbose:
                if isinstance(target, io.FileIO) or isinstance(target, multivolumefile.MultiVolume):
                    file_name: str = target.name  # type: ignore
                else:
                    file_name = str(target)
                file.write("Listing archive: {}\n".format(file_name))
                file.write("--\n")
                file.write("Path = {}\n".format(archive_info.filename))
                file.write("Type = 7z\n")
                fstat = archive_info.stat
                file.write("Phisical Size = {}\n".format(fstat.st_size))
                file.write("Headers Size = {}\n".format(archive_info.header_size))
                file.write("Method = {}\n".format(", ".join(archive_info.method_names)))
                if archive_info.solid:
                    file.write("Solid = {}\n".format("+"))
                else:
                    file.write("Solid = {}\n".format("-"))
                file.write("Blocks = {}\n".format(archive_info.blocks))
                file.write("\n")
            file.write(
                "total %d files and directories in %sarchive\n"
                % (len(archive_list), (archive_info.solid and "solid ") or "")
            )
            file.write("   Date      Time    Attr         Size   Compressed  Name\n")
            file.write("------------------- ----- ------------ ------------  ------------------------\n")
            for f in archive_list:
                if f.creationtime is not None:
                    lastwritedate = f.creationtime.astimezone(Local).strftime("%Y-%m-%d")
                    lastwritetime = f.creationtime.astimezone(Local).strftime("%H:%M:%S")
                else:
                    lastwritedate = "         "
                    lastwritetime = "         "
                if f.is_directory:
                    attrib = "D..."
                else:
                    attrib = "...."
                if f.archivable:
                    attrib += "A"
                else:
                    attrib += "."
                if f.is_directory:
                    extra = "           0 "
                elif f.compressed is None:
                    extra = "             "
                else:
                    extra = "%12d " % (f.compressed)
                file.write(
                    "%s %s %s %12d %s %s\n"
                    % (
                        lastwritedate,
                        lastwritetime,
                        attrib,
                        f.uncompressed,
                        extra,
                        f.filename,
                    )
                )
            file.write("------------------- ----- ------------ ------------  ------------------------\n")

        return 0

    @staticmethod
    def print_archiveinfo(archive, file):
        file.write("--\n")
        file.write("Path = {}\n".format(archive.filename))
        file.write("Type = 7z\n")
        fstat = os.stat(archive.filename)
        file.write("Phisical Size = {}\n".format(fstat.st_size))
        file.write("Headers Size = {}\n".format(archive.header.size))
        file.write("Method = {}\n".format(", ".join(archive._get_method_names())))
        if archive._is_solid():
            file.write("Solid = {}\n".format("+"))
        else:
            file.write("Solid = {}\n".format("-"))
        file.write("Blocks = {}\n".format(len(archive.header.main_streams.unpackinfo.folders)))

    def run_test(self, args):
        target = args.arcfile
        if not py7zr.is_7zfile(target):
            print("not a 7z file")
            return 1
        with open(target, "rb") as f:
            try:
                a = py7zr.SevenZipFile(f)
                file = sys.stdout
                file.write("Testing archive: {}\n".format(a.filename))
                self.print_archiveinfo(archive=a, file=file)
                file.write("\n")
                if a.testzip() is None:
                    file.write("Everything is Ok\n")
                    return 0
                else:
                    file.write("Bad 7zip file\n")
                    return 1
            except py7zr.exceptions.Bad7zFile:
                print("Header is corrupted. Cannot read as 7z file.")
                return 1
            except py7zr.exceptions.PasswordRequired:
                print("The archive is encrypted but password is not given. FAILED.")
                return 1

    def run_extract(self, args: argparse.Namespace) -> int:
        target = args.arcfile
        verbose = args.verbose
        if not py7zr.is_7zfile(target):
            print("not a 7z file")
            return 1
        if not args.password:
            password = None  # type: Optional[str]
        else:
            try:
                password = getpass.getpass()
            except getpass.GetPassWarning:
                sys.stderr.write("Warning: your password may be shown.\n")
                return 1
        try:
            a = py7zr.SevenZipFile(target, "r", password=password)
        except py7zr.exceptions.Bad7zFile:
            print("Header is corrupted. Cannot read as 7z file.")
            return 1
        except py7zr.exceptions.PasswordRequired:
            print("The archive is encrypted, but password is not given. ABORT.")
            return 1
        except lzma.LZMAError:
            if password is None:
                print("The archive is corrupted. ABORT.")
            else:
                print("The archive is corrupted, or password is wrong. ABORT.")
            return 1
        except _lzma.LZMAError:
            return 1

        cb = None  # Optional[ExtractCallback]
        if verbose:
            archive_info = a.archiveinfo()
            cb = CliExtractCallback(total_bytes=archive_info.uncompressed, ofd=sys.stderr)
        try:
            if args.odir:
                a.extractall(path=args.odir, callback=cb)
            else:
                a.extractall(callback=cb)
        except py7zr.exceptions.UnsupportedCompressionMethodError:
            print("Unsupported compression method is used in archive. ABORT.")
            return 1
        except py7zr.exceptions.DecompressionError:
            print("Error has been occurred during decompression. ABORT.")
            return 1
        except py7zr.exceptions.PasswordRequired:
            print("The archive is encrypted, but password is not given. ABORT.")
            return 1
        except lzma.LZMAError:
            if password is None:
                print("The archive is corrupted. ABORT.")
            else:
                print("The archive is corrupted, or password is wrong. ABORT.")
            return 1
        except _lzma.LZMAError:
            return 1
        else:
            return 0

    def _check_volumesize_valid(self, size: str) -> bool:
        if self.unit_pattern.match(size):
            return True
        else:
            return False

    def _volumesize_unitconv(self, size: str) -> int:
        m = self.unit_pattern.match(size)
        if m is not None:
            num = m.group(1)
            unit = m.group(2)
            return int(num) if unit is None else int(num) * self.dunits[unit]
        else:
            return -1

    def run_create(self, args):
        sztarget = args.arcfile  # type: str
        filenames = args.filenames  # type: List[str]
        volume_size = args.volume[0] if getattr(args, "volume", None) is not None else None
        if volume_size is not None and not self._check_volumesize_valid(volume_size):
            sys.stderr.write("Error: Specified volume size is invalid.\n")
            self.show_help(args)
            exit(1)
        if not sztarget.endswith(".7z"):
            sztarget += ".7z"
        target = pathlib.Path(sztarget)
        if target.exists():
            sys.stderr.write("Archive file exists!\n")
            self.show_help(args)
            exit(1)
        if not args.password:
            password = None  # type: Optional[str]
        else:
            try:
                password = getpass.getpass()
            except getpass.GetPassWarning:
                sys.stderr.write("Warning: your password may be shown.\n")
                return 1
        if volume_size is None:
            with py7zr.SevenZipFile(target, "w", password=password) as szf:
                for path in filenames:
                    src = pathlib.Path(path)
                    if src.is_dir():
                        szf.writeall(src)
                    else:
                        szf.write(src)
            return 0
        else:
            size = self._volumesize_unitconv(volume_size)
            with multivolumefile.MultiVolume(target, mode="wb", volume=size, ext_digits=4) as mvf:
                with py7zr.SevenZipFile(mvf, "w", password=password) as szf:
                    for path in filenames:
                        src = pathlib.Path(path)
                        if src.is_dir():
                            szf.writeall(src)
                        else:
                            szf.write(src)
            return 0

    def run_append(self, args):
        sztarget: str = args.arcfile
        filenames: List[str] = args.filenames
        if not sztarget.endswith(".7z"):
            sys.stderr.write("Error: specified archive file is invalid.")
            self.show_help(args)
            exit(1)
        target = pathlib.Path(sztarget)
        if not target.exists():
            sys.stderr.write("Archive file does not exists!\n")
            self.show_help(args)
            exit(1)
        with py7zr.SevenZipFile(target, "a") as szf:
            for path in filenames:
                src = pathlib.Path(path)
                if src.is_dir():
                    szf.writeall(src)
                else:
                    szf.write(src)
        return 0
