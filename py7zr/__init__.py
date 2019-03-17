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

from .archive7z import Archive

__all__ = ['Archive']


def main():
    parser = argparse.ArgumentParser(prog='py7zr', description='py7zr',
                                     formatter_class=argparse.RawTextHelpFormatter, add_help=True)
    parser.add_argument('subcommand', choices=['l', 'x'], help="command l list, x extract")
    parser.add_argument('-o', nargs='?', help="output directory")
    parser.add_argument("file", help="7z archive file")

    args = parser.parse_args()
    com = args.subcommand
    target = args.file

    if com == 'l':
        f = Archive(open(target, 'rb'))
        f.list()
        exit(0)

    if com == 'x':
        f = Archive(open(target, 'rb'))
        if args.o:
            f.extract_all(dest=args.o)
        else:
            f.extract_all()
        exit(0)
