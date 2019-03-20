import os
import pytest
from io import StringIO
import py7zr
from py7zr.tests import utils


testdata_path = os.path.join(os.path.dirname(__file__), 'data')

def test_list_1():
    archive = py7zr.Archive(open(os.path.join(testdata_path,'test_1.7z'), 'rb'))
    output = StringIO()
    archive.list(file=output)
    contents = output.getvalue()
    expected = """total 3 files in solid archive
       111       441 b36aaedb scripts/py7zr
        58       441 dcbf8d07 setup.cfg
       559       441 80fc72be setup.py
"""
    assert expected == contents

def test_list_2():
    archive = py7zr.Archive(open(os.path.join(testdata_path,'test_3.7z'), 'rb'))
    output = StringIO()
    archive.list(file=output)
    contents = output.getvalue()
    expected = """total 18 files in solid archive
        26      8472 f7c93fe5 5.9.7/gcc_64/include/QtX11Extras/QX11Info
       176      8472 06cfbb1d 5.9.7/gcc_64/include/QtX11Extras/QtX11Extras
       201      8472 f29d7597 5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasDepends
        32      8472 77d26efb 5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasVersion
       722      8472 e646f1b8 5.9.7/gcc_64/lib/libQt5X11Extras.la
      2280      8472 8c8cdf40 5.9.7/gcc_64/include/QtX11Extras/qtx11extrasglobal.h
       222      8472 76db1fa8 5.9.7/gcc_64/include/QtX11Extras/qtx11extrasversion.h
      2890      8472 cd86f14b 5.9.7/gcc_64/include/QtX11Extras/qx11info_x11.h
        24      8472 7f892e04 5.9.7/gcc_64/lib/libQt5X11Extras.so
        24      8472 7f892e04 5.9.7/gcc_64/lib/libQt5X11Extras.so.5
     14568      8472 a383b739 5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9.7
        24      8472 7f892e04 5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9
      6704      8472 a17e4b91 5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfig.cmake
       287      8472 0afe3467 5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfigVersion.cmake
       283      8472 2d8d94d9 5.9.7/gcc_64/lib/pkgconfig/Qt5X11Extras.pc
       555      8472 9a79d3b6 5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras.pri
       526      8472 283bb2f8 5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras_private.pri
      1064      8472 80ffd5c9 5.9.7/gcc_64/lib/libQt5X11Extras.prl
"""
    assert expected == contents


def test_extract_1():
    archive = py7zr.Archive(open(os.path.join(testdata_path,'test_1.7z'), 'rb'))
    archive.extract_all(dest='/tmp/py7zr-test')
    with open(os.path.join(testdata_path, "test_1/setup.cfg")) as expected:
        with open("/tmp/py7zr-test/setup.cfg", "r") as f:
            assert expected.read() == f.read()

def test_extract_2():
    archive = py7zr.Archive(open(os.path.join(testdata_path,'test_2.7z'), 'rb'))
    archive.extract_all(dest='/tmp/py7zr-test')
    with open(os.path.join(testdata_path,"test_2/qt.qt5.597.gcc_64/installscript.qs")) as expected:
        with open("/tmp/py7zr-test/qt.qt5.597.gcc_64/installscript.qs", "r") as f:
            assert expected.read() == f.read()

@pytest.mark.xfail(reason="Uknown issue")
def test_decode_4():
    archive = py7zr.Archive(open(os.path.join(testdata_path,'test_4.7z'), 'rb'))
    utils.decode_all(archive)

