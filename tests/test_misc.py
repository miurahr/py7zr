import os
import pathlib
import shutil
import subprocess
import sys

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
def test_read_writed(tmp_path):
    with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "w") as target:
        with py7zr.SevenZipFile(testdata_path.joinpath("mblock_1.7z").open(mode="rb")) as source:
            target.writed(source.readall())
    p7zip_test(tmp_path / "target.7z")
