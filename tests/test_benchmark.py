import os
import tempfile

import pytest

import py7zr

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
