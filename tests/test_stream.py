import io
import os
import pathlib
from typing import Optional

import requests
from pytest_httpserver import HTTPServer

import py7zr
import py7zr.io
from py7zr.io import Py7zIO

testdata_path = pathlib.Path(os.path.dirname(__file__)).joinpath("data")
os.umask(0o022)


def test_extract_stream(httpserver: HTTPServer):
    httpserver.expect_request("/setup.cfg", method="PUT").respond_with_data("ok")
    httpserver.expect_request("/setup.cfg", method="GET").respond_with_data("dummy data")
    httpserver.expect_request("/setup.py", method="PUT").respond_with_data("ok")
    httpserver.expect_request("/scripts/py7zr", method="PUT").respond_with_data("ok")
    factory = StreamWriterFactory(httpserver)
    with py7zr.SevenZipFile(testdata_path.joinpath("test_1.7z").open(mode="rb")) as archive:
        result = archive.readall(factory=factory)
    assert len(factory.debug_info) == 3
    assert "setup.cfg" in factory.debug_info
    assert "setup.py" in factory.debug_info
    assert "scripts/py7zr" in factory.debug_info
    assert result["setup.cfg"].read() == b"[flake8]\nmax-line-length = 125\n\n[bdist_wheel]\nuniversal=1\n"


def test_extract_stream_create_traditional(tmp_path, httpserver: HTTPServer):
    httpserver.expect_request("/setup.cfg", method="PUT").respond_with_data("ok")
    httpserver.expect_request("/setup.py", method="PUT").respond_with_data("ok")
    httpserver.expect_request("/scripts/py7zr", method="PUT").respond_with_data("ok")
    factory = StreamWriterFactory(httpserver)
    with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "w") as target:
        with py7zr.SevenZipFile(testdata_path.joinpath("test_1.7z").open(mode="rb")) as source:
            target.writed(source.readall(factory=factory))


class StreamWriter(py7zr.io.Py7zIO):
    """Pseudo object storage writer."""

    def __init__(self, httpserver: HTTPServer, fname: str):
        self.buf = io.BytesIO()  # for test
        self.httpserver: HTTPServer = httpserver  # for test
        self.fname = fname
        self.length = 0

    def write(self, data: [bytes, bytearray]):
        self.length += len(data)
        self.buf.write(data)
        requests.put(self.httpserver.url_for(self.fname), data=data)
        self.httpserver.check_assertions()

    def read(self, size: Optional[int] = None) -> bytes:
        # This may read from other than memory.
        # Here is a stub using BytesIO for test
        return self.buf.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.buf.seek(offset, whence)  # for test

    def flush(self) -> None:
        self.buf.flush()  # for test

    def size(self) -> int:
        return self.length


class StreamWriterFactory(py7zr.io.WriterFactory):
    """Factory class to return StreamWriter object."""

    def __init__(self, httpserver: HTTPServer):
        self.httpserver: HTTPServer = httpserver
        self.debug_info = []  # for test

    def create(self, filename: str) -> Py7zIO:
        self.debug_info.append(filename)
        return StreamWriter(self.httpserver, filename)
