import ctypes
import io
import os
import pathlib
import shutil
import subprocess
import sys
from contextlib import contextmanager

import multivolumefile
import pytest

import py7zr

from . import libarchive_extract, p7zip_test

testdata_path = pathlib.Path(os.path.dirname(__file__)).joinpath("data")
os.umask(0o022)


@pytest.mark.misc
def test_extract_multi_volume(tmp_path):
    with testdata_path.joinpath("lzma2bcj.7z").open("rb") as src:
        with tmp_path.joinpath("lzma2bcj.7z.001").open("wb") as tgt:
            tgt.write(src.read(25000))
        with tmp_path.joinpath("lzma2bcj.7z.002").open("wb") as tgt:
            tgt.write(src.read(27337))
    with multivolumefile.open(tmp_path.joinpath("lzma2bcj.7z"), mode="rb") as tgt:
        with py7zr.SevenZipFile(tgt) as arc:
            arc.extractall(tmp_path.joinpath("tgt"))


@pytest.mark.misc
def test_compress_to_multi_volume(tmp_path):
    tmp_path.joinpath("src").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "lzma2bcj.7z"), path=tmp_path.joinpath("src"))
    with multivolumefile.open(tmp_path.joinpath("target.7z"), mode="wb", volume=10240) as tgt:
        with py7zr.SevenZipFile(tgt, "w") as arc:
            arc.writeall(tmp_path.joinpath("src"), "src")
    assert tmp_path.joinpath("target.7z.0001").stat().st_size == 10240
    assert tmp_path.joinpath("target.7z.0002").stat().st_size == 10240
    assert tmp_path.joinpath("target.7z.0003").stat().st_size == 10240
    assert 6000 < tmp_path.joinpath("target.7z.0004").stat().st_size < 6100
    #
    p7zip_test(tmp_path.joinpath("target.7z.0001"))


@pytest.mark.misc
def test_copy_bcj_file(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath("copy_bcj_1.7z").open(mode="rb")) as ar:
        ar.extractall(tmp_path)


@pytest.mark.misc
@pytest.mark.skipif(sys.platform.startswith("win"), reason="Case uses gcc and posix path on linux/mac")
def test_bcj_file(tmp_path):
    tmp_path.joinpath("src").mkdir()
    # build test target data
    if shutil.which("gcc"):
        result = subprocess.run(
            [
                "gcc",
                "-std=c99",
                "-fPIC",
                "-o",
                tmp_path.joinpath("src").joinpath("bcj_test").as_posix(),
                "-c",
                testdata_path.joinpath("bcj_test.c").as_posix(),
            ],
            stdout=subprocess.PIPE,
        )
        if result.returncode != 0:
            return 0
        #
        tmp_path.joinpath("tgt").mkdir()
        tmp_path.joinpath("tgt2").mkdir()
        my_filters = [{"id": py7zr.FILTER_X86}, {"id": py7zr.FILTER_COPY}]
        with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), filters=my_filters, mode="w") as ar:
            ar.write(tmp_path.joinpath("src/bcj_test"), "bcj_test")
        target = tmp_path.joinpath("target.7z")
        with py7zr.SevenZipFile(target, "r") as ar:
            ar.extractall(tmp_path.joinpath("tgt"))
        p7zip_test(target)
        libarchive_extract(target, tmp_path / "tgt2")


@pytest.mark.files
@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
def test_double_extract_symlink(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath("symlink_2.7z").open(mode="rb")) as archive:
        archive.extractall(path=tmp_path)
    with py7zr.SevenZipFile(testdata_path.joinpath("symlink_2.7z").open(mode="rb")) as archive:
        archive.extractall(path=tmp_path)


class ProgressCallbackExample(py7zr.callbacks.ExtractCallback):
    def __init__(self):
        pass


def test_callback_raw_class():
    # test the case when passed argument is class name.
    # it is wrong, so it become the error.
    with pytest.raises(ValueError):
        with py7zr.SevenZipFile(testdata_path.joinpath("solid.7z").open(mode="rb")) as z:
            z.extractall(None, callback=ProgressCallbackExample)


def test_callback_not_concrete_class():
    # test the case when passed argument is abstract class
    with pytest.raises(TypeError):
        with py7zr.SevenZipFile(testdata_path.joinpath("solid.7z").open(mode="rb")) as z:
            cb = ProgressCallbackExample()
            z.extractall(None, callback=cb)


@pytest.mark.api
def test_extract_callback(tmp_path):
    # test the case when good callback passed.
    class ECB(py7zr.callbacks.ExtractCallback):
        def __init__(self, ofd):
            self.ofd = ofd

        def report_start_preparation(self):
            self.ofd.write("preparation.\n")

        def report_start(self, processing_file_path, processing_bytes):
            self.ofd.write('start "{}" (compressed in {} bytes)\n'.format(processing_file_path, processing_bytes))

        def report_update(self, decompressed_bytes):
            self.ofd.write("decompressed part of {} bytes\n".format(decompressed_bytes))

        def report_end(self, processing_file_path, wrote_bytes):
            self.ofd.write('end "{}" extracted to {} bytes\n'.format(processing_file_path, wrote_bytes))

        def report_postprocess(self):
            self.ofd.write("post processing.\n")

        def report_warning(self, message):
            self.ofd.write("warning: {:s}\n".format(message))

    cb = ECB(sys.stdout)
    with py7zr.SevenZipFile(open(os.path.join(testdata_path, "test_1.7z"), "rb")) as archive:
        archive.extractall(path=tmp_path, callback=cb)


@pytest.mark.misc
@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Only meaningful only on Unix-like OSes",
)
@pytest.mark.slow
def test_extract_high_compression_rate(tmp_path):
    gen = Generator()
    with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "w") as source:
        source.writef(gen, "source")
    limit = int(512e6)  # 0.5GB
    with limit_memory(limit):
        with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "r") as target:
            target.extractall(path=tmp_path)


@contextmanager
def limit_memory(maxsize: int):
    """
    Decorator to limit memory. Raise MemoryError when the limit is exceeded.

    :param maxsize: Maximum size of memory resource to limit
    :raises: MemoryError: When function reaches the limit.
    """
    if sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
        yield
    else:
        import resource

        import psutil  # type: ignore

        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        soft_new = psutil.Process(os.getpid()).memory_info().rss + maxsize
        if soft == -1 or soft_new < soft:
            resource.setrlimit(resource.RLIMIT_AS, (soft_new, hard))
        try:
            yield
        finally:
            resource.setrlimit(resource.RLIMIT_AS, (soft, hard))


class Generator(io.BufferedIOBase):
    def __init__(self):
        super(Generator, self).__init__()
        self.generated = 0
        self.length = int(1e9)
        self.seeked = False

    def readinto(self, b):
        if self.generated > self.length:
            return b""
        buf = self.generate_raw_bytes(len(b))
        b[: len(buf)] = buf
        self.generated += len(buf)
        return len(buf)

    def read1(self, size=-1):
        return self.read(size)

    def read(self, size=-1):
        if self.generated > self.length:
            return b""
        self.generated += size
        return self.generate_raw_bytes(size)

    def seek(self, *args, **kwargs):
        self.seeked = True

    def tell(self) -> int:
        if self.seeked:
            return self.length
        else:
            return 0

    def generate_raw_bytes(self, size):
        return bytes(size)
