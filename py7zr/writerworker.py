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

import io
from bringbuf.bringbuf import bRingBuf
from py7zr.properties import READ_BLOCKSIZE


class CallBack():

    def write(self, data):
        pass

    def flush(self):
        pass

    def close(self):
        pass


class BufferWriter(CallBack):

    def __init__(self, target):
        self.buf = target

    def write(self, data):
        self.buf.write(data)

    def flush(self):
        pass

    def close(self):
        self.buf.close()


class FileWriter(CallBack):

    def __init__(self, target):
        self.fp = io.BufferedWriter(target)

    def write(self, data):
        self.fp.write(data)

    def flush(self):
        self.fp.flush()

    def close(self):
        self.fp.close()


class Worker():

    def __init__(self, files, fp):
        self.handler = {}
        self.buf = bRingBuf(READ_BLOCKSIZE * 2)
        self.files = files
        self.fp = fp

    def register_reader(self, name, func):
        for f in self.files:
            if name == f.filename:
                self.handler[name] = func
                break

    def extract(self):
        for f in self.files:
            folder = f.folder
            handler = self.handler.get(f.filename, None)
            if folder is not None and handler is not None:
                while f.size > self.buf.len:
                    self.buf.enqueue(folder.decompressor.decompress(self.fp.read(READ_BLOCKSIZE)))
                handler.write(self.buf.dequeue(f.size))
                handler.flush()

    def close(self):
        for f in self.files:
            n = f.filename
            handler = self.handler.get(n, None)
            if handler is not None:
                handler.close()
