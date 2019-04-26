import binascii
import hashlib
import io
import os
from io import StringIO
import lzma
import py7zr
from py7zr import archiveinfo, is_7zfile
from py7zr.properties import Property
from py7zr.tests import decode_all
import pytest
import shutil
import tempfile
import time


testdata_path = os.path.join(os.path.dirname(__file__), 'data')
os.environ['TZ'] = 'Asia/Tokyo'
if os.name == 'posix':
    time.tzset()


@pytest.mark.basic
def test_basic_initinfo():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    assert archive is not None


@pytest.mark.basic
def test_basic_list_1():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    output = StringIO()
    archive.list(file=output)
    contents = output.getvalue()
    expected = """total 4 files and directories in solid archive
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
2019-03-14 09:10:08 D....            0            0  scripts
2019-03-14 09:10:08 ....A          111          441  scripts/py7zr
2019-03-14 09:07:13 ....A           58          441  setup.cfg
2019-03-14 09:09:01 ....A          559          441  setup.py
------------------- ----- ------------ ------------  ------------------------
"""
    assert expected == contents


@pytest.mark.basic
def test_basic_list_2():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_3.7z'), 'rb'))
    output = StringIO()
    archive.list(file=output)
    contents = output.getvalue()
    expected = """total 28 files and directories in solid archive
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
2018-10-18 23:52:42 D....            0            0  5.9.7
2018-10-18 23:52:43 D....            0            0  5.9.7/gcc_64
2018-10-18 23:52:42 D....            0            0  5.9.7/gcc_64/include
2018-10-18 23:52:42 D....            0            0  5.9.7/gcc_64/include/QtX11Extras
2018-10-18 23:52:42 D....            0            0  5.9.7/gcc_64/lib
2018-10-18 23:52:42 D....            0            0  5.9.7/gcc_64/lib/cmake
2018-10-18 23:52:42 D....            0            0  5.9.7/gcc_64/lib/cmake/Qt5X11Extras
2018-10-18 23:52:42 D....            0            0  5.9.7/gcc_64/lib/pkgconfig
2018-10-18 23:52:42 D....            0            0  5.9.7/gcc_64/mkspecs
2018-10-18 23:52:42 D....            0            0  5.9.7/gcc_64/mkspecs/modules
2018-10-16 19:26:21 ....A           26         8472  5.9.7/gcc_64/include/QtX11Extras/QX11Info
2018-10-16 19:26:24 ....A          176         8472  5.9.7/gcc_64/include/QtX11Extras/QtX11Extras
2018-10-16 19:26:24 ....A          201         8472  5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasDepends
2018-10-16 19:26:24 ....A           32         8472  5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasVersion
2018-10-16 19:26:27 ....A          722         8472  5.9.7/gcc_64/lib/libQt5X11Extras.la
2018-10-16 19:26:21 ....A         2280         8472  5.9.7/gcc_64/include/QtX11Extras/qtx11extrasglobal.h
2018-10-16 19:26:24 ....A          222         8472  5.9.7/gcc_64/include/QtX11Extras/qtx11extrasversion.h
2018-10-16 19:26:21 ....A         2890         8472  5.9.7/gcc_64/include/QtX11Extras/qx11info_x11.h
2018-10-18 23:52:42 ....A           24         8472  5.9.7/gcc_64/lib/libQt5X11Extras.so
2018-10-18 23:52:42 ....A           24         8472  5.9.7/gcc_64/lib/libQt5X11Extras.so.5
2018-10-16 19:26:27 ....A        14568         8472  5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9.7
2018-10-18 23:52:42 ....A           24         8472  5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9
2018-10-16 19:26:24 ....A         6704         8472  5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfig.cmake
2018-10-16 19:26:24 ....A          287         8472  5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfigVersion.cmake
2018-10-16 19:26:27 ....A          283         8472  5.9.7/gcc_64/lib/pkgconfig/Qt5X11Extras.pc
2018-10-16 19:26:24 ....A          555         8472  5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras.pri
2018-10-16 19:26:24 ....A          526         8472  5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras_private.pri
2018-10-18 19:28:16 ....A         1064         8472  5.9.7/gcc_64/lib/libQt5X11Extras.prl
------------------- ----- ------------ ------------  ------------------------
"""
    assert expected == contents


@pytest.mark.basic
def test_basic_decode_1():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    decode_all(archive)


@pytest.mark.basic
def test_basic_decode_2():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_2.7z'), 'rb'))
    decode_all(archive)


@pytest.mark.basic
def test_basic_extract_1():
    tmpdir = tempfile.mkdtemp()
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    archive.extractall(path=tmpdir)
    target = os.path.join(tmpdir, "setup.cfg")
    expected_mode = 33188
    expected_mtime = 1552522033
    assert os.stat(target).st_mode == expected_mode
    assert os.stat(target).st_mtime == expected_mtime
    m = hashlib.sha256()
    m.update(open(target, 'rb').read())
    assert m.digest() == binascii.unhexlify('ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240')
    m = hashlib.sha256()
    m.update(open(os.path.join(tmpdir, 'setup.py'), 'rb').read())
    assert m.digest() == binascii.unhexlify('b916eed2a4ee4e48c51a2b51d07d450de0be4dbb83d20e67f6fd166ff7921e49')
    m = hashlib.sha256()
    m.update(open(os.path.join(tmpdir, 'scripts/py7zr'), 'rb').read())
    assert m.digest() == binascii.unhexlify('b0385e71d6a07eb692f5fb9798e9d33aaf87be7dfff936fd2473eab2a593d4fd')
    shutil.rmtree(tmpdir)


@pytest.mark.basic
def test_basic_extract_2():
    tmpdir = tempfile.mkdtemp()
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_2.7z'), 'rb'))
    archive.extractall(path=tmpdir)
    m = hashlib.sha256()
    m.update(open(os.path.join(tmpdir, 'qt.qt5.597.gcc_64/installscript.qs'), 'rb').read())
    assert m.digest() == binascii.unhexlify('39445276e79ea43c0fa8b393b35dc621fcb2045cb82238ddf2b838a4fbf8a587')
    shutil.rmtree(tmpdir)


@pytest.mark.unit
def test_py7zr_signatureheader():
    header_data = io.BytesIO(b'\x37\x7a\xbc\xaf\x27\x1c\x00\x02\x70\x2a\xb7\x37\xa0\x00\x00\x00\x00\x00\x00\x00\x21'
                             b'\x00\x00\x00\x00\x00\x00\x00\xb9\xb8\xe4\xbf')
    header = archiveinfo.SignatureHeader(header_data)
    assert header is not None
    assert header.version == (0, 2)
    assert header.nextheaderofs == 160


@pytest.mark.unit
def test_py7zr_mainstreams():
    header_data = io.BytesIO(b'\x04\x06\x00\x01\t0\x00\x07\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00\x00\x00\x02\x0cB\x00'
                             b'\x08\r\x02\t!\n\x01>jb\x08\xce\x9a\xb7\x88\x00\x00')
    pid = header_data.read(1)
    assert pid == Property.MAIN_STREAMS_INFO
    streams = archiveinfo.StreamsInfo(header_data)
    assert streams is not None


@pytest.mark.unit
def test_py7zr_header():
    fp = open(os.path.join(testdata_path, 'solid.7z'), 'rb')
    header_data = io.BytesIO(b'\x01'
                             b'\x04\x06\x00\x01\t0\x00\x07\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00\x00\x00\x02\x0cB\x00'
                             b'\x08\r\x02\t!\n\x01>jb\x08\xce\x9a\xb7\x88\x00\x00'
                             b'\x05\x03\x0e\x01\x80\x11=\x00t\x00e\x00s\x00t\x00\x00\x00t\x00e\x00s\x00t\x001\x00.'
                             b'\x00t\x00x\x00t\x00\x00\x00t\x00e\x00s\x00t\x00/\x00t\x00e\x00s\x00t\x002\x00.\x00t\x00x'
                             b'\x00t\x00\x00\x00\x14\x1a\x01\x00\x04>\xe6\x0f{H\xc6\x01d\xca \x8byH\xc6\x01\x8c\xfa\xb6'
                             b'\x83yH\xc6\x01\x15\x0e\x01\x00\x10\x00\x00\x00 \x00\x00\x00 \x00\x00\x00\x00\x00')
    header = archiveinfo.Header(fp, header_data, start_pos=32)
    assert header is not None
    assert header.files_info is not None
    assert header.main_streams is not None
    assert header.files_info.numfiles == 3
    assert len(header.files_info.files) == header.files_info.numfiles


@pytest.mark.unit
def test_py7zr_encoded_header():
    fp = open(os.path.join(testdata_path, 'test_5.7z'), 'rb')
    # set test data to buffer that start with Property.ENCODED_HEADER
    buffer = io.BytesIO(b'\x17\x060\x01\tp\x00\x07\x0b\x01\x00\x01#\x03\x01\x01\x05]\x00'
                        b'\x00\x10\x00\x0c\x80\x9d\n\x01\xe5\xa1\xb7b\x00\x00')
    header = archiveinfo.Header(fp, buffer, start_pos=32)
    assert header is not None
    assert header.files_info is not None
    assert header.main_streams is not None
    assert header.files_info.numfiles == 3
    assert len(header.files_info.files) == header.files_info.numfiles


@pytest.mark.unit
def test_py7zr_files_info():
    header_data = io.BytesIO(b'\x05\x03\x0e\x01\x80\x11=\x00t\x00e\x00s\x00t\x00\x00\x00t\x00e\x00s\x00t\x001\x00.'
                             b'\x00t\x00x\x00t\x00\x00\x00t\x00e\x00s\x00t\x00/\x00t\x00e\x00s\x00t\x002\x00.\x00t\x00x'
                             b'\x00t\x00\x00\x00\x14\x1a\x01\x00\x04>\xe6\x0f{H\xc6\x01d\xca \x8byH\xc6\x01\x8c\xfa\xb6'
                             b'\x83yH\xc6\x01\x15\x0e\x01\x00\x10\x00\x00\x00 \x00\x00\x00 \x00\x00\x00\x00\x00')
    pid = header_data.read(1)
    assert pid == Property.FILES_INFO
    files_info = archiveinfo.FilesInfo(header_data)
    assert files_info is not None
    assert files_info.files[0].get('filename') == 'test'
    assert files_info.files[1].get('filename') == 'test1.txt'
    assert files_info.files[2].get('filename') == 'test/test2.txt'


@pytest.mark.unit
def test_py7zr_files_info2():
    header_data = io.BytesIO(b'\x05\x04\x11_\x00c\x00o\x00p\x00y\x00i\x00n\x00g\x00.\x00t\x00x\x00t\x00\x00\x00H\x00'
                             b'i\x00s\x00t\x00o\x00r\x00y\x00.\x00t\x00x\x00t\x00\x00\x00L\x00i\x00c\x00e\x00n\x00s'
                             b'\x00e\x00.\x00t\x00x\x00t\x00\x00\x00r\x00e\x00a\x00d\x00m\x00e\x00.\x00t\x00x\x00t\x00'
                             b'\x00\x00\x14"\x01\x00\x00[\x17\xe6\xc70\xc1\x01\x00Vh\xb5\xda\xf8\xc5\x01\x00\x97\xbd'
                             b'\xf9\x07\xf7\xc4\x01\x00gK\xa8\xda\xf8\xc5\x01\x15\x12\x01\x00  \x00\x00  \x00'
                             b'\x00  \x00\x00  \x00\x00\x00\x00')
    pid = header_data.read(1)
    assert pid == Property.FILES_INFO
    files_info = archiveinfo.FilesInfo(header_data)
    assert files_info is not None
    assert files_info.numfiles == 4
    assert files_info.files[0].get('filename') == 'copying.txt'
    assert files_info.files[0].get('attributes') == 0x2020
    assert files_info.files[1].get('filename') == 'History.txt'
    assert files_info.files[1].get('attributes') == 0x2020
    assert files_info.files[2].get('filename') == 'License.txt'
    assert files_info.files[2].get('attributes') == 0x2020
    assert files_info.files[3].get('filename') == 'readme.txt'
    assert files_info.files[3].get('attributes') == 0x2020


@pytest.mark.unit
def test_py7zr_is_7zfile():
    assert is_7zfile(os.path.join(testdata_path, 'test_1.7z'))


@pytest.mark.unit
def test_lzma_lzma2_compressor():
    filters = [{'id': 33, 'dict_size': 16777216}]
    assert lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters) is not None


@pytest.mark.unit
def test_lzma_lzma2bcj_compressor():
    filters = [{'id': 4}, {'id': 33, 'dict_size': 16777216}]
    assert lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters) is not None
