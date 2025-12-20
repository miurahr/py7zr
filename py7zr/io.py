#!/usr/bin/env python
#
#    Pure python p7zr implementation
#    Copyright (C) 2019-2024 Hiroshi Miura
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
import hashlib
import io
from abc import ABC, abstractmethod
from typing import Optional, Union


class Py7zIO(ABC):

    @abstractmethod
    def write(self, s: bytes | bytearray) -> int:
        pass

    @abstractmethod
    def read(self, size: int | None = None) -> bytes:
        pass

    @abstractmethod
    def seek(self, offset: int, whence: int = 0) -> int:
        pass

    @abstractmethod
    def flush(self) -> None:
        pass

    @abstractmethod
    def size(self) -> int:
        pass


class HashIO(Py7zIO):
    def __init__(self, filename):
        self.filename = filename
        self.hash = hashlib.sha256()
        self._size: int = 0

    def write(self, s: bytes | bytearray) -> int:
        self._size += len(s)
        self.hash.update(s)
        return len(s)

    def read(self, length: int | None = None) -> bytes:
        return self.hash.digest()

    def seek(self, offset: int, whence: int = 0) -> int:
        return 0

    def flush(self) -> None:
        pass

    def size(self) -> int:
        return self._size


class Py7zBytesIO(Py7zIO):
    def __init__(self, filename: str, limit: int):
        self.filename = filename
        self.limit = limit
        self._buffer = io.BytesIO()

    def write(self, s: bytes | bytearray) -> int:
        if self.size() < self.limit:
            return self._buffer.write(s)
        else:
            return 0

    def read(self, size: int | None = None) -> bytes:
        return self._buffer.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._buffer.seek(offset, whence)

    def flush(self) -> None:
        return self._buffer.flush()

    def size(self) -> int:
        return self._buffer.getbuffer().nbytes


class WriterFactory(ABC):

    @abstractmethod
    def create(self, filename: str) -> Py7zIO:
        """request writer which compatible with BinaryIO, such as BytesIO object."""
        pass


class HashIOFactory(WriterFactory):
    def __init__(self):
        self.products = {}

    def create(self, filename: str) -> Py7zIO:
        product = HashIO(filename)
        self.products[filename] = product
        return product

    def get(self, filename: str) -> Py7zIO:
        return self.products[filename]


class BytesIOFactory(WriterFactory):

    def __init__(self, limit: int):
        self.limit = limit
        self.products: dict[str, Py7zBytesIO] = {}

    def create(self, filename: str) -> Py7zIO:
        product = Py7zBytesIO(filename, self.limit)
        self.products[filename] = product
        return product

    def get(self, filename):
        return self.products[filename]


class NullIOFactory(WriterFactory):
    def __init__(self):
        pass

    def create(self, filename: str) -> Py7zIO:
        return NullIO()


class MemIO:
    """pathlib.Path-like IO class to write memory"""

    def __init__(self, fname: str, factory: WriterFactory):
        self._buf: Py7zIO | None = None
        self._closed = True
        self.fname = fname
        self.factory = factory

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def name(self) -> str:
        return self.fname

    @property
    def closed(self) -> bool:
        return self._closed

    def size(self) -> int:
        return self.__sizeof__()

    def __sizeof__(self) -> int:
        if self._buf is None:
            return -1
        return self._buf.size()

    def flush(self) -> None:
        if self._buf is not None:
            self._buf.flush()

    def write(self, s: bytes | bytearray) -> int:
        if self._buf is None:
            return -1
        return self._buf.write(s)

    def read(self, length: int | None = None) -> bytes:
        if self._buf is None:
            return b""
        if length is not None:
            return self._buf.read(length)
        else:
            return self._buf.read()

    def close(self) -> None:
        self._closed = True
        if self._buf is not None:
            self._buf.seek(0)

    def seek(self, offset: int, whence: int = 0) -> int:
        if self._buf is None:
            return -1
        return self._buf.seek(offset, whence)

    def open(self, mode: str = "w"):
        self._mode = mode
        self._closed = False
        if self._buf is None:
            self._buf = self.factory.create(self.fname)
        else:
            self._buf.seek(0)
        return self

    @property
    def parent(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class NullIO(Py7zIO):
    """pathlib.Path-like IO class of /dev/null"""

    def __init__(self):
        pass

    def write(self, data):
        return len(data)

    def read(self, length=None):
        if length is not None:
            return bytes(length)
        else:
            return b""

    def close(self):
        pass

    def flush(self):
        pass

    def open(self, mode=None):
        return self

    @property
    def parent(self):
        return self

    def mkdir(self):
        return None

    def seek(self, offset: int, whence: int = 0) -> int:
        return offset

    def size(self):
        return 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class BufferOverflow(Exception):
    pass


class Buffer:
    def __init__(self, size: int = 16):
        self._buf = bytearray(size)
        self._buflen = 0
        self.view = memoryview(self._buf[0:0])

    def add(self, data: bytes | bytearray | memoryview):
        length = len(data)
        self._buf[self._buflen :] = data
        self._buflen += length
        self.view = memoryview(self._buf[0 : self._buflen])

    def reset(self) -> None:
        self._buflen = 0
        self.view = memoryview(self._buf[0:0])

    def set(self, data: bytes | bytearray | memoryview) -> None:
        length = len(data)
        self._buf[0:] = data
        self._buflen = length
        self.view = memoryview(self._buf[0:length])

    def get(self) -> bytearray:
        val = self._buf[: self._buflen]
        self.reset()
        return val

    def __len__(self) -> int:
        return self._buflen

    def __bytes__(self):
        return bytes(self._buf[0 : self._buflen])
