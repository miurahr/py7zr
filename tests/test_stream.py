import io
import os
import pathlib
from typing import Optional, Union

import pytest

import py7zr
import py7zr.io
from py7zr import SevenZipFile

from . import p7zip_test

testdata_path = pathlib.Path(os.path.dirname(__file__)).joinpath("data")
os.umask(0o022)


class TestArchiveWriter(py7zr.io.Py7zIO):

    def __init__(self, fname, target: SevenZipFile):
        self.fname = fname
        self.target = target
        self.buffer = io.BytesIO()

    def write(self, s: Union[bytes, bytearray]) -> int:
        return self.buffer.write(s)

    def read(self, size: Optional[int] = None) -> bytes:
        return self.buffer.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.buffer.seek(offset, whence)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self.target.writef(self.buffer, self.fname)

    def size(self) -> int:
        return self.buffer.getbuffer().nbytes


class TestWriterFactory(py7zr.io.WriterFactory):
    def __init__(self, target: SevenZipFile):
        self.target = target

    def create(self, filename: str) -> py7zr.io.Py7zIO:
        return TestArchiveWriter(filename, self.target)


@pytest.mark.files
def test_read_write_new(tmp_path):
    with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "w") as target:
        with py7zr.SevenZipFile(testdata_path.joinpath("mblock_1.7z").open(mode="rb")) as source:
            source.extractall(factory=TestWriterFactory(target))
    p7zip_test(tmp_path / "target.7z")
