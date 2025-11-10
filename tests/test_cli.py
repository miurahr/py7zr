import getpass
import lzma
import os
import shutil
import sys

import pytest

import py7zr
import py7zr.archiveinfo
import py7zr.callbacks
import py7zr.cli
import py7zr.properties

from . import check_output, libarchive_extract, ltime2, p7zip_test

testdata_path = os.path.join(os.path.dirname(__file__), "data")
os.umask(0o022)


@pytest.mark.cli
def test_cli_list_1(capsys):
    arc = os.path.join(testdata_path, "test_1.7z")
    expected = """total 4 files and directories in solid archive
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
"""
    expected += "{} D....            0            0  scripts\n".format(ltime2(2019, 3, 14, 0, 10, 8))
    expected += "{} ....A          111          441  scripts/py7zr\n".format(ltime2(2019, 3, 14, 0, 10, 8))
    expected += "{} ....A           58               setup.cfg\n".format(ltime2(2019, 3, 14, 0, 7, 13))
    expected += "{} ....A          559               setup.py\n".format(ltime2(2019, 3, 14, 0, 9, 1))
    expected += "------------------- ----- ------------ ------------  ------------------------\n"
    cli = py7zr.cli.Cli()
    cli.run(["l", arc])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.cli
def test_cli_list_2(capsys):
    arc = os.path.join(testdata_path, "test_3.7z")
    expected = "total 28 files and directories in solid archive\n"
    expected += "   Date      Time    Attr         Size   Compressed  Name\n"
    expected += "------------------- ----- ------------ ------------  ------------------------\n"
    expected += "{} D....            0            0  5.9.7\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64\n".format(ltime2(2018, 10, 18, 14, 52, 43))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/include\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/include/QtX11Extras\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/lib\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/lib/cmake\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/lib/cmake/Qt5X11Extras\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/lib/pkgconfig\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/mkspecs\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/mkspecs/modules\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} ....A           26         8472  5.9.7/gcc_64/include/QtX11Extras/QX11Info\n".format(
        ltime2(2018, 10, 16, 10, 26, 21)
    )  # noqa: E501
    expected += "{} ....A          176               5.9.7/gcc_64/include/QtX11Extras/QtX11Extras\n".format(
        ltime2(2018, 10, 16, 10, 26, 24)
    )  # noqa: E501
    expected += "{} ....A          201               5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasDepends\n".format(
        ltime2(2018, 10, 16, 10, 26, 24)
    )  # noqa: E501
    expected += "{} ....A           32               5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasVersion\n".format(
        ltime2(2018, 10, 16, 10, 26, 24)
    )  # noqa: E501
    expected += "{} ....A          722               5.9.7/gcc_64/lib/libQt5X11Extras.la\n".format(
        ltime2(2018, 10, 16, 10, 26, 27)
    )  # noqa: E501
    expected += "{} ....A         2280               5.9.7/gcc_64/include/QtX11Extras/qtx11extrasglobal.h\n".format(
        ltime2(2018, 10, 16, 10, 26, 21)
    )  # noqa: E501
    expected += "{} ....A          222               5.9.7/gcc_64/include/QtX11Extras/qtx11extrasversion.h\n".format(
        ltime2(2018, 10, 16, 10, 26, 24)
    )  # noqa: E501
    expected += "{} ....A         2890               5.9.7/gcc_64/include/QtX11Extras/qx11info_x11.h\n".format(
        ltime2(2018, 10, 16, 10, 26, 21)
    )  # noqa: E501
    expected += "{} ....A           24               5.9.7/gcc_64/lib/libQt5X11Extras.so\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} ....A           24               5.9.7/gcc_64/lib/libQt5X11Extras.so.5\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} ....A        14568               5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9.7\n".format(
        ltime2(2018, 10, 16, 10, 26, 27)
    )  # noqa: E501
    expected += "{} ....A           24               5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9\n".format(
        ltime2(2018, 10, 18, 14, 52, 42)
    )  # noqa: E501
    expected += "{} ....A         6704               5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfig.cmake\n".format(
        ltime2(2018, 10, 16, 10, 26, 24)
    )  # noqa: E501
    expected += (
        "{} ....A          287               5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfigVersion.cmake\n".format(
            ltime2(2018, 10, 16, 10, 26, 24)
        )
    )  # noqa: E501
    expected += "{} ....A          283               5.9.7/gcc_64/lib/pkgconfig/Qt5X11Extras.pc\n".format(
        ltime2(2018, 10, 16, 10, 26, 27)
    )  # noqa: E501
    expected += "{} ....A          555               5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras.pri\n".format(
        ltime2(2018, 10, 16, 10, 26, 24)
    )  # noqa: E501
    expected += "{} ....A          526               5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras_private.pri\n".format(
        ltime2(2018, 10, 16, 10, 26, 24)
    )  # noqa: E501
    expected += "{} ....A         1064               5.9.7/gcc_64/lib/libQt5X11Extras.prl\n".format(
        ltime2(2018, 10, 18, 10, 28, 16)
    )  # noqa: E501
    expected += "------------------- ----- ------------ ------------  ------------------------\n"
    cli = py7zr.cli.Cli()
    cli.run(["l", arc])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.cli
def test_cli_help(capsys):
    if sys.version_info >= (3, 10):
        expected = "usage: py7zr [-h] [--version] {l,x,c,a,t,i} ...\n\npy7zr\n\noptions:"
    else:
        expected = "usage: py7zr [-h] [--version] {l,x,c,a,t," "i} ...\n\npy7zr\n\noptional arguments:\n  -h, --help"
    cli = py7zr.cli.Cli()
    with pytest.raises(SystemExit):
        cli.run(["-h"])
    out, err = capsys.readouterr()
    assert out.startswith(expected)


@pytest.mark.cli
def test_cli_no_subcommand(capsys):
    expected = py7zr.cli.Cli._get_version()
    if sys.version_info >= (3, 10):
        expected += "\nusage: py7zr [-h] [--version] {l,x,c,a,t,i} ...\n\npy7zr\n\noptions:"
    else:
        expected += "\nusage: py7zr [-h] [--version] {l,x,c,a,t,i} ...\n\npy7zr\n\noptional arguments:\n  -h, --help"
    cli = py7zr.cli.Cli()
    cli.run([])
    out, err = capsys.readouterr()
    assert out.startswith(expected)


@pytest.mark.cli
def test_cli_list_verbose(capsys):
    arcfile = os.path.join(testdata_path, "test_1.7z")
    expected = """Listing archive: {}
--
Path = {}
Type = 7z
Physical Size = 657
Headers Size = 216
Method = LZMA2
Solid = +
Blocks = 1

total 4 files and directories in solid archive
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
""".format(
        arcfile, arcfile
    )
    expected += "{} D....            0            0  scripts\n".format(ltime2(2019, 3, 14, 0, 10, 8))
    expected += "{} ....A          111          441  scripts/py7zr\n".format(ltime2(2019, 3, 14, 0, 10, 8))
    expected += "{} ....A           58               setup.cfg\n".format(ltime2(2019, 3, 14, 0, 7, 13))
    expected += "{} ....A          559               setup.py\n".format(ltime2(2019, 3, 14, 0, 9, 1))
    expected += "------------------- ----- ------------ ------------  ------------------------\n"
    cli = py7zr.cli.Cli()
    cli.run(["l", "--verbose", arcfile])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.cli
def test_cli_test(capsys):
    arcfile = os.path.join(testdata_path, "test_2.7z")
    expected = """Testing archive: {}
--
Path = {}
Type = 7z
Physical Size = 1663
Headers Size = 203
Method = LZMA2
Solid = -
Blocks = 1

Everything is Ok
""".format(
        arcfile, arcfile
    )
    cli = py7zr.cli.Cli()
    cli.run(["t", arcfile])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.cli
def test_cli_info(capsys):
    expected = py7zr.cli.Cli._get_version()
    if lzma.is_check_supported(lzma.CHECK_CRC64):
        check0 = "\n0              CRC64"
    else:
        check0 = ""
    if lzma.is_check_supported(lzma.CHECK_SHA256):
        check1 = "\n0             SHA256"
    else:
        check1 = ""
    expected_checks = """0              CRC32{}{}""".format(check1, check0)
    expected += """\n
Formats:
7z    37 7a bc af 27 1c

Codecs and hashes:
00              COPY
21             LZMA2
03             DELTA
030101          LZMA
03030103         BCJ
03030205         PPC
03030401        IA64
03030501         ARM
03030701        ARMT
03030805       SPARC
040108       DEFLATE
040202         BZip2
04f71101   ZStandard
030401          PPMd
04f71102      Brotli
040109     DEFLATE64
06f10701       7zAES
{}
""".format(
        expected_checks
    )
    cli = py7zr.cli.Cli()
    cli.run(["i"])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.cli
def test_cli_extract(tmp_path):
    arcfile = os.path.join(testdata_path, "test_1.7z")
    cli = py7zr.cli.Cli()
    cli.run(["x", arcfile, str(tmp_path.resolve())])
    expected = [
        {
            "filename": "setup.cfg",
            "mode": 33188,
            "mtime": 1552522033,
            "digest": "ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240",
        },
        {
            "filename": "setup.py",
            "mode": 33188,
            "mtime": 1552522141,
            "digest": "b916eed2a4ee4e48c51a2b51d07d450de0be4dbb83d20e67f6fd166ff7921e49",
        },
        {
            "filename": "scripts/py7zr",
            "mode": 33261,
            "mtime": 1552522208,
            "digest": "b0385e71d6a07eb692f5fb9798e9d33aaf87be7dfff936fd2473eab2a593d4fd",
        },
    ]
    check_output(expected, tmp_path)


@pytest.mark.cli
def test_cli_extract_member(tmp_path):
    arcfile = os.path.join(testdata_path, "test_1.7z")
    cli = py7zr.cli.Cli()
    cli.run(["x", arcfile, str(tmp_path.resolve()), "--files", "setup.cfg"])
    expected = [
        {
            "filename": "setup.cfg",
            "mode": 33188,
            "mtime": 1552522033,
            "digest": "ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240",
        },
    ]
    check_output(expected, tmp_path)


@pytest.mark.cli
def test_cli_encrypted_extract(monkeypatch, tmp_path):
    def _getpasswd():
        return "secret"

    monkeypatch.setattr(getpass, "getpass", _getpasswd)

    arcfile = os.path.join(testdata_path, "encrypted_1.7z")
    cli = py7zr.cli.Cli()
    cli.run(["x", "--password", arcfile, str(tmp_path.resolve())])
    expected = [
        {
            "filename": "test1.txt",
            "mode": 33188,
            "digest": "0f16b2f4c3a74b9257cd6229c0b7b91855b3260327ef0a42ecf59c44d065c5b2",
        },
        {
            "filename": "test/test2.txt",
            "mode": 33188,
            "digest": "1d0d28682fca74c5912ea7e3f6878ccfdb6e4e249b161994b7f2870e6649ef09",
        },
    ]
    check_output(expected, tmp_path)


@pytest.mark.cli
def test_cli_encrypted_wrong_password(monkeypatch, tmp_path, capsys):
    def _getpasswd():
        return "badsecret"

    monkeypatch.setattr(getpass, "getpass", _getpasswd)

    expected = "The archive is corrupted, or password is wrong. ABORT.\n"

    arcfile = os.path.join(testdata_path, "encrypted_1.7z")
    cli = py7zr.cli.Cli()
    result = cli.run(["x", "--password", arcfile, str(tmp_path.resolve())])
    out, err = capsys.readouterr()
    assert result == 1
    assert out == expected


@pytest.mark.cli
@pytest.mark.skipif(sys.hexversion == 0x030900F0, reason="bpo-42057")
def test_cli_encrypted_zero_length_password(monkeypatch, tmp_path, capsys):
    def _getpasswd():
        return ""

    monkeypatch.setattr(getpass, "getpass", _getpasswd)

    expected = "The archive is corrupted, or password is wrong. ABORT.\n"

    arcfile = os.path.join(testdata_path, "encrypted_1.7z")
    cli = py7zr.cli.Cli()
    result = cli.run(["x", "--password", arcfile, str(tmp_path.resolve())])
    out, err = capsys.readouterr()
    assert result == 1
    assert out == expected


@pytest.mark.cli
def test_non7z_ext(capsys, tmp_path):
    expected = "not a 7z file\n"
    arcfile = os.path.join(testdata_path, "test_1.txt")
    cli = py7zr.cli.Cli()
    cli.run(["x", arcfile, str(tmp_path.resolve())])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.cli
def test_non7z_test(capsys):
    expected = "not a 7z file\n"
    arcfile = os.path.join(testdata_path, "test_1.txt")
    cli = py7zr.cli.Cli()
    cli.run(["t", arcfile])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.cli
def test_non7z_list(capsys):
    expected = "not a 7z file\n"
    arcfile = os.path.join(testdata_path, "test_1.txt")
    cli = py7zr.cli.Cli()
    cli.run(["l", arcfile])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.cli
def test_archive_creation(tmp_path, capsys):
    expected = ""
    tmp_path.joinpath("src").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    os.chdir(str(tmp_path))
    target = "target.7z"
    source = "src"
    cli = py7zr.cli.Cli()
    cli.run(["c", target, source])
    out, err = capsys.readouterr()
    assert out == expected
    #
    p7zip_test(tmp_path / "target.7z")
    libarchive_extract(tmp_path / "target.7z", tmp_path.joinpath("tgt2"))


@pytest.mark.cli
@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires python3.7 or higher")
def test_archive_already_exist(tmp_path, capsys):
    expected = "Archive file exists!\n"
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    target = tmp_path / "target.7z"
    with target.open("w") as f:
        f.write("Already exist!")
    source = str(tmp_path / "src")
    cli = py7zr.cli.Cli()
    with pytest.raises(SystemExit):
        cli.run(["c", str(target), source])
    out, err = capsys.readouterr()
    assert err == expected


@pytest.mark.cli
def test_archive_append(tmp_path, capsys):
    expected = ""
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_2.7z"), path=tmp_path.joinpath("src"))
    target = tmp_path / "target.7z"
    shutil.copy(os.path.join(testdata_path, "test_1.7z"), target)
    source = str(tmp_path / "src")
    cli = py7zr.cli.Cli()
    cli.run(["a", str(target), source])
    out, err = capsys.readouterr()
    assert err == expected
    #
    p7zip_test(tmp_path / "target.7z")
    libarchive_extract(tmp_path / "target.7z", tmp_path.joinpath("tgt2"))


@pytest.mark.cli
def test_archive_without_extension(tmp_path, capsys):
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    target = str(tmp_path / "target")
    source = str(tmp_path / "src")
    cli = py7zr.cli.Cli()
    cli.run(["c", target, source])
    expected_target = tmp_path / "target.7z"
    assert expected_target.exists()


@pytest.mark.cli
@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires python3.7 or higher")
def test_volume_creation(tmp_path, capsys):
    expected = ""
    tmp_path.joinpath("src").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "lzma2bcj.7z"), path=tmp_path.joinpath("src"))
    target = str(tmp_path / "target.7z")
    source = str(tmp_path / "src")
    cli = py7zr.cli.Cli()
    cli.run(["c", target, source, "-v", "2m"])
    out, err = capsys.readouterr()
    assert out == expected
    assert err == expected


@pytest.mark.cli
@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires python3.7 or higher")
def test_volume_creation_wrong_volume_unit(tmp_path, capsys):
    expected = "Error: Specified volume size is invalid.\n"
    target = str(tmp_path / "target.7z")
    source = tmp_path / "src"
    source.mkdir()
    cli = py7zr.cli.Cli()
    with pytest.raises(SystemExit):
        cli.run(["c", target, str(source), "-v", "2P"])
    out, err = capsys.readouterr()
    assert err == expected


@pytest.mark.cli
@pytest.mark.files
def test_list_multivolume(capsys):
    arcfile = os.path.join(testdata_path, "archive.7z.001")
    basefile = os.path.join(testdata_path, "archive.7z")
    expected = """Listing archive: {}
--
Path = {}
Type = 7z
Physical Size = 52337
Headers Size = 518
Method = LZMA2, BCJ
Solid = +
Blocks = 2

total 19 files and directories in solid archive
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
""".format(
        basefile, basefile
    )
    expected += "{} D....            0            0  mingw64\n".format(ltime2(2017, 1, 23, 6, 2, 46))
    expected += "{} D....            0            0  mingw64/bin\n".format(ltime2(2020, 6, 7, 2, 45, 18))
    expected += "{} D....            0            0  mingw64/include\n".format(ltime2(2020, 6, 7, 2, 45, 18))
    expected += "{} D....            0            0  mingw64/lib\n".format(ltime2(2020, 6, 7, 2, 45, 18))
    expected += "{} D....            0            0  mingw64/share\n".format(ltime2(2020, 6, 7, 2, 45, 26))
    expected += "{} D....            0            0  mingw64/share/doc\n".format(ltime2(2017, 1, 23, 6, 2, 43))
    expected += "{} D....            0            0  mingw64/share/doc/szip\n".format(ltime2(2017, 1, 23, 6, 2, 43))
    expected += "{} ....A         2289        26895  mingw64/include/SZconfig.h\n".format(ltime2(2017, 1, 23, 6, 2, 34))
    expected += "{} ....A         3470               mingw64/include/ricehdf.h\n".format(ltime2(2004, 3, 16, 16, 14, 27))
    expected += "{} ....A         1774               mingw64/include/szip_adpt.h\n".format(ltime2(2010, 7, 2, 21, 31, 38))
    expected += "{} ....A         5282               mingw64/include/szlib.h\n".format(ltime2(2008, 11, 11, 16, 12, 56))
    expected += "{} ....A        60008               mingw64/lib/libszip.a\n".format(ltime2(2017, 1, 23, 6, 2, 47))
    expected += "{} ....A        10900               mingw64/lib/libszip.dll.a\n".format(ltime2(2017, 1, 23, 6, 2, 39))
    expected += "{} ....A         1986               mingw64/share/doc/szip/COPYING\n".format(ltime2(2008, 1, 24, 23, 8, 43))
    expected += "{} ....A         1544               mingw64/share/doc/szip/HISTORY.txt\n".format(
        ltime2(2010, 7, 14, 13, 43, 15)
    )
    expected += "{} ....A         3544               mingw64/share/doc/szip/INSTALL\n".format(
        ltime2(2008, 11, 11, 16, 12, 56)
    )
    expected += "{} ....A          564               mingw64/share/doc/szip/README\n".format(ltime2(2007, 8, 20, 18, 47, 21))
    expected += "{} ....A          513               mingw64/share/doc/szip/RELEASE.txt\n".format(
        ltime2(2010, 7, 14, 13, 43, 15)
    )
    expected += "{} ....A        66352        24924  mingw64/bin/libszip-0.dll\n".format(ltime2(2017, 1, 23, 6, 2, 47))
    expected += "------------------- ----- ------------ ------------  ------------------------\n"
    cli = py7zr.cli.Cli()
    cli.run(["l", "--verbose", arcfile])
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.cli
def test_cli_encrypted_no_password(capsys):
    arcfile = os.path.join(testdata_path, "encrypted_1.7z")
    expected = """Testing archive: {}
--
Path = {}
Type = 7z
Physical Size = 251
Headers Size = 203
Method = LZMA, 7zAES
Solid = +
Blocks = 1

The archive is encrypted but password is not given. FAILED.
""".format(
        arcfile, arcfile
    )
    cli = py7zr.cli.Cli()
    cli.run(["t", arcfile])
    out, err = capsys.readouterr()
    assert out == expected
