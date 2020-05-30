import os
import platform
import tempfile

import pytest

import py7zr
import py7zr.helpers

testdata_path = os.path.join(os.path.dirname(__file__), 'data')


@pytest.mark.benchmark
@pytest.mark.parametrize("data, password", [('solid.7z', None),
                                            ('mblock_1.7z', None),
                                            ('encrypted_1.7z', 'secret')])
def test_extract_benchmark(tmp_path, benchmark, data, password):

    def extractor(path, target, password):
        target_path = tempfile.mkdtemp(dir=str(path))
        szf = py7zr.SevenZipFile(os.path.join(testdata_path, target), 'r', password=password)
        szf.extractall(path=target_path)
        szf.close()

    benchmark(extractor, tmp_path, data, password)


@pytest.mark.benchmark
def test_benchmark_calculate_key1(benchmark):
    password = 'secret'.encode('utf-16LE')
    cycles = 19
    salt = b''
    expected = b'e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d'
    key = benchmark(py7zr.helpers._calculate_key1, password, cycles, salt, 'sha256')
    assert key == expected


@pytest.mark.benchmark
@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="Pypy has a bug around ctypes")
def test_benchmark_calculate_key2(benchmark):
    password = 'secret'.encode('utf-16LE')
    cycles = 19
    salt = b''
    expected = b'e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d'
    key = benchmark(py7zr.helpers._calculate_key2, password, cycles, salt, 'sha256')
    assert key == expected


@pytest.mark.benchmark
def test_benchmark_calculate_key3(benchmark):
    password = 'secret'.encode('utf-16LE')
    cycles = 19
    salt = b''
    expected = b'e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d'
    key = benchmark(py7zr.helpers._calculate_key3, password, cycles, salt, 'sha256')
    assert key == expected
