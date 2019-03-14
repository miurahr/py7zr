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

from .py7zrlib import Archive7z

__all__ = ['Archive7z']


def main():
    parser = argparse.ArgumentParser(prog='py7zr', description='py7zr',
                                     formatter_class=argparse.RawTextHelpFormatter, add_help=True)
    parser.add_argument('subcommand', choices=['l', 'x'], help="command l list, x extract")
    parser.add_argument("file", help="7z archive file")

    args = parser.parse_args()
    com = args.subcommand
    target = args.file

    if com == 'l':
        f = Archive7z(open(target, 'rb'))
        f.list()
        exit(0)

    if com == 'x':
        f = Archive7z(open(target, 'rb'))
        for name in f.getnames():
            outfilename = name
            outdir = os.path.dirname(outfilename)
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            outfile = open(outfilename, 'wb')
            outfile.write(f.getmember(name).read())
            outfile.close()
        exit(0)
