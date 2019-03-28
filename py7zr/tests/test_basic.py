import os
from io import StringIO
import py7zr
from py7zr.tests import utils
import shutil
import tempfile

testdata_path = os.path.join(os.path.dirname(__file__), 'data')


def test_initinfo():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    assert archive != None


def test_list_1():
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


def test_list_2():
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


def test_decode_1():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    utils.decode_all(archive)


def test_decode_2():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_2.7z'), 'rb'))
    utils.decode_all(archive)


def test_extract_1():
    tmpdir = tempfile.mkdtemp()
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    archive.extractall(path=tmpdir)
    with open(os.path.join(testdata_path, "test_1/setup.cfg")) as expected:
        with open(os.path.join(tmpdir, "setup.cfg"), "r") as f:
            assert f.read() == expected.read()
    shutil.rmtree(tmpdir)


def test_extract_2():
    tmpdir = tempfile.mkdtemp()
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_2.7z'), 'rb'))
    archive.extractall(path=tmpdir)
    with open(os.path.join(testdata_path, "test_2/qt.qt5.597.gcc_64/installscript.qs")) as expected:
        with open(os.path.join(tmpdir, "qt.qt5.597.gcc_64/installscript.qs"), "r") as f:
            assert expected.read() == f.read()
    shutil.rmtree(tmpdir)
