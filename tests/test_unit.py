import binascii
import ctypes
import datetime
import hashlib
import io
import lzma
import os
import pathlib
import stat
import struct
import sys

import pytest

import py7zr.archiveinfo
import py7zr.compressor
import py7zr.helpers
import py7zr.properties
from py7zr.py7zr import FILE_ATTRIBUTE_UNIX_EXTENSION

testdata_path = os.path.join(os.path.dirname(__file__), "data")


@pytest.mark.unit
def test_py7zr_signatureheader():
    header_data = io.BytesIO(
        b"\x37\x7a\xbc\xaf\x27\x1c\x00\x02\x70\x2a\xb7\x37\xa0\x00\x00\x00\x00\x00\x00\x00\x21"
        b"\x00\x00\x00\x00\x00\x00\x00\xb9\xb8\xe4\xbf"
    )
    header = py7zr.archiveinfo.SignatureHeader.retrieve(header_data)
    assert header is not None
    assert header.version == (b"\x00", b"\x02")
    assert header.nextheaderofs == 160


@pytest.mark.unit
def test_py7zr_mainstreams():
    header_data = io.BytesIO(
        b"\x04\x06\x00\x01\t0\x00\x07\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00\x00\x00\x02\x0cB\x00"
        b"\x08\r\x02\t!\n\x01>jb\x08\xce\x9a\xb7\x88\x00\x00"
    )
    pid = header_data.read(1)
    assert pid == py7zr.properties.Property.MAIN_STREAMS_INFO
    streams = py7zr.archiveinfo.StreamsInfo.retrieve(header_data)
    assert streams is not None


@pytest.mark.unit
def test_py7zr_folder_retrive():
    header_data = io.BytesIO(b"\x0b" b"\x01\x00\x01#\x03\x01\x01\x05]\x00\x10\x00\x00")
    pid = header_data.read(1)
    assert pid == py7zr.properties.Property.FOLDER
    num_folders = py7zr.archiveinfo.read_byte(header_data)
    assert num_folders == 1
    external = py7zr.archiveinfo.read_byte(header_data)
    assert external == 0x00
    folder = py7zr.archiveinfo.Folder.retrieve(header_data)
    assert folder.packed_indices == [0]
    assert folder.digestdefined is False
    coder = folder.coders[0]
    assert coder["method"] == b"\x03\x01\x01"
    assert coder["properties"] == b"]\x00\x10\x00\x00"
    assert coder["numinstreams"] == 1
    assert coder["numoutstreams"] == 1


@pytest.mark.unit
def test_py7zr_folder_write():
    folders = []
    for _ in range(1):
        folder = py7zr.archiveinfo.Folder()
        folder.bindpairs = []
        folder.coders = [
            {
                "method": b"\x03\x01\x01",
                "numinstreams": 1,
                "numoutstreams": 1,
                "properties": b"]\x00\x10\x00\x00",
            }
        ]
        folder.crc = None
        folder.digestdefined = False
        folder.packed_indices = [0]
        folder.solid = True
        folders.append(folder)
    #
    buffer = io.BytesIO()
    # following should be run in StreamsInfo class.
    py7zr.archiveinfo.write_byte(buffer, py7zr.properties.Property.FOLDER)
    py7zr.archiveinfo.write_uint64(buffer, len(folders))
    external = b"\x00"
    py7zr.archiveinfo.write_byte(buffer, external)
    for folder in folders:
        folder.write(buffer)
    actual = buffer.getvalue()
    assert actual == b"\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00\x10\x00\x00"


@pytest.mark.unit
def test_py7zr_unpack_info():
    # prepare for unpack_info values
    unpack_info = py7zr.archiveinfo.UnpackInfo()
    unpack_info.folders = []
    for _ in range(1):
        folder = py7zr.archiveinfo.Folder()
        folder.bindpairs = []
        folder.coders = [
            {
                "method": b"\x03\x01\x01",
                "numinstreams": 1,
                "numoutstreams": 1,
                "properties": b"]\x00\x10\x00\x00",
            }
        ]
        folder.crc = None
        folder.digestdefined = False
        folder.packed_indices = [0]
        folder.solid = True
        folder.unpacksizes = [0x22]
        unpack_info.folders.append(folder)
    unpack_info.numfolders = len(unpack_info.folders)
    #
    buffer = io.BytesIO()
    unpack_info.write(buffer)
    actual = buffer.getvalue()
    assert actual == b"\x07\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00\x10\x00\x00\x0c\x22\x00"


@pytest.mark.unit
def test_py7zr_substreamsinfo():
    header_data = io.BytesIO(b"\x08\x0d\x03\x09\x6f\x3a\n\x01\xdb\xaej\xb3\x07\x8d\xbf\xdc\xber\xfc\x80\x00")
    pid = header_data.read(1)
    assert pid == py7zr.properties.Property.SUBSTREAMS_INFO
    folders = [py7zr.archiveinfo.Folder()]
    folders[0].unpacksizes = [728]
    numfolders = 1
    ss = py7zr.archiveinfo.SubstreamsInfo.retrieve(header_data, numfolders, folders)
    pos = header_data.tell()
    print(pos)
    assert ss.digestsdefined == [True, True, True]
    assert ss.digests[0] == 3010113243
    assert ss.digests[1] == 3703540999
    assert ss.digests[2] == 2164028094
    assert ss.num_unpackstreams_folders[0] == 3
    assert ss.unpacksizes == [111, 58, 559]


@pytest.mark.unit
def test_py7zr_substreamsinfo_write():
    folders = [py7zr.archiveinfo.Folder()]
    folders[0].unpacksizes = [728]
    ss = py7zr.archiveinfo.SubstreamsInfo()
    buffer = io.BytesIO()
    ss.digestsdefined = [True, True, True]
    ss.digests = [3010113243, 3703540999, 2164028094]
    ss.num_unpackstreams_folders = [3]
    ss.unpacksizes = [111, 58, 559]
    ss.write(buffer)
    actual = buffer.getvalue()
    assert actual == b"\x08\x0d\x03\x09\x6f\x3a\n\x01\xdb\xaej\xb3\x07\x8d\xbf\xdc\xber\xfc\x80\x00"


@pytest.mark.unit
def test_py7zr_header():
    fp = open(os.path.join(testdata_path, "solid.7z"), "rb")
    header_data = io.BytesIO(
        b"\x01"
        b"\x04\x06\x00\x01\t0\x00\x07\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00\x00\x00\x02\x0cB\x00"
        b"\x08\r\x02\t!\n\x01>jb\x08\xce\x9a\xb7\x88\x00\x00"
        b"\x05\x03\x0e\x01\x80"
        b"\x11=\x00t\x00e\x00s\x00t\x00\x00\x00"
        b"t\x00e\x00s\x00t\x001\x00.\x00t\x00x\x00t\x00\x00\x00"
        b"t\x00e\x00s\x00t\x00/\x00t\x00e\x00s\x00t\x002\x00.\x00t\x00x\x00t\x00\x00\x00"
        b"\x14\x1a\x01\x00\x04>\xe6\x0f{H\xc6\x01d\xca \x8byH\xc6\x01\x8c\xfa\xb6\x83yH\xc6\x01"
        b"\x15\x0e\x01\x00\x10\x00\x00\x00 \x00\x00\x00 \x00\x00\x00"
        b"\x00\x00"
    )
    header = py7zr.archiveinfo.Header.retrieve(fp, header_data, start_pos=32)
    assert header is not None
    assert header.files_info is not None
    assert header.main_streams is not None
    assert len(header.files_info.files) == 3


@pytest.mark.unit
def test_py7zr_encoded_header():
    fp = open(os.path.join(testdata_path, "test_5.7z"), "rb")
    # set test data to buffer that start with Property.ENCODED_HEADER
    buffer = io.BytesIO(
        b"\x17\x060\x01\tp\x00\x07\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00"
        b"\x00\x10\x00\x0c\x80\x9d\n\x01\xe5\xa1\xb7b\x00\x00"
    )
    header = py7zr.archiveinfo.Header.retrieve(fp, buffer, start_pos=32)
    assert header is not None
    assert header.files_info is not None
    assert header.main_streams is not None
    assert len(header.files_info.files) == 3


@pytest.mark.unit
def test_py7zr_files_info_1():
    header_data = io.BytesIO(
        b"\x05\x03\x0e\x01\x80\x11=\x00t\x00e\x00s\x00t\x00\x00\x00t\x00e\x00s\x00t\x001\x00."
        b"\x00t\x00x\x00t\x00\x00\x00t\x00e\x00s\x00t\x00/\x00t\x00e\x00s\x00t\x002\x00.\x00t\x00x"
        b"\x00t\x00\x00\x00\x14\x1a\x01\x00\x04>\xe6\x0f{H\xc6\x01d\xca \x8byH\xc6\x01\x8c\xfa\xb6"
        b"\x83yH\xc6\x01\x15\x0e\x01\x00\x10\x00\x00\x00 \x00\x00\x00 \x00\x00\x00\x00\x00"
    )
    pid = header_data.read(1)
    assert pid == py7zr.properties.Property.FILES_INFO
    files_info = py7zr.archiveinfo.FilesInfo.retrieve(header_data)
    assert files_info is not None
    assert files_info.files[0].get("filename") == "test"
    assert files_info.files[1].get("filename") == "test1.txt"
    assert files_info.files[2].get("filename") == "test/test2.txt"


@pytest.mark.unit
def test_py7zr_files_info_2():
    header_data = io.BytesIO(
        b"\x05\x04\x11_\x00c\x00o\x00p\x00y\x00i\x00n\x00g\x00.\x00t\x00x\x00t\x00\x00\x00H\x00"
        b"i\x00s\x00t\x00o\x00r\x00y\x00.\x00t\x00x\x00t\x00\x00\x00L\x00i\x00c\x00e\x00n\x00s"
        b"\x00e\x00.\x00t\x00x\x00t\x00\x00\x00r\x00e\x00a\x00d\x00m\x00e\x00.\x00t\x00x\x00t\x00"
        b'\x00\x00\x14"\x01\x00\x00[\x17\xe6\xc70\xc1\x01\x00Vh\xb5\xda\xf8\xc5\x01\x00\x97\xbd'
        b"\xf9\x07\xf7\xc4\x01\x00gK\xa8\xda\xf8\xc5\x01\x15\x12\x01\x00  \x00\x00  \x00"
        b"\x00  \x00\x00  \x00\x00\x00\x00"
    )
    pid = header_data.read(1)
    assert pid == py7zr.properties.Property.FILES_INFO
    files_info = py7zr.archiveinfo.FilesInfo.retrieve(header_data)
    assert files_info is not None
    assert len(files_info.files) == 4
    assert files_info.files[0].get("filename") == "copying.txt"
    assert files_info.files[0].get("attributes") == 0x2020
    assert files_info.files[1].get("filename") == "History.txt"
    assert files_info.files[1].get("attributes") == 0x2020
    assert files_info.files[2].get("filename") == "License.txt"
    assert files_info.files[2].get("attributes") == 0x2020
    assert files_info.files[3].get("filename") == "readme.txt"
    assert files_info.files[3].get("attributes") == 0x2020


@pytest.mark.unit
def test_lzma_lzma2_compressor():
    filters = [{"id": 33, "dict_size": 16777216}]
    assert lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters) is not None


@pytest.mark.unit
def test_lzma_lzma2bcj_compressor():
    filters = [{"id": 4}, {"id": 33, "dict_size": 16777216}]
    assert lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters) is not None


@pytest.mark.unit
@pytest.mark.parametrize(
    "abytes, count, checkall, expected",
    [
        (
            b"\xb4\x80",
            9,
            False,
            [True, False, True, True, False, True, False, False, True],
        ),
        (
            b"\xff\xc0",
            10,
            False,
            [True, True, True, True, True, True, True, True, True, True],
        ),
        (
            b"\xff\xff\x80",
            17,
            False,
            [
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
            ],
        ),
    ],
)
def test_read_booleans(abytes, count, checkall, expected):
    buf = io.BytesIO(abytes)
    actual = py7zr.archiveinfo.read_boolean(buf, count, checkall)
    assert actual == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "booleans, all_defined, expected",
    [
        (
            [True, False, True, True, False, True, False, False, True],
            False,
            b"\xb4\x80",
        ),
        (
            [True, True, True, True, True, True, True, True, True, True],
            False,
            b"\xff\xc0",
        ),
        (
            [
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
            ],
            False,
            b"\xff\xff\x80",
        ),
        (
            [True, False, True, True, False, True, False, False, True],
            True,
            b"\x00\xb4\x80",
        ),
    ],
)
def test_write_booleans(booleans, all_defined, expected):
    buffer = io.BytesIO()
    py7zr.archiveinfo.write_boolean(buffer, booleans, all_defined=all_defined)
    actual = buffer.getvalue()
    assert actual == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "testinput, expected",
    [
        (1, b"\x01"),
        (127, b"\x7f"),
        (128, b"\x80\x80"),
        (65535, b"\xc0\xff\xff"),
        (441, b"\x81\xb9"),
        (0xFFFF7F, b"\xe0\x7f\xff\xff"),
        (0x0E002100, b"\xee\x00\x21\x00"),
        (0xFFFFFFFF, b"\xf0\xff\xff\xff\xff"),
        (0x7F1234567F, b"\xf8\x7f\x56\x34\x12\x7f"),
        (0x1234567890ABCD, b"\xfe\xcd\xab\x90\x78\x56\x34\x12"),
        (0xCF1234567890ABCD, b"\xff\xcd\xab\x90\x78\x56\x34\x12\xcf"),
    ],
)
def test_write_uint64(testinput, expected):
    buf = io.BytesIO()
    py7zr.archiveinfo.write_uint64(buf, testinput)
    actual = buf.getvalue()
    assert actual == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "testinput, expected",
    [
        (b"\x01", 1),
        (b"\x7f", 127),
        (b"\x80\x80", 128),
        (b"\x81\xb9", 441),
        (b"\xc0\xff\xff", 65535),
        (b"\xe0\x7f\xff\xff", 0xFFFF7F),
        (b"\xee\x00\x21\x00", 0x0E002100),
        (b"\xf0\xff\xff\xff\xff", 0xFFFFFFFF),
        (b"\xf8\x7f\x56\x34\x12\x7f", 0x7F1234567F),
        (b"\xfe\xcd\xab\x90\x78\x56\x34\x12", 0x1234567890ABCD),
        (b"\xff\xcd\xab\x90\x78\x56\x34\x12\xcf", 0xCF1234567890ABCD),
    ],
)
def test_read_uint64(testinput, expected):
    buf = io.BytesIO(testinput)
    assert py7zr.archiveinfo.read_uint64(buf) == expected


@pytest.mark.unit
@pytest.mark.parametrize("testinput, expected", [(b"t\x00e\x00s\x00t\x00\x00\x00", "test")])
def test_read_utf16(testinput, expected):
    buf = io.BytesIO(testinput)
    actual = py7zr.archiveinfo.read_utf16(buf)
    assert actual == expected


@pytest.mark.unit
@pytest.mark.parametrize("testinput, expected", [("test", b"t\x00e\x00s\x00t\x00\x00\x00")])
def test_write_utf16(testinput, expected):
    buf = io.BytesIO()
    py7zr.archiveinfo.write_utf16(buf, testinput)
    actual = buf.getvalue()
    assert actual == expected


@pytest.mark.unit
def test_write_packinfo():
    packinfo = py7zr.archiveinfo.PackInfo()
    packinfo.packpos = 0
    packinfo.packsizes = [48]
    packinfo.crcs = [py7zr.helpers.calculate_crc32(b"abcd")]
    packinfo.digestdefined = [True]
    packinfo.enable_digests = True
    packinfo.numstreams = 1
    buffer = io.BytesIO()
    packinfo.write(buffer)
    actual = buffer.getvalue()
    assert actual == b"\x06\x00\x01\t0\n\x01\x11\xcd\x82\xed\x00"


@pytest.mark.unit
def test_utc():
    dt = datetime.datetime(2019, 6, 1, 12, 13, 14, 0, tzinfo=py7zr.helpers.UTC())
    assert dt.tzname() == "UTC"


@pytest.mark.unit
def test_utcoffset():
    dt = datetime.datetime(2019, 6, 1, 12, 13, 14, 0)
    assert py7zr.helpers.Local.utcoffset(dt) is not None


@pytest.mark.unit
def test_dst():
    dt = datetime.datetime(2019, 6, 1, 12, 13, 14, 0)
    dst = py7zr.helpers.Local.dst(dt)
    assert dst == datetime.timedelta(0) or dst == datetime.timedelta(hours=1)


@pytest.mark.unit
def test_localtime_tzname():
    dt = datetime.datetime(2019, 6, 1, 12, 13, 14, 0)
    assert py7zr.helpers.Local.tzname(dt) is not None


@pytest.mark.unit
def test_read_crcs():
    """Unit test for read_crcs()"""
    buf = io.BytesIO()
    data0 = 1024
    data1 = 32
    data2 = 1372678730
    buf.write(struct.pack("<L", data0))
    buf.write(struct.pack("<L", data1))
    buf.write(struct.pack("<L", data2))
    buf.seek(0)
    crcs = py7zr.archiveinfo.read_crcs(buf, 3)
    assert crcs[0] == data0
    assert crcs[1] == data1
    assert crcs[2] == data2


@pytest.mark.unit
def test_fileinfo_st_fmt():
    file_info = {}
    file_info["attributes"] = FILE_ATTRIBUTE_UNIX_EXTENSION
    file = py7zr.py7zr.ArchiveFile(0, file_info)
    assert file.st_fmt == 0
    file_info["attributes"] = 0
    file = py7zr.py7zr.ArchiveFile(0, file_info)
    assert file.st_fmt is None


@pytest.mark.unit
def test_wrong_mode():
    with pytest.raises(ValueError):
        py7zr.SevenZipFile(os.path.join(testdata_path, "test_1.7z"), "z")


@pytest.mark.unit
def test_calculate_crc32():
    test_data = b"\x12\x11\x12\x11"
    expected = 3572816238
    assert py7zr.helpers.calculate_crc32(test_data) == expected


@pytest.mark.unit
def test_calculate_crc32_blocksize():
    test_data = open(os.path.join(testdata_path, "test_1.7z"), "rb").read()
    expected = 0x3B04C652
    assert py7zr.helpers.calculate_crc32(test_data, value=0, blocksize=128) == expected


@pytest.mark.unit
def test_startheader_calccrc():
    startheader = py7zr.archiveinfo.SignatureHeader()
    startheader.version = (0, 4)
    startheader.nextheaderofs = 0x000000A0
    startheader.nextheadersize = 0x00000021
    # set test data to buffer that start with Property.ENCODED_HEADER
    header_data = (
        b"\x17\x060\x01\tp\x00\x07\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00"
        b"\x00\x10\x00\x0c\x80\x9d\n\x01\xe5\xa1\xb7b\x00\x00"
    )
    header_crc = py7zr.helpers.calculate_crc32(header_data)
    startheader.calccrc(len(header_data), header_crc)
    assert startheader.nextheadercrc == 0xBFE4B8B9
    assert startheader.startheadercrc == 0x37B72A70


@pytest.mark.unit
def test_write_signature_header():
    startheader = py7zr.archiveinfo.SignatureHeader()
    startheader.nextheaderofs = 0x000000A0
    startheader.nextheadersize = 0x00000021
    header_data = (
        b"\x17\x060\x01\tp\x00\x07\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00"
        b"\x00\x10\x00\x0c\x80\x9d\n\x01\xe5\xa1\xb7b\x00\x00"
    )
    header_crc = py7zr.helpers.calculate_crc32(header_data)
    startheader.calccrc(len(header_data), header_crc)
    file = io.BytesIO()
    startheader.write(file)
    val = file.getvalue()
    assert val.startswith(py7zr.properties.MAGIC_7Z)
    exp_ver = b"\x00\x04"
    exp_scrc = b"\x70\x2a\xb7\x37"
    exp_ofs = b"\xa0\x00\x00\x00\x00\x00\x00\x00"
    exp_size = b"\x21\x00\x00\x00\x00\x00\x00\x00"
    exp_hcrc = b"\xb9\xb8\xe4\xbf"
    assert val == py7zr.properties.MAGIC_7Z + exp_ver + exp_scrc + exp_ofs + exp_size + exp_hcrc


@pytest.mark.unit
def test_make_file_info1():
    file_info = py7zr.py7zr.SevenZipFile._make_file_info(
        pathlib.Path(os.path.join(testdata_path, "src", "bra.txt")), "src/bra.txt"
    )
    assert file_info.get("filename") == "src/bra.txt"
    assert not file_info.get("emptystream")
    assert file_info.get("uncompressed") == 11


@pytest.mark.unit
def test_make_file_info2():
    file_info = py7zr.py7zr.SevenZipFile._make_file_info(pathlib.Path(testdata_path).joinpath("src"))
    assert file_info.get("filename") == pathlib.Path(testdata_path).joinpath("src").as_posix()
    assert file_info.get("emptystream")
    flag = stat.FILE_ATTRIBUTE_DIRECTORY
    assert file_info.get("attributes") & flag == flag


@pytest.mark.unit
def test_simple_compress_and_decompress():
    filters = [
        {"id": lzma.FILTER_LZMA2, "preset": 7 | lzma.PRESET_DEFAULT},
    ]
    lzc = py7zr.compressor.SevenZipCompressor(filters=filters)
    outbuf = io.BytesIO()
    _, _, _ = lzc.compress(io.BytesIO(b"Some data\n"), outbuf)
    _, _, _ = lzc.compress(io.BytesIO(b"Another piece of data\n"), outbuf)
    _, _, _ = lzc.compress(io.BytesIO(b"Even more data\n"), outbuf)
    _ = lzc.flush(outbuf)
    result = outbuf.getvalue()
    size = len(result)
    #
    filters = lzc.filters
    decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
    out5 = decompressor.decompress(result)
    assert out5 == b"Some data\nAnother piece of data\nEven more data\n"
    #
    coders = lzc.coders
    crc = py7zr.helpers.calculate_crc32(result)
    decompressor = py7zr.compressor.SevenZipDecompressor(coders, size, [len(out5)], crc)
    outbuf.seek(0, 0)
    out6 = decompressor.decompress(outbuf)
    assert out6 == b"Some data\nAnother piece of data\nEven more data\n"


@pytest.mark.unit
def test_sevenzipcompressor_default():
    plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
    plain_data += plain_data
    indata = io.BytesIO(plain_data)
    outdata = io.BytesIO()
    compressor = py7zr.compressor.SevenZipCompressor(filters=None)
    _, _, _ = compressor.compress(indata, outdata)
    _ = compressor.flush(outdata)
    assert len(outdata.getvalue()) > 1


@pytest.mark.unit
@pytest.mark.parametrize(
    "password, cycle, salt, expected",
    [
        (
            "secret^&",
            0x3F,
            b"i@#ri#Ildajfdk",
            b"i@#ri#Ildajfdks\x00e\x00c\x00r\x00e\x00t\x00^\x00&\x00\x00\x00",
        ),
        (
            "secret",
            5,
            b"",
            b'(6\xa7\xf0\xcc"\t\x9dod\xe2\x8d\xd2\xe9\x08^s\x9c\x99-\xa3N\x08\x10' b"\x9e\\~\x89<\x1cR\xc2",
        ),
    ],
)
def test_calculate_key1(password: str, cycle: int, salt: bytes, expected: bytes):
    key = py7zr.helpers._calculate_key1(password.encode("utf-16LE"), cycle, salt, "sha256")
    assert key == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "password, cycle, salt, expected",
    [
        (
            "secret^&",
            0x3F,
            b"i@#ri#Ildajfdk",
            b"i@#ri#Ildajfdks\x00e\x00c\x00r\x00e\x00t\x00^\x00&\x00\x00\x00",
        )
    ],
)
def test_calculate_key2(password: str, cycle: int, salt: bytes, expected: bytes):
    key = py7zr.helpers._calculate_key2(password.encode("utf-16LE"), cycle, salt, "sha256")
    assert key == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "password, cycle, salt, expected",
    [
        (
            "secret^&",
            0x3F,
            b"i@#ri#Ildajfdk",
            b"i@#ri#Ildajfdks\x00e\x00c\x00r\x00e\x00t\x00^\x00&\x00\x00\x00",
        ),
        (
            "secret",
            5,
            b"",
            b'(6\xa7\xf0\xcc"\t\x9dod\xe2\x8d\xd2\xe9\x08^s\x9c\x99-\xa3N\x08\x10' b"\x9e\\~\x89<\x1cR\xc2",
        ),
    ],
)
def test_calculate_key3(password: str, cycle: int, salt: bytes, expected: bytes):
    key = py7zr.helpers._calculate_key3(password.encode("utf-16LE"), cycle, salt, "sha256")
    assert key == expected


def test_calculate_key1_nohash():
    with pytest.raises(ValueError):
        py7zr.helpers._calculate_key1("secret".encode("utf-16LE"), 16, b"", "sha123")


def test_calculate_key2_nohash():
    with pytest.raises(ValueError):
        py7zr.helpers._calculate_key2("secret".encode("utf-16LE"), 16, b"", "sha123")


def test_calculate_key3_nohash():
    with pytest.raises(ValueError):
        py7zr.helpers._calculate_key3("secret".encode("utf-16LE"), 16, b"", "sha123")


@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires python3.7")
@pytest.mark.skipif(sys.version_info > (3, 7), reason="requires python3.7")
@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
def test_helpers_readlink_dirfd(tmp_path):
    origin = tmp_path / "parent" / "original.txt"
    origin.parent.mkdir(parents=True, exist_ok=True)
    with origin.open("w") as f:
        f.write("Original")
    slink = tmp_path / "target" / "link"
    slink.parent.mkdir(parents=True, exist_ok=True)
    target = pathlib.Path("../parent/original.txt")
    slink.symlink_to(target, False)
    dirfd = os.open(str(origin.parent), os.O_RDONLY | os.O_DIRECTORY)
    assert py7zr.helpers.readlink(slink, dir_fd=dirfd) == target
    os.close(dirfd)


@pytest.mark.unit
def test_compressor_lzma2bcj(tmp_path):
    my_filters = [{"id": py7zr.FILTER_X86}, {"id": py7zr.FILTER_LZMA2, "preset": 7}]
    plain_data = b"\x00*\x1a\t'd\x19\xb08s\xca\x8b\x13 \xaf:\x1b\x8d\x97\xf8|#M\xe9\xe1W\xd4\xe4\x97BB\xd2"
    plain_data += plain_data
    indata = io.BytesIO(plain_data)
    outdata = io.BytesIO()
    compressor = py7zr.compressor.SevenZipCompressor(filters=my_filters)
    _, _, _ = compressor.compress(indata, outdata)
    _ = compressor.flush(outdata)
    unpacksizes = compressor.unpacksizes
    outdata.seek(0, 0)
    coders = [
        {"method": b"!", "properties": b"\x18", "numinstreams": 1, "numoutstreams": 1},
        {"method": b"\x03\x03\x01\x03", "numinstreams": 1, "numoutstreams": 1},
    ]
    decompressor = py7zr.compressor.SevenZipDecompressor(
        coders=coders, packsize=len(plain_data), unpacksizes=unpacksizes, crc=None
    )
    revert_data = decompressor.decompress(outdata, max_length=len(plain_data))
    assert revert_data == plain_data


@pytest.mark.unit
def test_lzmadecompressor_lzmabcj():
    indata = b"This file is located in the root."
    compressor = lzma.LZMACompressor(
        format=lzma.FORMAT_RAW,
        filters=[{"id": lzma.FILTER_X86}, {"id": lzma.FILTER_LZMA1}],
    )
    compressed = compressor.compress(indata)
    compressed += compressor.flush()
    decompressor = lzma.LZMADecompressor(
        format=lzma.FORMAT_RAW,
        filters=[{"id": lzma.FILTER_X86}, {"id": lzma.FILTER_LZMA1}],
    )
    outdata = decompressor.decompress(data=compressed)
    assert outdata == indata


@pytest.mark.unit
def test_unit_buffer():
    buf = py7zr.helpers.Buffer(size=16)
    buf.add(b"12345")
    assert len(buf) == 5
    assert buf.get() == bytearray(b"12345")
    buf.add(b"67890")
    assert buf.view == bytearray(b"67890")
    assert bytes(buf) == b"67890"
    buf.reset()
    assert buf.get() == bytearray(b"")


@pytest.mark.unit
def test_supported_method_is_crypto_id():
    assert py7zr.compressor.SupportedMethods.is_crypto_id(py7zr.properties.FILTER_CRYPTO_AES256_SHA256)


@pytest.mark.unit
def test_supported_method_get_method_id():
    id = py7zr.compressor.SupportedMethods.get_method_id(py7zr.properties.FILTER_CRYPTO_AES256_SHA256)
    assert id == py7zr.properties.CompressionMethod.CRYPT_AES256_SHA256


@pytest.mark.unit
def test_bcj_encode(tmp_path):
    with open(os.path.join(testdata_path, "x86.bin"), "rb") as f:
        filter = py7zr.compressor.BCJEncoder()
        m = hashlib.sha256()
        with tmp_path.joinpath("target.bin").open("wb") as fo:
            data = f.read(8192)
            while len(data) > 0:
                odata = filter.compress(data)
                m.update(odata)
                fo.write(odata)
                data = f.read(8192)
            odata = filter.flush()
            m.update(odata)
            fo.write(odata)
        assert m.digest() == binascii.unhexlify("e396dadbbe0be4190cdea986e0ec949b049ded2b38df19268a78d32b90b72d42")


@pytest.mark.unit
def test_bcj_decode(tmp_path):
    with open(os.path.join(testdata_path, "bcj.bin"), "rb") as f:
        filter = py7zr.compressor.BCJDecoder(12800)
        m = hashlib.sha256()
        data = f.read(8192)
        while len(data) > 0:
            m.update(filter.decompress(data))
            data = f.read(8192)
        assert m.digest() == binascii.unhexlify("5ae0726746e2ccdad8f511ecfcf5f79df4533b83f86b1877cebc07f14a4e9b6a")
