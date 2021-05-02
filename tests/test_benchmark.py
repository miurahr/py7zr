import os
import platform
import shutil

import pytest

import py7zr
import py7zr.helpers

testdata_path = os.path.join(os.path.dirname(__file__), "data")
targets = [
    ("zstd", [{"id": py7zr.FILTER_ZSTD, "level": 3}]),
    ("bzip2", [{"id": py7zr.FILTER_BZIP2}]),
    ("lzma+bcj", [{"id": py7zr.FILTER_X86}, {"id": py7zr.FILTER_LZMA, "preset": 7}]),
    ("lzma2+bcj", [{"id": py7zr.FILTER_X86}, {"id": py7zr.FILTER_LZMA2, "preset": 7}]),
    (
        "bzip2+aes",
        [{"id": py7zr.FILTER_BZIP2}, {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}],
    ),
    (
        "lzma2+aes",
        [
            {"id": py7zr.FILTER_LZMA2, "preset": 7},
            {"id": py7zr.FILTER_CRYPTO_AES256_SHA256},
        ],
    ),
]


@pytest.mark.benchmark(group="compress")
@pytest.mark.parametrize("name, filters", targets)
def test_benchmark_filters_compress(tmp_path, benchmark, name, filters):
    def compressor(filters, password):
        with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "w", filters=filters, password=password) as szf:
            szf.writeall(tmp_path.joinpath("src"), "src")

    def setup():
        if tmp_path.joinpath("target.7z").exists():
            tmp_path.joinpath("target.7z").unlink()

    with py7zr.SevenZipFile(os.path.join(testdata_path, "mblock_1.7z"), "r") as szf:
        szf.extractall(path=tmp_path.joinpath("src"))
    with py7zr.SevenZipFile(os.path.join(testdata_path, "mblock_1.7z"), "r") as szf:
        archive_info = szf.archiveinfo()
        source_size = archive_info.uncompressed
    if name.endswith("aes"):
        password = "secret"
    else:
        password = None
    benchmark.extra_info["data_size"] = source_size
    benchmark.pedantic(compressor, setup=setup, args=[filters, password], iterations=1, rounds=3)
    benchmark.extra_info["ratio"] = str(tmp_path.joinpath("target.7z").stat().st_size / source_size)


@pytest.mark.benchmark(group="decompress")
@pytest.mark.parametrize("name, filters", targets)
def test_benchmark_filters_decompress(tmp_path, benchmark, name, filters):
    def decompressor(secret):
        with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "r", password=secret) as szf:
            szf.extractall(tmp_path.joinpath("tgt"))

    def setup():
        shutil.rmtree(tmp_path.joinpath("tgt"), ignore_errors=True)

    with py7zr.SevenZipFile(os.path.join(testdata_path, "mblock_1.7z"), "r") as szf:
        szf.extractall(path=tmp_path.joinpath("src"))
    with py7zr.SevenZipFile(os.path.join(testdata_path, "mblock_1.7z"), "r") as szf:
        archive_info = szf.archiveinfo()
        source_size = archive_info.uncompressed

    if name.endswith("aes"):
        password = "secret"
    else:
        password = None
    with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "w", filters=filters, password=password) as szf:
        szf.writeall(tmp_path.joinpath("src"), "src")
    benchmark.extra_info["data_size"] = source_size
    benchmark.extra_info["ratio"] = str(tmp_path.joinpath("target.7z").stat().st_size / source_size)
    benchmark.pedantic(decompressor, setup=setup, args=[password], iterations=1, rounds=3)


textfilters = [
    ("ppmd(text)", [{"id": py7zr.FILTER_PPMD, "order": 8, "mem": "4m"}]),
    ("deflate(text)", [{"id": py7zr.FILTER_DEFLATE}]),
    ("zstd(text)", [{"id": py7zr.FILTER_ZSTD, "level": 3}]),
    ("brotli(text)", [{"id": py7zr.FILTER_BROTLI, "level": 11}]),
]


@pytest.mark.benchmark(group="compress")
@pytest.mark.parametrize("name, filters", textfilters)
def test_benchmark_text_compress(tmp_path, benchmark, name, filters):
    def compressor(filters):
        with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "w", filters=filters) as szf:
            szf.writeall(tmp_path.joinpath("src"), "src")

    def setup():
        if tmp_path.joinpath("target.7z").exists():
            tmp_path.joinpath("target.7z").unlink()

    with py7zr.SevenZipFile(os.path.join(testdata_path, "bzip2_2.7z"), "r") as szf:
        szf.extractall(path=tmp_path.joinpath("src"))
    with py7zr.SevenZipFile(os.path.join(testdata_path, "bzip2_2.7z"), "r") as szf:
        archive_info = szf.archiveinfo()
        source_size = archive_info.uncompressed
    benchmark.extra_info["data_size"] = source_size
    benchmark.pedantic(compressor, setup=setup, args=[filters], iterations=1, rounds=3)
    benchmark.extra_info["ratio"] = str(tmp_path.joinpath("target.7z").stat().st_size / source_size)


@pytest.mark.benchmark(group="decompress")
@pytest.mark.parametrize("name, filters", textfilters)
def test_benchmark_text_decompress(tmp_path, benchmark, name, filters):
    def decompressor():
        with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "r") as szf:
            szf.extractall(tmp_path.joinpath("tgt"))

    def setup():
        shutil.rmtree(tmp_path.joinpath("tgt"), ignore_errors=True)

    with py7zr.SevenZipFile(os.path.join(testdata_path, "bzip2_2.7z"), "r") as szf:
        szf.extractall(path=tmp_path.joinpath("src"))
    with py7zr.SevenZipFile(os.path.join(testdata_path, "bzip2_2.7z"), "r") as szf:
        archive_info = szf.archiveinfo()
        source_size = archive_info.uncompressed
    password = None
    with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "w", filters=filters, password=password) as szf:
        szf.writeall(tmp_path.joinpath("src"), "src")
    benchmark.extra_info["data_size"] = source_size
    benchmark.extra_info["ratio"] = str(tmp_path.joinpath("target.7z").stat().st_size / source_size)
    benchmark.pedantic(decompressor, setup=setup, args=[], iterations=1, rounds=3)


@pytest.mark.benchmark(group="calculate_key")
@pytest.mark.skip(reason="Don't test in ordinary development")
def test_benchmark_calculate_key1(benchmark):
    password = "secret".encode("utf-16LE")
    cycles = 19
    salt = b""
    expected = b"e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d"
    key = benchmark(py7zr.helpers._calculate_key1, password, cycles, salt, "sha256")
    assert key == expected


@pytest.mark.benchmark(group="calculate_key")
@pytest.mark.skip(reason="Don't test in ordinary development")
@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="Will crash on PyPy")
def test_benchmark_calculate_key2(benchmark):
    password = "secret".encode("utf-16LE")
    cycles = 19
    salt = b""
    expected = b"e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d"
    key = benchmark(py7zr.helpers._calculate_key2, password, cycles, salt, "sha256")
    assert key == expected


@pytest.mark.benchmark(group="calculate_key")
@pytest.mark.skip(reason="Don't test in ordinary development")
def test_benchmark_calculate_key3(benchmark):
    password = "secret".encode("utf-16LE")
    cycles = 19
    salt = b""
    expected = b"e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d"
    key = benchmark(py7zr.helpers._calculate_key3, password, cycles, salt, "sha256")
    assert key == expected
