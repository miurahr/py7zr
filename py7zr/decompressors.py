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
#

import io
import lzma
import bz2
import stat
import zlib
from functools import reduce

from py7zr import FileAttribute
from py7zr.exceptions import UnsupportedCompressionMethodError, DecompressionError
from py7zr.properties import CompressionMethod

FILTER_COPY = 1
FILTER_BZIP2 = 2
FILTER_ZIP = 3

lzma_methods_map = {
    CompressionMethod.LZMA: lzma.FILTER_LZMA1,
    CompressionMethod.LZMA2: lzma.FILTER_LZMA2,
    CompressionMethod.DELTA: lzma.FILTER_DELTA,
    CompressionMethod.BCJ: lzma.FILTER_X86,
    CompressionMethod.BCJ_ARM: lzma.FILTER_ARM,
    CompressionMethod.BCJ_ARMT: lzma.FILTER_ARMTHUMB,
    CompressionMethod.BCJ_IA64: lzma.FILTER_IA64,
    CompressionMethod.BCJ_PPC: lzma.FILTER_POWERPC,
    CompressionMethod.BCJ_SPARC: lzma.FILTER_SPARC,
}
alt_methods_map = {
    CompressionMethod.COPY: FILTER_COPY,
    CompressionMethod.MISC_BZIP2: FILTER_BZIP2,
    CompressionMethod.MISC_ZIP: FILTER_ZIP,
}


def get_decompressor(coders, unpacksize=None):
    decompressor = None
    filters = []
    try:
        for coder in coders:
            filter = lzma_methods_map.get(coder['method'], None)
            if filter is not None:
                properties = coder.get('properties', None)
                if properties is not None:
                    filters.append(lzma._decode_filter_properties(filter, properties))
                else:
                    filters.append({'id': filter})
            else:
                raise UnsupportedCompressionMethodError
    except UnsupportedCompressionMethodError as e:
        filter = alt_methods_map.get(coders[0]['method'], None)
        if len(coders) == 1 and filter is not None:
            if filter == FILTER_BZIP2:
                decompressor = bz2.BZ2Decompressor()
            elif filter == FILTER_ZIP:
                decompressor = zlib.decompressobj(-15)
            elif filter == FILTER_COPY:
                decompressor = DecompressorCopy(unpacksize)
            can_partial_decompress = False
        else:
            raise e
    else:
        decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
        can_partial_decompress = True
    return decompressor, can_partial_decompress


class DecompressorCopy():

    def __init__(self, total):
        self.remaining = total

    def decompress(self, data, max_length=None):
        self.remaining -= len(data)
        return data

    @property
    def needs_input(self):
        return self.remaining > 0

    @property
    def eof(self):
        return self.remaining <= 0


class BufferWriter():

    def __init__(self, target):
        self.buf = target

    def write(self, data):
        self.buf.write(data)

    def flush(self):
        pass

    def close(self):
        self.buf.close()


class FileWriter():

    def __init__(self, target):
        self.fp = io.BufferedWriter(target)

    def write(self, data):
        self.fp.write(data)

    def flush(self):
        self.fp.flush()

    def close(self):
        self.fp.close()


class Worker():

    def __init__(self, files, fp, src_start):
        self.handler = {}
        self.files = files
        self.fp = fp
        self.src_start = src_start

    def register_reader(self, name, func):
        for f in self.files:
            if name == f.filename:
                self.handler[name] = func
                break

    def extract(self, fp):
        fp.seek(self.src_start)
        for f in self.files:
            handler = self.handler.get(f.filename, None)
            if handler is not None:
                f.decompress(fp, handler)
            else:
                f.decompress(fp, io.BytesIO())

    def close(self):
        for f in self.files:
            n = f.filename
            handler = self.handler.get(n, None)
            if handler is not None:
                handler.close()

    def decompress(self, fp, data):
        if self.folder is None:
            return b''
        decompressor = self.folder.decompressor
        queue = self.folder.queue
        if queue.len > 0:
            if self.out_remaining > queue.len:
                self.out_remaining -= queue.len
                data.write(queue.dequeue(queue.len))
            else:
                data.write(queue.dequeue(self.out_remaining))
                self.out_remaining = 0
                return

        while self.out_remaining > 0:
            if decompressor.needs_input:
                inp = fp.read(READ_BLOCKSIZE)
            else:
                inp = b''
            if not decompressor.eof:
                tmp = decompressor.decompress(inp, self.out_remaining)
                if self.out_remaining > len(tmp):
                    data.write(tmp)
                    self.out_remaining -= len(tmp)
                else:
                    queue.enqueue(tmp)
                    data.write(queue.dequeue(self.out_remaining))
                    break
            else:
                raise DecompressionError("Corrupted data")
        return


def decode_file_info(header, src_pos):
    files_list = []
    unpacksizes = [0]
    if hasattr(header, 'main_streams'):
        folders = header.main_streams.unpackinfo.folders
        packinfo = header.main_streams.packinfo
        subinfo = header.main_streams.substreamsinfo
        packsizes = packinfo.packsizes
        solid = packinfo.numstreams == 1
        if hasattr(subinfo, 'unpacksizes'):
            unpacksizes = subinfo.unpacksizes
        else:
            unpacksizes = [x.unpacksizes for x in folders]
    else:
        subinfo = None
        folders = None
        packinfo = None
        packsizes = []
        solid = False

    folder_index = 0
    output_binary_index = 0
    streamidx = 0
    pos = 0
    instreamindex = 0
    folder_pos = src_pos

    if getattr(header, 'files_info', None) is None:
        return files_list

    for file_info in header.files_info.files:
        if not file_info['emptystream'] or folders is None:
            folder = folders[folder_index]
            if streamidx == 0:
                folder.solid = subinfo.num_unpackstreams_folders[folder_index] > 1

            maxsize = (folder.solid and packinfo.packsizes[instreamindex]) or None
            uncompressed = unpacksizes[output_binary_index]
            if not isinstance(uncompressed, (list, tuple)):
                uncompressed = [uncompressed] * len(folder.coders)
            if pos > 0:
                # file is part of solid archive
                assert instreamindex < len(packsizes), 'Folder outside index for solid archive'
                file_info['compressed'] = packsizes[instreamindex]
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
            maxsize = 0
            numinstreams = 1

        file_info['folder'] = folder
        file_info['offset'] = pos

        archive_file = ArchiveFile(file_info, folder, maxsize)
        if folder is not None and subinfo.digestsdefined[output_binary_index]:
            archive_file.digest = subinfo.digests[output_binary_index]
        files_list.append(archive_file)

        if folder is not None:
            if folder.solid:
                pos += unpacksizes[output_binary_index]
            output_binary_index += 1
        else:
            src_pos += file_info['compressed']
        if folder is not None and streamidx >= subinfo.num_unpackstreams_folders[folder_index]:
            pos = 0
            for x in range(numinstreams):
                folder_pos += packinfo.packsizes[instreamindex + x]
            src_pos = folder_pos
            folder_index += 1
            instreamindex += numinstreams
            streamidx = 0

    return files_list, solid


class ArchiveFile():
    """Informational class which holds the details about an
       archive member.
       ArchiveFile objects are returned by SevenZipFile.getmember(),
       SevenZipFile.getmembers() and are usually created internally.
    """

    __slots__ = ['digest', 'attributes', 'folder', 'size', 'uncompressed',
                 'filename', 'maxsize', 'out_remaining', 'offset', 'emptystream',
                 'lastwritetime', 'creationtime', 'lastaccesstime', 'compressed', 'packsizes']

    def __init__(self, info, folder, maxsize):
        self.digest = None
        self.attributes = None
        self.folder = folder
        self.maxsize = maxsize
        for k, v in info.items():
            setattr(self, k, v)
        if hasattr(self, 'uncompressed'):
            self.size = reduce(self._plus, self.uncompressed)
        else:
            self.size = 0

    def _plus(self, a, b):
        return a + b

    def _test_attribute(self, target_bit):
        if not self.attributes:
            return False
        return self.attributes & target_bit == target_bit

    def is_archivable(self):
        return self._test_attribute(FileAttribute.ARCHIVE)

    def is_directory(self):
        return self._test_attribute(FileAttribute.DIRECTORY)

    def is_readonly(self):
        return self._test_attribute(FileAttribute.READONLY)

    def is_executable(self):
        """
        :return: True if unix mode is read+exec, otherwise False
        """
        if self._test_attribute(FileAttribute.UNIX_EXTENSION):
            st_mode = self.attributes >> 16
            if (st_mode & 0b0101 == 0b0101):
                return True
        return False

    def is_symlink(self):
        if self._test_attribute(FileAttribute.UNIX_EXTENSION):
            st_mode = self.attributes >> 16
            return stat.S_ISLNK(st_mode)
        return False

    def get_posix_mode(self):
        """
        :return: Return file stat mode can be set by os.chmod()
        """
        if self._test_attribute(FileAttribute.UNIX_EXTENSION):
            st_mode = self.attributes >> 16
            return stat.S_IMODE(st_mode)
        return None

    def get_st_fmt(self):
        """
        :return: Return the portion of the file mode that describes the file type
        """
        if self._test_attribute(FileAttribute.UNIX_EXTENSION):
            st_mode = self.attributes >> 16
            return stat.S_IFMT(st_mode)
        return None