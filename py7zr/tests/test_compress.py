import binascii
import io
import lzma
import os
import py7zr.archiveinfo
import py7zr.compression
import py7zr.helpers
import py7zr.io
import pytest

testdata_path = os.path.join(os.path.dirname(__file__), 'data')


@pytest.mark.unit
def test_simple_compress_and_properties():
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
    decompressor = py7zr.compression.SevenZipDecompressor(coders, size)
    out6 = decompressor.decompress(result)
    assert out6 == b'Some data\nAnother piece of data\nEven more data\n'


@pytest.mark.unit
def test_write_archive_properties():
    """
    test write function of ArchiveProperties class.
    Structure is as follows:
    BYTE Property.ARCHIVE_PROPERTIES (0x02)
       UINT64 PropertySize   (7 for test)
       BYTE PropertyData(PropertySize) b'0123456789abcd' for test
    BYTE Property.END (0x00)
    """
    archiveproperties = py7zr.archiveinfo.ArchiveProperties()
    archiveproperties.property_data = [binascii.unhexlify('0123456789abcd')]
    buf = io.BytesIO()
    archiveproperties.write(buf)
    assert buf.getvalue() == binascii.unhexlify('02070123456789abcd00')


@pytest.mark.unit
def test_write_packinfo():
    pi = py7zr.archiveinfo.PackInfo()
    pi.packpos = 0
    pi.numstreams = 1
    pi.packsizes = [64]
    pi.crcs = [py7zr.helpers.calculate_crc32(b'abcd')]


@pytest.mark.unit
def test_startheader_calccrc():
    startheader = py7zr.archiveinfo.SignatureHeader()
    startheader.version = (0, 4)
    startheader.nextheaderofs = 1024
    startheader.nextheadersize = 32
    # set test data to buffer that start with Property.ENCODED_HEADER
    fp = open(os.path.join(testdata_path, 'test_5.7z'), 'rb')
    buffer = io.BytesIO(b'\x17\x060\x01\tp\x00\x07\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00'
                        b'\x00\x10\x00\x0c\x80\x9d\n\x01\xe5\xa1\xb7b\x00\x00')
    header = py7zr.archiveinfo.Header.retrieve(fp, buffer, start_pos=32)
    # FIXME:
    # startheader.calccrc(header)


@pytest.mark.unit
def test_write_digests():
    digests = py7zr.archiveinfo.Digests()
    digests.crcs = [0x12345, 0x12345, 0x12345]
    digests.defined = [True, True, True]
    buf = io.BytesIO()
    digests.write(buf)
    actual = buf.getvalue()
    assert actual == b'\xffE#\x01\x00E#\x01\x00E#\x01\x00'


@pytest.mark.unit
def test_write_substreamsinfo():
    substreamsinfo = py7zr.archiveinfo.SubstreamsInfo()
    substreamsinfo.digests = py7zr.archiveinfo.Digests()
    substreamsinfo.digests.crcs = [0x12345, 0x12345, 0x12345]
    substreamsinfo.digests.defined = [True, True, True]
    substreamsinfo.digestsdefined = substreamsinfo.digests.defined
    substreamsinfo.num_unpackstreams_folders = [1]
    substreamsinfo.unpacksizes = [34]


@pytest.mark.unit
def test_write_packinfo():
    packinfo = py7zr.archiveinfo.PackInfo()
    packinfo.packpos = 0
    packinfo.packsizes = [48]
    buffer = io.BytesIO()
    packinfo.write(buffer)
    actual = buffer.getvalue()
    assert actual == b'\x06\x00\x01\t0\x00'