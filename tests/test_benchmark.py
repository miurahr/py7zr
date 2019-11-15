import os
import shutil
import tempfile

import pytest

import py7zr

testdata_path = os.path.join(os.path.dirname(__file__), 'data')


def extract_files():
    tmpdir = tempfile.mkdtemp()
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_3.7z'), 'rb'))
    archive.extractall(tmpdir)
    shutil.rmtree(tmpdir)


@pytest.mark.perf
def test_performance_decompress(benchmark):
    benchmark(extract_files)
