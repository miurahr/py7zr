import pytest

from . import extract_files


@pytest.mark.files
def test_performance_decompress(benchmark):
    f = 'test_3.7z'
    benchmark(extract_files, f)
