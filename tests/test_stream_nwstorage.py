import os
import pathlib
from typing import Optional

import requests
from pytest_httpserver import HTTPServer

import py7zr
import py7zr.io

testdata_path = pathlib.Path(os.path.dirname(__file__)).joinpath("data")
os.umask(0o022)


def test_extract_stream(httpserver: HTTPServer):
    httpserver.expect_request("/setup.cfg", method="PUT").respond_with_data("ok")
    httpserver.expect_request("/setup.cfg", method="GET").respond_with_data(
        b"[flake8]\nmax-line-length = 125\n\n[bdist_wheel]\nuniversal=1\n"
    )
    httpserver.expect_request("/setup.py", method="PUT").respond_with_data("ok")
    httpserver.expect_request("/scripts/py7zr", method="PUT").respond_with_data("ok")
    factory = StreamWriterFactory(httpserver)
    with py7zr.SevenZipFile(testdata_path.joinpath("test_1.7z").open(mode="rb")) as archive:
        archive.extractall(factory=factory)
    assert len(factory.products) == 3
    assert "setup.cfg" in factory.products.keys()
    assert "setup.py" in factory.products.keys()
    assert "scripts/py7zr" in factory.products.keys()
    assert factory.products["setup.cfg"].read() == b"[flake8]\nmax-line-length = 125\n\n[bdist_wheel]\nuniversal=1\n"


class StreamWriter(py7zr.io.Py7zIO):
    """Pseudo object storage writer."""

    def __init__(self, httpserver: HTTPServer, fname: str):
        self.httpserver: HTTPServer = httpserver
        self.fname = fname
        self.length = 0

    def write(self, data: [bytes, bytearray]):
        self.length += len(data)
        requests.put(self.httpserver.url_for(self.fname), data=data)
        self.httpserver.check_assertions()

    def read(self, size: Optional[int] = None) -> bytes:
        response = requests.get(self.httpserver.url_for(self.fname))
        return response.content

    def seek(self, offset: int, whence: int = 0) -> int:
        return offset

    def flush(self) -> None:
        pass

    def size(self) -> int:
        return self.length


class StreamWriterFactory(py7zr.io.WriterFactory):
    """Factory class to return StreamWriter object."""

    def __init__(self, httpserver: HTTPServer):
        self.httpserver: HTTPServer = httpserver
        self.products = {}

    def create(self, filename: str) -> py7zr.io.Py7zIO:
        product = StreamWriter(self.httpserver, filename)
        self.products[filename] = product
        return product
