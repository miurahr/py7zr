import io
import os
import shutil
import tempfile
import time

import py7zr
import py7zr.archiveinfo
import py7zr.cli
import py7zr.compression
import pytest

from . import check_output, decode_all

testdata_path = os.path.join(os.path.dirname(__file__), 'data')
os.environ['TZ'] = 'UTC'
if os.name == 'posix':
    time.tzset()
os.umask(0o022)


@pytest.mark.basic
def test_basic_initinfo():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    assert archive is not None


@pytest.mark.basic
def test_basic_list_1():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    output = io.StringIO()
    archive.list(file=output)
    contents = output.getvalue()
    expected = """total 4 files and directories in solid archive
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
2019-03-14 00:10:08 D....            0            0  scripts
2019-03-14 00:10:08 ....A          111          441  scripts/py7zr
2019-03-14 00:07:13 ....A           58          441  setup.cfg
2019-03-14 00:09:01 ....A          559          441  setup.py
------------------- ----- ------------ ------------  ------------------------
"""
    assert expected == contents


@pytest.mark.basic
def test_basic_list_2():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_3.7z'), 'rb'))
    output = io.StringIO()
    archive.list(file=output)
    contents = output.getvalue()
    expected = """total 28 files and directories in solid archive
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
2018-10-18 14:52:42 D....            0            0  5.9.7
2018-10-18 14:52:43 D....            0            0  5.9.7/gcc_64
2018-10-18 14:52:42 D....            0            0  5.9.7/gcc_64/include
2018-10-18 14:52:42 D....            0            0  5.9.7/gcc_64/include/QtX11Extras
2018-10-18 14:52:42 D....            0            0  5.9.7/gcc_64/lib
2018-10-18 14:52:42 D....            0            0  5.9.7/gcc_64/lib/cmake
2018-10-18 14:52:42 D....            0            0  5.9.7/gcc_64/lib/cmake/Qt5X11Extras
2018-10-18 14:52:42 D....            0            0  5.9.7/gcc_64/lib/pkgconfig
2018-10-18 14:52:42 D....            0            0  5.9.7/gcc_64/mkspecs
2018-10-18 14:52:42 D....            0            0  5.9.7/gcc_64/mkspecs/modules
2018-10-16 10:26:21 ....A           26         8472  5.9.7/gcc_64/include/QtX11Extras/QX11Info
2018-10-16 10:26:24 ....A          176         8472  5.9.7/gcc_64/include/QtX11Extras/QtX11Extras
2018-10-16 10:26:24 ....A          201         8472  5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasDepends
2018-10-16 10:26:24 ....A           32         8472  5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasVersion
2018-10-16 10:26:27 ....A          722         8472  5.9.7/gcc_64/lib/libQt5X11Extras.la
2018-10-16 10:26:21 ....A         2280         8472  5.9.7/gcc_64/include/QtX11Extras/qtx11extrasglobal.h
2018-10-16 10:26:24 ....A          222         8472  5.9.7/gcc_64/include/QtX11Extras/qtx11extrasversion.h
2018-10-16 10:26:21 ....A         2890         8472  5.9.7/gcc_64/include/QtX11Extras/qx11info_x11.h
2018-10-18 14:52:42 ....A           24         8472  5.9.7/gcc_64/lib/libQt5X11Extras.so
2018-10-18 14:52:42 ....A           24         8472  5.9.7/gcc_64/lib/libQt5X11Extras.so.5
2018-10-16 10:26:27 ....A        14568         8472  5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9.7
2018-10-18 14:52:42 ....A           24         8472  5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9
2018-10-16 10:26:24 ....A         6704         8472  5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfig.cmake
2018-10-16 10:26:24 ....A          287         8472  5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfigVersion.cmake
2018-10-16 10:26:27 ....A          283         8472  5.9.7/gcc_64/lib/pkgconfig/Qt5X11Extras.pc
2018-10-16 10:26:24 ....A          555         8472  5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras.pri
2018-10-16 10:26:24 ....A          526         8472  5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras_private.pri
2018-10-18 10:28:16 ....A         1064         8472  5.9.7/gcc_64/lib/libQt5X11Extras.prl
------------------- ----- ------------ ------------  ------------------------
"""
    assert expected == contents


@pytest.mark.api
def test_basic_not_implemented_yet1():
    tmpdir = tempfile.mkdtemp()
    with pytest.raises(NotImplementedError):
        py7zr.SevenZipFile(os.path.join(tmpdir, 'test_x.7z'), mode='x')
    shutil.rmtree(tmpdir)


@pytest.mark.api
def test_write_mode():
    tmpdir = tempfile.mkdtemp()
    py7zr.SevenZipFile(os.path.join(tmpdir, 'test_w.7z'), mode='w')
    shutil.rmtree(tmpdir)


@pytest.mark.api
def test_basic_not_implemented_yet3():
    tmpdir = tempfile.mkdtemp()
    with pytest.raises(NotImplementedError):
        py7zr.SevenZipFile(os.path.join(tmpdir, 'test_a.7z'), mode='a')
    shutil.rmtree(tmpdir)


@pytest.mark.api
def test_basic_wrong_option_value():
    tmpdir = tempfile.mkdtemp()
    with pytest.raises(ValueError):
        py7zr.SevenZipFile(os.path.join(tmpdir, 'test_p.7z'), mode='p')
    shutil.rmtree(tmpdir)


@pytest.mark.basic
def test_basic_extract_1():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    expected = [{'filename': 'setup.cfg', 'mode': 33188, 'mtime': 1552522033,
                 'digest': 'ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240'},
                {'filename': 'setup.py', 'mode': 33188, 'mtime': 1552522141,
                 'digest': 'b916eed2a4ee4e48c51a2b51d07d450de0be4dbb83d20e67f6fd166ff7921e49'},
                {'filename': 'scripts/py7zr', 'mode': 33261, 'mtime': 1552522208,
                'digest': 'b0385e71d6a07eb692f5fb9798e9d33aaf87be7dfff936fd2473eab2a593d4fd'}
                ]
    decode_all(archive, expected)


@pytest.mark.basic
def test_basic_extract_2():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_2.7z'), 'rb'))
    expected = [{'filename': 'qt.qt5.597.gcc_64/installscript.qs',
                 'digest': '39445276e79ea43c0fa8b393b35dc621fcb2045cb82238ddf2b838a4fbf8a587'}]
    decode_all(archive, expected)


@pytest.mark.basic
def test_basic_decode_3():
    """Test when passing path string instead of file-like object."""
    archive = py7zr.SevenZipFile(os.path.join(testdata_path, 'test_1.7z'))
    expected = [{'filename': 'setup.cfg', 'mode': 33188, 'mtime': 1552522033,
                 'digest': 'ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240'}]
    decode_all(archive, expected)


@pytest.mark.api
def test_py7zr_is_7zfile():
    assert py7zr.is_7zfile(os.path.join(testdata_path, 'test_1.7z'))


@pytest.mark.api
def test_py7zr_is_7zfile_fileish():
    assert py7zr.is_7zfile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))


@pytest.mark.basic
def test_py7zr_is_not_7zfile():
    tmpdir = tempfile.mkdtemp()
    target = os.path.join(tmpdir, 'test_not.7z')
    with open(target, 'wb') as f:
        f.write(b'12345dahodjg98adfjfak;')
    assert not py7zr.is_7zfile(target)
    shutil.rmtree(tmpdir)


@pytest.mark.cli
@pytest.mark.parametrize("ops, expected", [(["-h"], "usage: py7zr [-h] {l,x,c,t}")])
def test_cli_ops(capsys, ops, expected):
    cli = py7zr.cli.Cli()
    with pytest.raises(SystemExit):
        cli.run(ops)
    out, err = capsys.readouterr()
    assert out.startswith(expected)


@pytest.mark.cli
def test_cli_list(capsys):
    arcfile = os.path.join(testdata_path, "test_1.7z")
    expected = """total 4 files and directories in solid archive
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
2019-03-14 00:10:08 D....            0            0  scripts
2019-03-14 00:10:08 ....A          111          441  scripts/py7zr
2019-03-14 00:07:13 ....A           58          441  setup.cfg
2019-03-14 00:09:01 ....A          559          441  setup.py
------------------- ----- ------------ ------------  ------------------------
"""
    cli = py7zr.cli.Cli()
    cli.run(["l", arcfile])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.api
def test_api_list_verbose(capsys):
    arcfile = os.path.join(testdata_path, "test_1.7z")
    archive = py7zr.SevenZipFile(open(arcfile, 'rb'))
    expected = """Listing archive: {}
--
Path = {}
Type = 7z
Phisical Size = 657
Headers Size = 0
Method = LZMA2
Solid = +
Blocks = 1

total 4 files and directories in solid archive
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
2019-03-14 00:10:08 D....            0            0  scripts
2019-03-14 00:10:08 ....A          111          441  scripts/py7zr
2019-03-14 00:07:13 ....A           58          441  setup.cfg
2019-03-14 00:09:01 ....A          559          441  setup.py
------------------- ----- ------------ ------------  ------------------------
""".format(arcfile, arcfile)
    output = io.StringIO()
    archive.list(file=output, verbose=True)
    out = output.getvalue()
    assert out == expected


@pytest.mark.cli
def test_cli_test(capsys):
    arcfile = os.path.join(testdata_path, 'test_2.7z')
    expected = """Testing archive: {}
--
Path = {}
Type = 7z
Phisical Size = 1663
Headers Size = 0
Method = LZMA2
Solid = +
Blocks = 1

Everything is Ok
""".format(arcfile, arcfile)
    cli = py7zr.cli.Cli()
    cli.run(["t", arcfile])
    out, err = capsys.readouterr()
    assert expected == out


@pytest.mark.cli
def test_cli_extract():
    arcfile = os.path.join(testdata_path, "test_1.7z")
    tmpdir = tempfile.mkdtemp()
    cli = py7zr.cli.Cli()
    cli.run(["x", arcfile, tmpdir])
    expected = [{'filename': 'setup.cfg', 'mode': 33188, 'mtime': 1552522033,
                 'digest': 'ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240'},
                {'filename': 'setup.py', 'mode': 33188, 'mtime': 1552522141,
                 'digest': 'b916eed2a4ee4e48c51a2b51d07d450de0be4dbb83d20e67f6fd166ff7921e49'},
                {'filename': 'scripts/py7zr', 'mode': 33261, 'mtime': 1552522208,
                 'digest': 'b0385e71d6a07eb692f5fb9798e9d33aaf87be7dfff936fd2473eab2a593d4fd'}
                ]
    check_output(expected, tmpdir)
    shutil.rmtree(tmpdir)


@pytest.mark.basic
def test_digests():
    arcfile = os.path.join(testdata_path, "test_2.7z")
    archive = py7zr.SevenZipFile(arcfile)
    assert archive._test_digests()
