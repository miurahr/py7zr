import datetime
import lzma
import os

import pytest

import py7zr.compression
import py7zr.helpers
import py7zr.properties

testdata_path = os.path.join(os.path.dirname(__file__), 'data')


@pytest.mark.unit
def test_simple_compress_and_decompress():
    sevenzip_compressor = py7zr.compression.SevenZipCompressor()
    lzc = sevenzip_compressor.compressor
    out1 = lzc.compress(b"Some data\n")
    out2 = lzc.compress(b"Another piece of data\n")
    out3 = lzc.compress(b"Even more data\n")
    out4 = lzc.flush()
    result = b"".join([out1, out2, out3, out4])
    size = len(result)
    #
    filters = sevenzip_compressor.filters
    decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
    out5 = decompressor.decompress(result)
    assert out5 == b'Some data\nAnother piece of data\nEven more data\n'
    #
    coders = sevenzip_compressor.coders
    crc = py7zr.helpers.calculate_crc32(result)
    decompressor = py7zr.compression.SevenZipDecompressor(coders, size, crc)
    out6 = decompressor.decompress(result)
    assert out6 == b'Some data\nAnother piece of data\nEven more data\n'


@pytest.mark.basic
def test_py7zr_write_and_read_single(capsys, tmp_path):
    target = tmp_path.joinpath('target.7z')
    archive = py7zr.SevenZipFile(target, 'w')
    archive.writeall(os.path.join(testdata_path, "test1.txt"), "test1.txt")
    assert len(archive.files) == 1
    archive.close()
    with target.open('rb') as target_archive:
        val = target_archive.read(1000)
        assert val.startswith(py7zr.properties.MAGIC_7Z)
    archive = py7zr.SevenZipFile(target, 'r')
    assert archive.test()
    ctime = datetime.datetime.fromtimestamp(os.stat(os.path.join(testdata_path, "test1.txt")).st_ctime)
    creationdate = ctime.astimezone(py7zr.helpers.Local).strftime("%Y-%m-%d")
    creationtime = ctime.astimezone(py7zr.helpers.Local).strftime("%H:%M:%S")
    expected = "total 1 files and directories in solid archive\n" \
               "   Date      Time    Attr         Size   Compressed  Name\n" \
               "------------------- ----- ------------ ------------  ------------------------\n"
    expected += "{} {} ....A           33           37  test1.txt\n".format(creationdate, creationtime)
    expected += "------------------- ----- ------------ ------------  ------------------------\n"
    cli = py7zr.cli.Cli()
    cli.run(["l", str(target)])
    out, err = capsys.readouterr()
    assert expected == out
