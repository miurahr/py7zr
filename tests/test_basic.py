import lzma
import os
import sys
import time

import pytest

import py7zr
import py7zr.archiveinfo
import py7zr.cli
import py7zr.compression
import py7zr.properties

from . import check_output, decode_all

if sys.version_info < (3, 6):
    import pathlib2 as pathlib
else:
    import pathlib

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
    archive_list = archive.list()
    # TODO


@pytest.mark.cli
def test_cli_list_1(capsys):
    arc = os.path.join(testdata_path, 'test_1.7z')
    expected = """total 4 files and directories in solid archive
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
2019-03-14 00:10:08 D....            0            0  scripts
2019-03-14 00:10:08 ....A          111          441  scripts/py7zr
2019-03-14 00:07:13 ....A           58               setup.cfg
2019-03-14 00:09:01 ....A          559               setup.py
------------------- ----- ------------ ------------  ------------------------
"""
    cli = py7zr.cli.Cli()
    cli.run(["l", arc])
    out, err = capsys.readouterr()
    assert expected == out


@pytest.mark.basic
def test_cli_list_2(capsys):
    arc = os.path.join(testdata_path, 'test_3.7z')
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
2018-10-16 10:26:24 ....A          176               5.9.7/gcc_64/include/QtX11Extras/QtX11Extras
2018-10-16 10:26:24 ....A          201               5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasDepends
2018-10-16 10:26:24 ....A           32               5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasVersion
2018-10-16 10:26:27 ....A          722               5.9.7/gcc_64/lib/libQt5X11Extras.la
2018-10-16 10:26:21 ....A         2280               5.9.7/gcc_64/include/QtX11Extras/qtx11extrasglobal.h
2018-10-16 10:26:24 ....A          222               5.9.7/gcc_64/include/QtX11Extras/qtx11extrasversion.h
2018-10-16 10:26:21 ....A         2890               5.9.7/gcc_64/include/QtX11Extras/qx11info_x11.h
2018-10-18 14:52:42 ....A           24               5.9.7/gcc_64/lib/libQt5X11Extras.so
2018-10-18 14:52:42 ....A           24               5.9.7/gcc_64/lib/libQt5X11Extras.so.5
2018-10-16 10:26:27 ....A        14568               5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9.7
2018-10-18 14:52:42 ....A           24               5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9
2018-10-16 10:26:24 ....A         6704               5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfig.cmake
2018-10-16 10:26:24 ....A          287               5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfigVersion.cmake
2018-10-16 10:26:27 ....A          283               5.9.7/gcc_64/lib/pkgconfig/Qt5X11Extras.pc
2018-10-16 10:26:24 ....A          555               5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras.pri
2018-10-16 10:26:24 ....A          526               5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras_private.pri
2018-10-18 10:28:16 ....A         1064               5.9.7/gcc_64/lib/libQt5X11Extras.prl
------------------- ----- ------------ ------------  ------------------------
"""
    cli = py7zr.cli.Cli()
    cli.run(["l", arc])
    out, err = capsys.readouterr()
    assert expected == out


@pytest.mark.api
def test_basic_not_implemented_yet1(tmp_path):
    with pytest.raises(NotImplementedError):
        py7zr.SevenZipFile(tmp_path.joinpath('test_x.7z'), mode='x')


@pytest.mark.api
def test_write_mode(tmp_path):
    py7zr.SevenZipFile(tmp_path.joinpath('test_w.7z'), mode='w')


@pytest.mark.api
def test_basic_not_implemented_yet3(tmp_path):
    with tmp_path.joinpath('test_a.7z').open('w') as f:
        f.write('foo')
    with pytest.raises(NotImplementedError):
        py7zr.SevenZipFile(tmp_path.joinpath('test_a.7z'), mode='a')


@pytest.mark.api
def test_basic_wrong_option_value(tmp_path):
    with pytest.raises(ValueError):
        py7zr.SevenZipFile(tmp_path.joinpath('test_p.7z'), mode='p')


@pytest.mark.basic
def test_basic_extract_1(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    expected = [{'filename': 'setup.cfg', 'mode': 33188, 'mtime': 1552522033,
                 'digest': 'ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240'},
                {'filename': 'setup.py', 'mode': 33188, 'mtime': 1552522141,
                 'digest': 'b916eed2a4ee4e48c51a2b51d07d450de0be4dbb83d20e67f6fd166ff7921e49'},
                {'filename': 'scripts/py7zr', 'mode': 33261, 'mtime': 1552522208,
                'digest': 'b0385e71d6a07eb692f5fb9798e9d33aaf87be7dfff936fd2473eab2a593d4fd'}
                ]
    decode_all(archive, expected, tmp_path)


@pytest.mark.basic
def test_basic_extract_2(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_2.7z'), 'rb'))
    expected = [{'filename': 'qt.qt5.597.gcc_64/installscript.qs',
                 'digest': '39445276e79ea43c0fa8b393b35dc621fcb2045cb82238ddf2b838a4fbf8a587'}]
    decode_all(archive, expected, tmp_path)


@pytest.mark.basic
def test_basic_decode_3(tmp_path):
    """Test when passing path string instead of file-like object."""
    archive = py7zr.SevenZipFile(os.path.join(testdata_path, 'test_1.7z'))
    expected = [{'filename': 'setup.cfg', 'mode': 33188, 'mtime': 1552522033,
                 'digest': 'ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240'}]
    decode_all(archive, expected, tmp_path)


@pytest.mark.api
def test_py7zr_is_7zfile():
    assert py7zr.is_7zfile(os.path.join(testdata_path, 'test_1.7z'))


@pytest.mark.api
def test_py7zr_is_7zfile_fileish():
    assert py7zr.is_7zfile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))


@pytest.mark.api
def test_py7zr_is_7zfile_path():
    assert py7zr.is_7zfile(pathlib.Path(testdata_path).joinpath('test_1.7z'))


@pytest.mark.basic
def test_py7zr_is_not_7zfile(tmp_path):
    target = tmp_path.joinpath('test_not.7z')
    with target.open('wb') as f:
        f.write(b'12345dahodjg98adfjfak;')
    with target.open('rb') as f:
        assert not py7zr.is_7zfile(f)


@pytest.mark.cli
def test_cli_help(capsys):
    expected = "usage: py7zr [-h] {l,x,c,t,i}"
    cli = py7zr.cli.Cli()
    with pytest.raises(SystemExit):
        cli.run(["-h"])
    out, err = capsys.readouterr()
    assert out.startswith(expected)


@pytest.mark.cli
def test_cli_no_subcommand(capsys):
    expected = "usage: py7zr [-h] {l,x,c,t,i}"
    cli = py7zr.cli.Cli()
    cli.run([])
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
2019-03-14 00:07:13 ....A           58               setup.cfg
2019-03-14 00:09:01 ....A          559               setup.py
------------------- ----- ------------ ------------  ------------------------
"""
    cli = py7zr.cli.Cli()
    cli.run(["l", arcfile])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.cli
def test_cli_list_verbose(capsys):
    arcfile = os.path.join(testdata_path, "test_1.7z")
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
2019-03-14 00:07:13 ....A           58               setup.cfg
2019-03-14 00:09:01 ....A          559               setup.py
------------------- ----- ------------ ------------  ------------------------
""".format(arcfile, arcfile)
    cli = py7zr.cli.Cli()
    cli.run(["l", "--verbose", arcfile])
    out, err = capsys.readouterr()
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
def test_cli_info(capsys):
    if lzma.is_check_supported(lzma.CHECK_CRC64):
        check0 = "\nCHECK_CRC64"
    else:
        check0 = ""
    if lzma.is_check_supported(lzma.CHECK_SHA256):
        check1 = "\nCHECK_SHA256"
    else:
        check1 = ""
    expected_checks = """Checks:
CHECK_NONE
CHECK_CRC32{}{}""".format(check0, check1)
    expected = """py7zr version {} {}
Formats:
7z    37 7a bc af 27 1c

Codecs:
030101      LZMA
21         LZMA2
03         DELTA
03030103     BCJ
03030205     PPC
03030401    IA64
03030501     ARM
03030701    ARMT
03030805   SPARC

{}
""".format(py7zr.__version__, py7zr.__copyright__, expected_checks)
    cli = py7zr.cli.Cli()
    cli.run(["i"])
    out, err = capsys.readouterr()
    assert expected == out


@pytest.mark.cli
def test_cli_extract(tmp_path):
    arcfile = os.path.join(testdata_path, "test_1.7z")
    cli = py7zr.cli.Cli()
    cli.run(["x", arcfile, str(tmp_path.resolve())])
    expected = [{'filename': 'setup.cfg', 'mode': 33188, 'mtime': 1552522033,
                 'digest': 'ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240'},
                {'filename': 'setup.py', 'mode': 33188, 'mtime': 1552522141,
                 'digest': 'b916eed2a4ee4e48c51a2b51d07d450de0be4dbb83d20e67f6fd166ff7921e49'},
                {'filename': 'scripts/py7zr', 'mode': 33261, 'mtime': 1552522208,
                 'digest': 'b0385e71d6a07eb692f5fb9798e9d33aaf87be7dfff936fd2473eab2a593d4fd'}
                ]
    check_output(expected, tmp_path)


@pytest.mark.basic
def test_digests():
    arcfile = os.path.join(testdata_path, "test_2.7z")
    archive = py7zr.SevenZipFile(arcfile)
    assert archive._test_digests()


@pytest.mark.cli
def test_non7z_ext(capsys, tmp_path):
    expected = "not a 7z file\n"
    arcfile = os.path.join(testdata_path, "test_1.txt")
    cli = py7zr.cli.Cli()
    cli.run(["x", arcfile, str(tmp_path.resolve())])
    out, err = capsys.readouterr()
    assert expected == out


@pytest.mark.cli
def test_non7z_test(capsys):
    expected = "not a 7z file\n"
    arcfile = os.path.join(testdata_path, "test_1.txt")
    cli = py7zr.cli.Cli()
    cli.run(["t", arcfile])
    out, err = capsys.readouterr()
    assert expected == out


@pytest.mark.cli
def test_non7z_list(capsys):
    expected = "not a 7z file\n"
    arcfile = os.path.join(testdata_path, "test_1.txt")
    cli = py7zr.cli.Cli()
    cli.run(["l", arcfile])
    out, err = capsys.readouterr()
    assert expected == out


@pytest.mark.unit
def test_py7zr_write_mode(tmp_path):
    target = tmp_path.joinpath('target.7z')
    archive = py7zr.SevenZipFile(target, 'w')
    archive.write(os.path.join(testdata_path, "test1.txt"), "test1.txt")
    assert archive.files is not None
    assert len(archive.files) == 1
    for f in archive.files:
        assert f.filename in ('test1.txt')
        assert not f.emptystream


@pytest.mark.api
def test_py7zr_writeall_single(tmp_path):
    target = tmp_path.joinpath('target.7z')
    archive = py7zr.SevenZipFile(target, 'w')
    archive.writeall(os.path.join(testdata_path, "test1.txt"), "test1.txt")
    assert archive.files is not None
    assert len(archive.files) == 1
    for f in archive.files:
        assert f.filename in ('test1.txt')
        assert not f.emptystream


@pytest.mark.api
def test_py7zr_writeall_dir(tmp_path):
    target = tmp_path.joinpath('target.7z')
    archive = py7zr.SevenZipFile(target, 'w')
    archive.writeall(os.path.join(testdata_path, "src"), "src")
    assert archive.files is not None
    assert len(archive.files) == 2
    for f in archive.files:
        assert f.filename in ('src', os.path.join('src', 'bra.txt'))
