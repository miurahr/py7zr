import os
import platform
import shutil
import tempfile

import pytest

import py7zr
import py7zr.helpers

testdata_path = os.path.join(os.path.dirname(__file__), 'data')

targets = ["zstd", "bzip2", "lzma+bcj", "lzma2+bcj", "lzma2+bcj+aes", "zstd+aes"]
target_dict = {"zstd": [{"id": py7zr.FILTER_ZSTD}],
               "bzip2": [{"id": py7zr.FILTER_BZIP2}],
               "lzma+bcj": [{"id": py7zr.FILTER_X86}, {"id": py7zr.FILTER_LZMA, "preset": 7}],
               "lzma2+bcj": [{"id": py7zr.FILTER_X86}, {"id": py7zr.FILTER_LZMA2, "preset": 7}],
               "zstd+aes": [{"id": py7zr.FILTER_ZSTD}, {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}],
               "lzma2+bcj+aes": [{"id": py7zr.FILTER_X86}, {"id": py7zr.FILTER_LZMA2, "preset": 7},
                                 {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}]}

@pytest.mark.benchmark
@pytest.mark.parametrize("name", targets)
def test_benchmark_filters_compress(tmp_path, benchmark, name):

    def compressor(filters, password):
        with py7zr.SevenZipFile(tmp_path.joinpath('target.7z'), 'w', filters=filters, password=password) as szf:
            szf.writeall(tmp_path.joinpath('src'), 'src')

    def setup():
        tmp_path.joinpath('target.7z').unlink(missing_ok=True)

    with py7zr.SevenZipFile(os.path.join(testdata_path, 'mblock_1.7z'), 'r') as szf:
        szf.extractall(path=tmp_path.joinpath('src'))
    filters = target_dict[name]
    if name.endswith('aes'):
        password = 'secret'
    else:
        password = None
    benchmark.pedantic(compressor, setup=setup, args=[filters, password], iterations=1, rounds=3)


@pytest.mark.benchmark
@pytest.mark.parametrize("name", targets)
def test_benchmark_filters_decompress(tmp_path, benchmark, name):

    def decompressor(secret):
        with py7zr.SevenZipFile(tmp_path.joinpath('target.7z'), 'r', password=secret) as szf:
            szf.extractall(tmp_path.joinpath('tgt'))

    def setup():
        shutil.rmtree(tmp_path.joinpath('tgt'), ignore_errors=True)

    with py7zr.SevenZipFile(os.path.join(testdata_path, 'mblock_1.7z'), 'r') as szf:
        szf.extractall(path=tmp_path.joinpath('src'))
    filters = target_dict[name]
    if name.endswith('aes'):
        password = 'secret'
    else:
        password = None
    with py7zr.SevenZipFile(tmp_path.joinpath('target.7z'), 'w', filters=filters, password=password) as szf:
        szf.writeall(tmp_path.joinpath('src'), 'src')
    benchmark.pedantic(decompressor, setup=setup, args=[password], iterations=1, rounds=3)


@pytest.mark.benchmark
@pytest.mark.skip(reason="manual run")
def test_benchmark_calculate_key1(benchmark):
    password = 'secret'.encode('utf-16LE')
    cycles = 19
    salt = b''
    expected = b'e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d'
    key = benchmark(py7zr.helpers._calculate_key1, password, cycles, salt, 'sha256')
    assert key == expected


@pytest.mark.benchmark
@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="Pypy has a bug around ctypes")
@pytest.mark.skip(reason="manual run")
def test_benchmark_calculate_key2(benchmark):
    password = 'secret'.encode('utf-16LE')
    cycles = 19
    salt = b''
    expected = b'e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d'
    key = benchmark(py7zr.helpers._calculate_key2, password, cycles, salt, 'sha256')
    assert key == expected


@pytest.mark.benchmark
@pytest.mark.skip(reason="manual run")
def test_benchmark_calculate_key3(benchmark):
    password = 'secret'.encode('utf-16LE')
    cycles = 19
    salt = b''
    expected = b'e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d'
    key = benchmark(py7zr.helpers._calculate_key3, password, cycles, salt, 'sha256')
    assert key == expected
