import os
import pathlib
import re
import shutil

import pytest

import py7zr
import py7zr.archiveinfo
import py7zr.callbacks
import py7zr.cli
import py7zr.properties

from . import check_output, decode_all

testdata_path = os.path.join(os.path.dirname(__file__), "data")
os.umask(0o022)


@pytest.mark.basic
def test_basic_initinfo():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, "test_1.7z"), "rb"))
    assert archive is not None


@pytest.mark.api
def test_basic_not_implemented_yet1(tmp_path):
    with pytest.raises(NotImplementedError):
        py7zr.SevenZipFile(tmp_path.joinpath("test_x.7z"), mode="x")


@pytest.mark.api
def test_basic_append_mode(tmp_path):
    target = tmp_path.joinpath("test_a.7z")
    shutil.copy(os.path.join(testdata_path, "test_1.7z"), target)
    with py7zr.SevenZipFile(target, mode="a") as archive:
        archive.write(os.path.join(testdata_path, "test1.txt"), "test1.txt")


@pytest.mark.api
def test_basic_wrong_option_value(tmp_path):
    with pytest.raises(ValueError):
        py7zr.SevenZipFile(tmp_path.joinpath("test_p.7z"), mode="p")


@pytest.mark.basic
def test_basic_extract_1(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, "test_1.7z"), "rb"))
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
    decode_all(archive, expected, tmp_path)


@pytest.mark.basic
def test_basic_extract_2(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, "test_2.7z"), "rb"))
    expected = [
        {
            "filename": "qt.qt5.597.gcc_64/installscript.qs",
            "digest": "39445276e79ea43c0fa8b393b35dc621fcb2045cb82238ddf2b838a4fbf8a587",
        }
    ]
    decode_all(archive, expected, tmp_path)


@pytest.mark.basic
def test_basic_decode_3(tmp_path):
    """Test when passing path string instead of file-like object."""
    archive = py7zr.SevenZipFile(os.path.join(testdata_path, "test_1.7z"))
    expected = [
        {
            "filename": "setup.cfg",
            "mode": 33188,
            "mtime": 1552522033,
            "digest": "ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240",
        }
    ]
    decode_all(archive, expected, tmp_path)


@pytest.mark.api
def test_py7zr_is_7zfile():
    assert py7zr.is_7zfile(os.path.join(testdata_path, "test_1.7z"))


@pytest.mark.api
def test_py7zr_is_7zfile_fileish():
    assert py7zr.is_7zfile(open(os.path.join(testdata_path, "test_1.7z"), "rb"))


@pytest.mark.api
def test_py7zr_is_7zfile_path():
    assert py7zr.is_7zfile(pathlib.Path(testdata_path).joinpath("test_1.7z"))


@pytest.mark.basic
def test_py7zr_is_not_7zfile(tmp_path):
    target = tmp_path.joinpath("test_not.7z")
    with target.open("wb") as f:
        f.write(b"12345dahodjg98adfjfak;")
    with target.open("rb") as f:
        assert not py7zr.is_7zfile(f)


@pytest.mark.basic
def test_digests():
    arcfile = os.path.join(testdata_path, "test_2.7z")
    archive = py7zr.SevenZipFile(arcfile)
    assert archive.test() is None
    assert archive.testzip() is None


@pytest.mark.basic
def test_digests_corrupted():
    arcfile = os.path.join(testdata_path, "crc_corrupted.7z")
    with py7zr.SevenZipFile(arcfile) as archive:
        assert archive.test() is None
        archive.reset()
        assert archive.testzip() == "src/scripts/py7zr"


@pytest.mark.unit
def test_py7zr_write_mode(tmp_path):
    target = tmp_path.joinpath("target.7z")
    archive = py7zr.SevenZipFile(target, "w")
    archive.write(os.path.join(testdata_path, "test1.txt"), "test1.txt")
    assert archive.files is not None
    assert len(archive.files) == 1
    for f in archive.files:
        assert f.filename in ("test1.txt")
        assert not f.emptystream


@pytest.mark.api
def test_py7zr_writeall_single(tmp_path):
    target = tmp_path.joinpath("target.7z")
    archive = py7zr.SevenZipFile(target, "w")
    archive.writeall(os.path.join(testdata_path, "test1.txt"), "test1.txt")
    assert archive.files is not None
    assert len(archive.files) == 1
    for f in archive.files:
        assert f.filename in ("test1.txt")
        assert not f.emptystream


@pytest.mark.api
def test_py7zr_writeall_dir(tmp_path):
    target = tmp_path.joinpath("target.7z")
    archive = py7zr.SevenZipFile(target, "w")
    archive.writeall(os.path.join(testdata_path, "src"), "src")
    assert archive.files is not None
    assert len(archive.files) == 2
    for f in archive.files:
        assert f.filename in ("src", "src/bra.txt")
    archive._fpclose()


@pytest.mark.api
def test_py7zr_extract_specified_file(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, "test_1.7z"), "rb"))
    expected = [
        {
            "filename": "scripts/py7zr",
            "mode": 33261,
            "mtime": 1552522208,
            "digest": "b0385e71d6a07eb692f5fb9798e9d33aaf87be7dfff936fd2473eab2a593d4fd",
        }
    ]
    archive.extract(path=tmp_path, targets=["scripts", "scripts/py7zr"])
    archive.close()
    assert tmp_path.joinpath("scripts").is_dir()
    assert tmp_path.joinpath("scripts/py7zr").exists()
    assert not tmp_path.joinpath("setup.cfg").exists()
    assert not tmp_path.joinpath("setup.py").exists()
    check_output(expected, tmp_path)


@pytest.mark.api
def test_py7zr_extract_and_getnames(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, "test_1.7z"), "rb"))
    allfiles = archive.getnames()
    filter_pattern = re.compile(r"scripts.*")
    targets = [f for f in allfiles if filter_pattern.match(f)]
    archive.extract(path=tmp_path, targets=targets)
    archive.close()
    assert tmp_path.joinpath("scripts").is_dir()
    assert tmp_path.joinpath("scripts/py7zr").exists()
    assert not tmp_path.joinpath("setup.cfg").exists()
    assert not tmp_path.joinpath("setup.py").exists()


@pytest.mark.api
def test_py7zr_extract_and_reset_iteration(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, "test_1.7z"), "rb"))
    iterations = archive.getnames()
    for target in iterations:
        archive.extract(path=tmp_path, targets=[target])
        archive.reset()
    archive.close()
    assert tmp_path.joinpath("scripts").is_dir()
    assert tmp_path.joinpath("scripts/py7zr").exists()
    assert tmp_path.joinpath("setup.cfg").exists()
    assert tmp_path.joinpath("setup.py").exists()


@pytest.mark.api
def test_py7zr_read_and_reset(tmp_path):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, "read_reset.7z"), "rb"))
    iterations = archive.getnames()
    for target in iterations:
        _dict = archive.read(targets=[target])
        assert len(_dict) == 1
        archive.reset()
    archive.close()


@pytest.mark.api
def test_context_manager_1(tmp_path):
    with py7zr.SevenZipFile(os.path.join(testdata_path, "test_1.7z"), "r") as z:
        z.extractall(path=tmp_path)
    assert tmp_path.joinpath("scripts").is_dir()
    assert tmp_path.joinpath("scripts/py7zr").exists()
    assert tmp_path.joinpath("setup.cfg").exists()
    assert tmp_path.joinpath("setup.py").exists()


@pytest.mark.api
def test_context_manager_2(tmp_path):
    target = tmp_path.joinpath("target.7z")
    with py7zr.SevenZipFile(target, "w") as z:
        z.writeall(os.path.join(testdata_path, "src"), "src")


@pytest.mark.api
def test_py7zr_list_values():
    with py7zr.SevenZipFile(os.path.join(testdata_path, "test_1.7z"), "r") as z:
        file_list = z.list()
    assert file_list[0].filename == "scripts"
    assert file_list[1].filename == "scripts/py7zr"
    assert file_list[2].filename == "setup.cfg"
    assert file_list[3].filename == "setup.py"
    assert file_list[0].uncompressed == 0
    assert file_list[1].uncompressed == 111
    assert file_list[2].uncompressed == 58
    assert file_list[3].uncompressed == 559
    assert file_list[0].is_directory is True
    assert file_list[1].archivable is True
    assert file_list[2].archivable is True
    assert file_list[3].archivable is True
    assert file_list[0].compressed == 0
    assert file_list[1].compressed == 441
    assert file_list[2].compressed is None
    assert file_list[3].compressed is None
    assert file_list[0].crc32 is None
    assert file_list[1].crc32 == 0xB36AAEDB
    assert file_list[2].crc32 == 0xDCBF8D07
    assert file_list[3].crc32 == 0x80FC72BE
