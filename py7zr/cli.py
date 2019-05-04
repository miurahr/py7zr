#!/usr/bin/env python
#
#    Pure python p7zr implementation
#    Copyright (C) 2019 Hiroshi Miura
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
import os
import py7zr


class Cli():
    def __init__(self):
        parser = argparse.ArgumentParser(prog='py7zr', description='py7zr',
                                         formatter_class=argparse.RawTextHelpFormatter, add_help=True)
        subparsers = parser.add_subparsers(title='subcommands', help='subcommand for py7zr')
        list_parser = subparsers.add_parser('l')
        list_parser.set_defaults(func=self.run_list)
        list_parser.add_argument("arcfile", help="7z archive file")
        extract_parser = subparsers.add_parser('x')
        extract_parser.set_defaults(func=self.run_extract)
        extract_parser.add_argument("arcfile", help="7z archive file")
        extract_parser.add_argument("odir", nargs="?", help="output directory")
        create_parser = subparsers.add_parser('c')
        create_parser.set_defaults(func=self.run_create)
        create_parser.add_argument("arcfile", help="7z archive file")
        create_parser.add_argument("filenames", nargs="*", help="filenames to archive")
        parser.set_defaults(func=self.show_help)
        self.parser = parser

    def show_help(self, args):
        self.parser.print_help()

    def run(self, arg=None):
        args = self.parser.parse_args(arg)
        args.func(args)

    def run_list(self, args):
        target = args.arcfile
        if not py7zr.is_7zfile(target):
            print('not a 7z file')
            return(1)

        with open(target, 'rb') as f:
            a = py7zr.SevenZipFile(f)
            a.list()
        return(0)

    def run_extract(self, args):
        target = args.arcfile
        if not py7zr.is_7zfile(target):
            print('not a 7z file')
            return(1)

        with open(target, 'rb') as f:
            a = py7zr.SevenZipFile(f)
            if args.odir:
                a.extractall(path=args.odir)
            else:
                a.extractall()
        return(0)

    def run_create(self, args):
        sztarget = args.arcfile

        def _add_to_sevenzip(szf, path, szpath):
            if os.path.isfile(path):
                szf.write(path, szpath)
            elif os.path.isdir(path):
                if szpath:
                    szf.write(path, szpath)
                for nm in sorted(os.listdir(path)):
                    _add_to_sevenzip(szf, os.path.join(path, nm), os.path.join(szpath, nm))
        with py7zr.SevenZipFile(sztarget, 'w') as szf:
            for path in args.filenames:
                zippath = os.path.basename(path)
                if not zippath:
                    zippath = os.path.basename(os.path.dirname(path))
                if zippath in ('', os.curdir, os.pardir):
                    zippath = ''
                _add_to_sevenzip(szf, path, zippath)


def main():
    cli = Cli()
    return cli.run()
