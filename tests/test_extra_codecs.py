import os
import pathlib
import zlib

import pytest
from Crypto.Cipher import AES

import py7zr
import py7zr.compressor
from py7zr.exceptions import UnsupportedCompressionMethodError

try:
    import zstandard as Zstd  # type: ignore  # noqa
except ImportError:
    Zstd = None

testdata_path = pathlib.Path(os.path.dirname(__file__)).joinpath('data')
os.umask(0o022)


@pytest.mark.unit
def test_aes_cipher():
    key = b'e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d'
    iv = b'|&\xae\x94do\x8a4\x00\x00\x00\x00\x00\x00\x00\x00'
    indata = b"T\x9f^\xb5\xbf\xdc\x08/\xfe<\xe6i'\x84A^\x83\xdc\xdd5\xe9\xd5\xd0b\xa9\x7fH$\x11\x82\x8d" \
             b"\xce[\x85\xe7\xf2}\xe3oJ*\xc0:\xf4\xfd\x82\xe8I"
    expected = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2" \
               b"\xf7\\m\xe0t\xa6$yF_-\xa0\x0b8f "
    cipher = AES.new(key, AES.MODE_CBC, iv)
    result = cipher.decrypt(indata)
    assert expected == result


@pytest.mark.unit
def test_deflate_compressor():
    plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
    plain_data += plain_data
    compressor = py7zr.compressor.DeflateCompressor()
    outdata = compressor.compress(plain_data)
    outdata += compressor.flush()
    expected = b'c\xd0\x92\xe2TO\x91\xdc`Q|\xaa[Xa\xbd\x95t\xef\xf4\x1f5\xca\xbe/\x1f\x86_y2\xdd\xc9\xe9\x12\x03\x01y\x00'
    assert outdata == expected


@pytest.mark.unit
def test_deflate_compressor_flushed():
    with pytest.raises(zlib.error):
        plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
        plain_data += plain_data
        compressor = py7zr.compressor.DeflateCompressor()
        outdata = compressor.compress(plain_data)
        outdata += compressor.flush()
        outdata += compressor.flush()


@pytest.mark.unit
def test_deflate_decompressor():
    plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
    plain_data += plain_data
    source_data = b'c\xd0\x92\xe2TO\x91\xdc`Q|\xaa[Xa\xbd\x95t\xef\xf4\x1f5\xca\xbe/\x1f\x86_y2\xdd\xc9\xe9\x12\x03\x01y\x00'
    decompressor = py7zr.compressor.DeflateDecompressor()
    outdata = decompressor.decompress(source_data)
    assert outdata == plain_data


@pytest.mark.unit
def test_copy_compressor():
    plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
    compressor = py7zr.compressor.CopyCompressor()
    outdata = compressor.compress(plain_data)
    outdata += compressor.flush()
    assert outdata == plain_data


@pytest.mark.unit
def test_copy_decompressor():
    source_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
    decompressor = py7zr.compressor.CopyDecompressor()
    outdata = decompressor.decompress(source_data)
    assert outdata == source_data


@pytest.mark.unit
@pytest.mark.skipif(Zstd is None, reason="zstd library is not exist.")
def test_zstd_compressor():
    plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
    plain_data += plain_data
    compressor = py7zr.compressor.ZstdCompressor()
    outdata = compressor.compress(plain_data)
    outdata += compressor.flush()
    expected = b"(\xb5/\xfd @E\x01\x00\x04\x02\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4" \
               b"\xe4\x97BB\xd2\x01\x00\x18\xb8z\x02"
    assert outdata == expected


@pytest.mark.unit
@pytest.mark.skipif(Zstd is None, reason="zstd library is not exist.")
def test_zstd_decompressor():
    plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
    plain_data += plain_data
    source_data = b"(\xb5/\xfd @E\x01\x00\x04\x02\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4" \
                  b"\xe4\x97BB\xd2\x01\x00\x18\xb8z\x02"
    property = b'\x01\x04\x04\x00\x00'
    decompressor = py7zr.compressor.ZstdDecompressor(property)
    outdata = decompressor.decompress(source_data)
    assert outdata == plain_data


@pytest.mark.unit
def test_sevenzipcompressor_aes_lzma2():
    plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
    plain_data += plain_data + plain_data
    filters = [
        {"id": py7zr.FILTER_LZMA2, "preset": py7zr.PRESET_DEFAULT},
        {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}
    ]
    compressor = py7zr.compressor.SevenZipCompressor(filters=filters, password='secret')
    outdata = compressor.compress(plain_data)
    outdata += compressor.flush()
    assert len(outdata) < 96
    coders = compressor.coders
    unpacksizes = compressor.unpacksizes
    decompressor = py7zr.compressor.SevenZipDecompressor(coders=coders, packsize=len(outdata), unpacksizes=unpacksizes,
                                                         crc=None, password='secret')
    revert_data = decompressor.decompress(outdata)
    assert revert_data == plain_data


@pytest.mark.unit
def test_aes_compressor():
    compressor = py7zr.compressor.AESCompressor('secret')
    assert compressor.method == py7zr.properties.CompressionMethod.CRYPT_AES256_SHA256
    assert len(compressor.encode_filter_properties()) == 2 + 16


@pytest.mark.unit
def test_sevenzipcompressor_aes_only():
    plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
    plain_data += plain_data
    filters = [
        {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}
    ]
    compressor = py7zr.compressor.SevenZipCompressor(filters=filters, password='secret')
    outdata = compressor.compress(plain_data)
    outdata += compressor.flush()
    assert len(outdata) == 64
    assert outdata != plain_data


@pytest.mark.unit
def test_aes_encrypt_data():
    plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB"
    plain_data += plain_data + plain_data
    compressor = py7zr.compressor.AESCompressor('secret')
    outdata = compressor.compress(plain_data)
    outdata += compressor.flush()
    assert len(outdata) == 96  # 96 = 16 * 6 = len(plain_data) + 3


@pytest.mark.unit
def test_aes_decrypt(monkeypatch):
    properties = b'S\x07|&\xae\x94do\x8a4'
    indata = b"T\x9f^\xb5\xbf\xdc\x08/\xfe<\xe6i'\x84A^\x83\xdc\xdd5\xe9\xd5\xd0b\xa9\x7fH$\x11\x82\x8d" \
             b"\xce[\x85\xe7\xf2}\xe3oJ*\xc0:\xf4\xfd\x82\xe8I"
    expected = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2" \
               b"\xf7\\m\xe0t\xa6$yF_-\xa0\x0b8f "
    decompressor = py7zr.compressor.AESDecompressor(properties, 'secret')
    assert decompressor.decompress(indata) == expected


@pytest.mark.files
def test_extract_bzip2(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('bzip2_2.7z').open(mode='rb'))
    archive.extractall(path=tmp_path)
    archive.close()


@pytest.mark.files
def test_extract_ppmd(tmp_path):
    with pytest.raises(UnsupportedCompressionMethodError):
        archive = py7zr.SevenZipFile(testdata_path.joinpath('ppmd.7z').open(mode='rb'))
        archive.extractall(path=tmp_path)
        archive.close()


@pytest.mark.files
def test_extract_deflate(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('deflate.7z').open(mode='rb')) as archive:
        archive.extractall(path=tmp_path)


@pytest.mark.files
@pytest.mark.skipif(Zstd is None, reason="zstandard library does not exist.")
def test_extract_zstd(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('zstd.7z').open(mode='rb')) as archive:
        archive.extractall(path=tmp_path)


@pytest.mark.files
@pytest.mark.skipif(Zstd is None, reason="zstandard library does not exist.")
@pytest.mark.skip(reason="Python lzma module does not allow BCJ only filter.")
def test_extract_p7zip_zstd(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('p7zip-zstd.7z').open('rb')) as archive:
        archive.extractall(path=tmp_path)
