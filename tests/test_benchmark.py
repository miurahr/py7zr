import array
import io
import struct

import pytest

from . import extract_files


@pytest.mark.perf
def test_performance_decompress(benchmark):
    f = 'test_3.7z'
    benchmark(extract_files, f)


@pytest.mark.perf
def test_read_crcs_perf_array(benchmark):
    data0 = 1024
    data1 = 32
    data2 = 1372678730

    def setup():
        buf = io.BytesIO()
        buf.write(struct.pack('<L', data0))
        buf.write(struct.pack('<L', data1))
        buf.write(struct.pack('<L', data2))
        buf.seek(0)
        return (buf, 3), {}

    def target(file, c):
        res = array.array('I', file.read(4 * c))
        return res

    result = benchmark.pedantic(target, setup=setup)
    assert result[0] == data0
    assert result[1] == data1
    assert result[2] == data2


@pytest.mark.perf
def test_read_crcs_perf_closure(benchmark):
    data0 = 1024
    data1 = 32
    data2 = 1372678730

    def setup():
        buf = io.BytesIO()
        buf.write(struct.pack('<L', data0))
        buf.write(struct.pack('<L', data1))
        buf.write(struct.pack('<L', data2))
        buf.seek(0)
        return (buf, 3), {}

    def target(file, c):
        data = file.read(4 * c)
        return [struct.unpack('<L', data[i * 4:i * 4 + 4])[0] for i in range(c)]

    result = benchmark.pedantic(target, setup=setup)
    assert result[0] == data0
    assert result[1] == data1
    assert result[2] == data2
