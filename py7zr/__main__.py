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
import py7zr # noqa


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='py7zr', description='py7zr',
                                     formatter_class=argparse.RawTextHelpFormatter, add_help=True)
    parser.add_argument('subcommand', choices=['l', 'x'], help="command l list, x extract")
    parser.add_argument('-o', nargs='?', help="output directory")
    parser.add_argument("file", help="7z archive file")

    args = parser.parse_args()
    com = args.subcommand
    target = args.file
    if not py7zr.is_7zfile(target):
        print('not a 7z file')
        exit(1)

    if com == 'l':
        with open(target, 'rb') as f:
            a = py7zr.SevenZipFile(f)
            a.list()
        exit(0)

    if com == 'x':
        with open(target, 'rb') as f:
            a = py7zr.SevenZipFile(f)
            if args.o:
                a.extractall(path=args.o)
            else:
                a.extractall()
        exit(0)
