import getpass
import lzma
import os
import re
import sys

import pytest

import py7zr
import py7zr.archiveinfo
import py7zr.callbacks
import py7zr.cli
import py7zr.compression
import py7zr.properties

from . import check_output, decode_all, ltime2

if sys.version_info < (3, 6):
    import pathlib2 as pathlib
else:
    import pathlib

testdata_path = os.path.join(os.path.dirname(__file__), 'data')
os.umask(0o022)


@pytest.mark.basic
def test_basic_initinfo():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    assert archive is not None


@pytest.mark.cli
def test_cli_list_1(capsys):
    arc = os.path.join(testdata_path, 'test_1.7z')
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


@pytest.mark.basic
def test_cli_list_2(capsys):
    arc = os.path.join(testdata_path, 'test_3.7z')
    expected = "total 28 files and directories in solid archive\n"
    expected += "   Date      Time    Attr         Size   Compressed  Name\n"
    expected += "------------------- ----- ------------ ------------  ------------------------\n"
    expected += "{} D....            0            0  5.9.7\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64\n".format(ltime2(2018, 10, 18, 14, 52, 43))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/include\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/include/QtX11Extras\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/lib\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/lib/cmake\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/lib/cmake/Qt5X11Extras\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/lib/pkgconfig\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/mkspecs\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} D....            0            0  5.9.7/gcc_64/mkspecs/modules\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} ....A           26         8472  5.9.7/gcc_64/include/QtX11Extras/QX11Info\n".format(ltime2(2018, 10, 16, 10, 26, 21))  # noqa: E501
    expected += "{} ....A          176               5.9.7/gcc_64/include/QtX11Extras/QtX11Extras\n".format(ltime2(2018, 10, 16, 10, 26, 24))  # noqa: E501
    expected += "{} ....A          201               5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasDepends\n".format(ltime2(2018, 10, 16, 10, 26, 24))  # noqa: E501
    expected += "{} ....A           32               5.9.7/gcc_64/include/QtX11Extras/QtX11ExtrasVersion\n".format(ltime2(2018, 10, 16, 10, 26, 24))  # noqa: E501
    expected += "{} ....A          722               5.9.7/gcc_64/lib/libQt5X11Extras.la\n".format(ltime2(2018, 10, 16, 10, 26, 27))  # noqa: E501
    expected += "{} ....A         2280               5.9.7/gcc_64/include/QtX11Extras/qtx11extrasglobal.h\n".format(ltime2(2018, 10, 16, 10, 26, 21))  # noqa: E501
    expected += "{} ....A          222               5.9.7/gcc_64/include/QtX11Extras/qtx11extrasversion.h\n".format(ltime2(2018, 10, 16, 10, 26, 24))  # noqa: E501
    expected += "{} ....A         2890               5.9.7/gcc_64/include/QtX11Extras/qx11info_x11.h\n".format(ltime2(2018, 10, 16, 10, 26, 21))  # noqa: E501
    expected += "{} ....A           24               5.9.7/gcc_64/lib/libQt5X11Extras.so\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} ....A           24               5.9.7/gcc_64/lib/libQt5X11Extras.so.5\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} ....A        14568               5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9.7\n".format(ltime2(2018, 10, 16, 10, 26, 27))  # noqa: E501
    expected += "{} ....A           24               5.9.7/gcc_64/lib/libQt5X11Extras.so.5.9\n".format(ltime2(2018, 10, 18, 14, 52, 42))  # noqa: E501
    expected += "{} ....A         6704               5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfig.cmake\n".format(ltime2(2018, 10, 16, 10, 26, 24))  # noqa: E501
    expected += "{} ....A          287               5.9.7/gcc_64/lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfigVersion.cmake\n".format(ltime2(2018, 10, 16, 10, 26, 24))  # noqa: E501
    expected += "{} ....A          283               5.9.7/gcc_64/lib/pkgconfig/Qt5X11Extras.pc\n".format(ltime2(2018, 10, 16, 10, 26, 27))  # noqa: E501
    expected += "{} ....A          555               5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras.pri\n".format(ltime2(2018, 10, 16, 10, 26, 24))  # noqa: E501
    expected += "{} ....A          526               5.9.7/gcc_64/mkspecs/modules/qt_lib_x11extras_private.pri\n".format(ltime2(2018, 10, 16, 10, 26, 24))  # noqa: E501
    expected += "{} ....A         1064               5.9.7/gcc_64/lib/libQt5X11Extras.prl\n".format(ltime2(2018, 10, 18, 10, 28, 16))  # noqa: E501
    expected += "------------------- ----- ------------ ------------  ------------------------\n"
    cli = py7zr.cli.Cli()
    cli.run(["l", arc])
    out, err = capsys.readouterr()
    assert out == expected


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
""".format(arcfile, arcfile)
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
    arcfile = os.path.join(testdata_path, 'test_2.7z')
    expected = """Testing archive: {}
--
Path = {}
Type = 7z
Phisical Size = 1663
Headers Size = 0
Method = LZMA2
Solid = -
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


@pytest.mark.cli
def test_cli_encrypted_extract(monkeypatch, tmp_path):

    def _getpasswd():
        return 'secret'

    monkeypatch.setattr(getpass, "getpass", _getpasswd)

    arcfile = os.path.join(testdata_path, "encrypted_1.7z")
    cli = py7zr.cli.Cli()
    cli.run(["x", "--password", arcfile, str(tmp_path.resolve())])
    expected = [{'filename': 'test1.txt', 'mode': 33188,
                 'digest': '0f16b2f4c3a74b9257cd6229c0b7b91855b3260327ef0a42ecf59c44d065c5b2'},
                {'filename': 'test/test2.txt', 'mode': 33188,
                 'digest': '1d0d28682fca74c5912ea7e3f6878ccfdb6e4e249b161994b7f2870e6649ef09'}
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
    tmp_path.joinpath('src').mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, 'test_1.7z'), path=tmp_path.joinpath('src'))
    target = str(tmp_path / "target.7z")
    source = str(tmp_path / 'src')
    cli = py7zr.cli.Cli()
    cli.run(['c', target, source])
    out, err = capsys.readouterr()


@pytest.mark.cli
def test_archive_already_exist(tmp_path, capsys):
    expected = 'Archive file exists!\n'
    py7zr.unpack_7zarchive(os.path.join(testdata_path, 'test_1.7z'), path=tmp_path.joinpath('src'))
    target = tmp_path / "target.7z"
    with target.open('w') as f:
        f.write('Already exist!')
    source = str(tmp_path / 'src')
    cli = py7zr.cli.Cli()
    with pytest.raises(SystemExit):
        cli.run(['c', str(target), source])
    out, err = capsys.readouterr()
    assert err == expected


@pytest.mark.cli
def test_archive_without_extension(tmp_path, capsys):
    py7zr.unpack_7zarchive(os.path.join(testdata_path, 'test_1.7z'), path=tmp_path.joinpath('src'))
    target = str(tmp_path / "target")
    source = str(tmp_path / 'src')
    cli = py7zr.cli.Cli()
    cli.run(['c', target, source])
    expected_target = tmp_path / "target.7z"
    assert expected_target.exists()


@pytest.mark.cli
@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires python3.6 or higher")
def test_volume_creation(tmp_path, capsys):
    tmp_path.joinpath('src').mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, 'lzma2bcj.7z'), path=tmp_path.joinpath('src'))
    target = str(tmp_path / "target.7z")
    source = str(tmp_path / 'src')
    cli = py7zr.cli.Cli()
    cli.run(['c', target, source, '-v', '2m'])
    out, err = capsys.readouterr()


@pytest.mark.cli
@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires python3.6 or higher")
def test_volume_creation_wrong_volume_unit(tmp_path, capsys):
    expected = 'Error: Specified volume size is invalid.\n'
    target = str(tmp_path / "target.7z")
    source = tmp_path / 'src'
    source.mkdir()
    cli = py7zr.cli.Cli()
    with pytest.raises(SystemExit):
        cli.run(['c', target, str(source), '-v', '2P'])
    out, err = capsys.readouterr()
    assert err == expected


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
        assert f.filename in ('src', 'src/bra.txt')
    archive._fpclose()


@pytest.mark.api
def test_py7zr_extract_specified_file(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    expected = [{'filename': 'scripts/py7zr', 'mode': 33261, 'mtime': 1552522208,
                'digest': 'b0385e71d6a07eb692f5fb9798e9d33aaf87be7dfff936fd2473eab2a593d4fd'}
                ]
    archive.extract(path=tmp_path, targets=['scripts', 'scripts/py7zr'])
    archive.close()
    assert tmp_path.joinpath('scripts').is_dir()
    assert tmp_path.joinpath('scripts/py7zr').exists()
    assert not tmp_path.joinpath('setup.cfg').exists()
    assert not tmp_path.joinpath('setup.py').exists()
    check_output(expected, tmp_path)


@pytest.mark.api
def test_py7zr_extract_and_getnames(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    allfiles = archive.getnames()
    filter_pattern = re.compile(r'scripts.*')
    targets = []
    for f in allfiles:
        if filter_pattern.match(f):
            targets.append(f)
    archive.extract(path=tmp_path, targets=targets)
    archive.close()
    assert tmp_path.joinpath('scripts').is_dir()
    assert tmp_path.joinpath('scripts/py7zr').exists()
    assert not tmp_path.joinpath('setup.cfg').exists()
    assert not tmp_path.joinpath('setup.py').exists()


@pytest.mark.api
def test_py7zr_extract_and_reset_iteration(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    iterations = archive.getnames()
    for target in iterations:
        archive.extract(path=tmp_path, targets=[target])
        archive.reset()
    archive.close()
    assert tmp_path.joinpath('scripts').is_dir()
    assert tmp_path.joinpath('scripts/py7zr').exists()
    assert tmp_path.joinpath('setup.cfg').exists()
    assert tmp_path.joinpath('setup.py').exists()


@pytest.mark.api
def test_context_manager_1(tmp_path):
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'test_1.7z'), 'r') as z:
        z.extractall(path=tmp_path)
    assert tmp_path.joinpath('scripts').is_dir()
    assert tmp_path.joinpath('scripts/py7zr').exists()
    assert tmp_path.joinpath('setup.cfg').exists()
    assert tmp_path.joinpath('setup.py').exists()


@pytest.mark.api
def test_context_manager_2(tmp_path):
    target = tmp_path.joinpath('target.7z')
    with py7zr.SevenZipFile(target, 'w') as z:
        z.writeall(os.path.join(testdata_path, "src"), "src")


@pytest.mark.api
def test_extract_callback(tmp_path):

    class ECB(py7zr.callbacks.ExtractCallback):

        def __init__(self, ofd):
            self.ofd = ofd

        def report_start_preparation(self):
            self.ofd.write('preparation.\n')

        def report_start(self, processing_file_path, processing_bytes):
            self.ofd.write('start \"{}\" (compressed in {} bytes)\n'.format(processing_file_path, processing_bytes))

        def report_end(self, processing_file_path, wrote_bytes):
            self.ofd.write('end \"{}\" extracted to {} bytes\n'.format(processing_file_path, wrote_bytes))

        def report_postprocess(self):
            self.ofd.write('post processing.\n')

        def report_warning(self, message):
            self.ofd.write('warning: {:s}\n'.format(message))

    cb = ECB(sys.stdout)
    with py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb')) as archive:
        archive.extractall(path=tmp_path, callback=cb)
