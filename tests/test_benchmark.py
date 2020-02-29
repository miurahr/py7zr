import os
import tempfile

import pytest

import py7zr

testdata_path = os.path.join(os.path.dirname(__file__), 'data')


@pytest.mark.benchmark
@pytest.mark.parametrize("data", ['solid.7z', 'mblock_1.7z'])
def test_extract_benchmark(tmp_path, benchmark, data):

    def extractor(path, target):
        target_path = tempfile.mkdtemp(dir=str(path))
        szf = py7zr.SevenZipFile(os.path.join(testdata_path, target), 'r')
        szf.extractall(path=target_path)
        szf.close()

    benchmark(extractor, tmp_path, data)
