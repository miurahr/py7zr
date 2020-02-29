import os

import pytest

import py7zr

testdata_path = os.path.join(os.path.dirname(__file__), 'data')


@pytest.mark.benchmark
def test_benchmark_basic(tmp_path, benchmark):

    def extractor(path):
        szf = py7zr.SevenZipFile(os.path.join(testdata_path, 'solid.7z'), 'r')
        szf.extractall(path=path)
        szf.close()

    benchmark(extractor, tmp_path)
