import ctypes
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

import py7zr.archiveinfo
import py7zr.compressor
import py7zr.helpers
import py7zr.properties
from py7zr import PasswordRequired
from py7zr.properties import CompressionMethod

testdata_path = pathlib.Path(os.path.dirname(__file__)).joinpath("data")
os.umask(0o022)


@pytest.mark.files
def test_extract_encrypted_1(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath("encrypted_1.7z").open(mode="rb"), password="secret")
    archive.extractall(path=tmp_path)
    archive.close()


@pytest.mark.files
def test_extract_encrypted_1_mem():
    archive = py7zr.SevenZipFile(testdata_path.joinpath("encrypted_1.7z").open(mode="rb"), password="secret")
    _dict = archive.readall()
    archive.close()


@pytest.mark.files
def test_extract_encrypted_no_password(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath("encrypted_1.7z").open(mode="rb"), password=None) as archive:
        with pytest.raises(PasswordRequired):
            archive.extractall(path=tmp_path)


@pytest.mark.files
def test_extract_encrypted_needs_password(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath("encrypted_1.7z").open(mode="rb"), password=None) as archive:
        assert archive.needs_password()


@pytest.mark.files
def test_extract_header_encrypted_no_password(tmp_path):
    with pytest.raises(PasswordRequired):
        with py7zr.SevenZipFile(testdata_path.joinpath("encrypted_3.7z").open(mode="rb"), password=None) as archive:
            archive.extractall(path=tmp_path)


@pytest.mark.files
def test_extract_header_encrypted_no_password_2(tmp_path):
    with pytest.raises(PasswordRequired):
        with py7zr.SevenZipFile(testdata_path.joinpath("encrypted_4.7z").open(mode="rb"), password=None) as archive:
            archive.extractall(path=tmp_path)


@pytest.mark.cli
def test_cli_encrypted_no_password(capsys):
    arcfile = os.path.join(testdata_path, "encrypted_1.7z")
    expected = """Testing archive: {}
--
Path = {}
Type = 7z
Phisical Size = 251
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


@pytest.mark.files
@pytest.mark.timeout(45)
@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
def test_extract_encrypted_2(tmp_path):
    with testdata_path.joinpath("encrypted_2.7z").open(mode="rb") as target:
        archive = py7zr.SevenZipFile(target, password="secret")
        assert archive.header.main_streams.unpackinfo.folders[0].coders[0]["method"] == CompressionMethod.CRYPT_AES256_SHA256
        assert archive.header.main_streams.unpackinfo.folders[0].coders[1]["method"] == CompressionMethod.LZMA2
        assert archive.header.main_streams.unpackinfo.folders[1].coders[0]["method"] == CompressionMethod.CRYPT_AES256_SHA256
        assert archive.header.main_streams.unpackinfo.folders[1].coders[1]["method"] == CompressionMethod.LZMA2
        assert archive.header.main_streams.unpackinfo.folders[1].coders[2]["method"] == CompressionMethod.P7Z_BCJ
        archive.extractall(path=tmp_path)
        archive.close()


@pytest.mark.files
def test_extract_encrypted_5(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath("encrypted_5.7z").open(mode="rb"), password="secret")
    archive.extractall(path=tmp_path)
    archive.close()


@pytest.mark.files
def test_extract_encrypted_6(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath("encrypted_6.7z").open(mode="rb"), password="secret")
    archive.extractall(path=tmp_path)
    archive.close()


@pytest.mark.files
def test_encrypt_file_0(tmp_path):
    filters = [{"id": py7zr.FILTER_LZMA}, {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}]
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("tgt").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    target = tmp_path.joinpath("target.7z")
    os.chdir(str(tmp_path.joinpath("src")))
    archive = py7zr.SevenZipFile(target, "w", password="secret", filters=filters)
    archive.set_encoded_header_mode(False)
    archive.writeall(".")
    archive.close()
    #
    reader = py7zr.SevenZipFile(target, "r", password="secret")
    reader.extractall(path=tmp_path.joinpath("tgt1"))
    reader.close()
    #
    if shutil.which("7z"):
        result = subprocess.run(
            ["7z", "t", "-psecret", (tmp_path / "target.7z").as_posix()],
            stdout=subprocess.PIPE,
        )
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail("7z command report error")


@pytest.mark.files
def test_encrypt_file_1(tmp_path):
    target = tmp_path.joinpath("target.7z")
    archive = py7zr.SevenZipFile(target, "w", password="secret")
    archive.writeall(os.path.join(testdata_path, "src"), "src")
    archive.set_encoded_header_mode(False)
    assert archive.header.main_streams.unpackinfo.folders[0].coders[0]["numinstreams"] == 1
    assert archive.header.main_streams.unpackinfo.folders[0].coders[0]["numoutstreams"] == 1
    archive._write_flush()
    assert len(archive.header.main_streams.unpackinfo.folders[0].coders[0]["properties"]) == 18
    assert archive.header.main_streams.substreamsinfo.unpacksizes == [11]
    assert archive.header.main_streams.unpackinfo.folders[0].unpacksizes == [17, 11]
    assert archive.header.main_streams.packinfo.packsizes == [32]
    archive._fpclose()
    #
    with py7zr.SevenZipFile(target, "r", password="secret") as arc:
        arc.extractall(path=tmp_path / "tgt")
    #
    if shutil.which("7z"):
        result = subprocess.run(
            ["7z", "t", "-psecret", (tmp_path / "target.7z").as_posix()],
            stdout=subprocess.PIPE,
        )
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail("7z command report error")


@pytest.mark.files
def test_encrypt_file_2(tmp_path):
    filters = [{"id": py7zr.FILTER_BZIP2}, {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}]
    tmp_path.joinpath("src").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    target = tmp_path.joinpath("target.7z")
    os.chdir(str(tmp_path.joinpath("src")))
    archive = py7zr.SevenZipFile(target, "w", password="secret", filters=filters)
    archive.writeall(".")
    archive.close()
    #
    tmp_path.joinpath("tgt").mkdir()
    reader = py7zr.SevenZipFile(target, "r", password="secret")
    reader.extractall(path=tmp_path.joinpath("tgt"))
    reader.close()
    #
    if shutil.which("7z"):
        result = subprocess.run(
            ["7z", "t", "-psecret", (tmp_path / "target.7z").as_posix()],
            stdout=subprocess.PIPE,
        )
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail("7z command report error")


@pytest.mark.files
def test_encrypt_file_3(tmp_path):
    filters = [
        {"id": py7zr.FILTER_DELTA},
        {"id": py7zr.FILTER_LZMA2},
        {"id": py7zr.FILTER_CRYPTO_AES256_SHA256},
    ]
    tmp_path.joinpath("src").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    target = tmp_path.joinpath("target.7z")
    os.chdir(str(tmp_path.joinpath("src")))
    archive = py7zr.SevenZipFile(target, "w", password="secret", filters=filters)
    archive.writeall(".")
    archive.close()
    #
    tmp_path.joinpath("tgt").mkdir()
    reader = py7zr.SevenZipFile(target, "r", password="secret")
    reader.extractall(path=tmp_path.joinpath("tgt"))
    reader.close()
    #
    if shutil.which("7z"):
        result = subprocess.run(
            ["7z", "t", "-psecret", (tmp_path / "target.7z").as_posix()],
            stdout=subprocess.PIPE,
        )
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail("7z command report error")


@pytest.mark.files
def test_encrypt_file_4(tmp_path):
    filters = [
        {"id": py7zr.FILTER_X86},
        {"id": py7zr.FILTER_BZIP2},
        {"id": py7zr.FILTER_CRYPTO_AES256_SHA256},
    ]
    tmp_path.joinpath("src").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    target = tmp_path.joinpath("target.7z")
    os.chdir(str(tmp_path.joinpath("src")))
    archive = py7zr.SevenZipFile(target, "w", password="secret", filters=filters)
    archive.writeall(".")
    archive.close()
    #
    tmp_path.joinpath("tgt").mkdir()
    reader = py7zr.SevenZipFile(target, "r", password="secret")
    reader.extractall(path=tmp_path.joinpath("tgt"))
    reader.close()
    #
    if shutil.which("7z"):
        result = subprocess.run(
            ["7z", "t", "-psecret", (tmp_path / "target.7z").as_posix()],
            stdout=subprocess.PIPE,
        )
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail("7z command report error")


@pytest.mark.files
def test_encrypt_file_5(tmp_path):
    tmp_path.joinpath("src").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    target = tmp_path.joinpath("target.7z")
    os.chdir(str(tmp_path))
    with py7zr.SevenZipFile(target, mode="w", password="test123", header_encryption=True) as archive:
        archive.writeall("src", arcname="src")


@pytest.mark.files
def test_encrypt_file_6(tmp_path):
    tmp_path.joinpath("src").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    target = tmp_path.joinpath("target.7z")
    os.chdir(str(tmp_path))
    with py7zr.SevenZipFile(target, mode="w", password="test123") as archive:
        archive.set_encrypted_header(True)
        archive.writeall("src", arcname="src")


@pytest.mark.files
def test_encrypt_file_7(tmp_path):
    filters = [{"id": py7zr.FILTER_ZSTD}, {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}]
    tmp_path.joinpath("src").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    target = tmp_path.joinpath("target.7z")
    os.chdir(str(tmp_path.joinpath("src")))
    archive = py7zr.SevenZipFile(target, "w", password="secret", filters=filters)
    archive.writeall(".")
    archive.close()
    #
    tmp_path.joinpath("tgt").mkdir()
    reader = py7zr.SevenZipFile(target, "r", password="secret")
    reader.extractall(path=tmp_path.joinpath("tgt"))
    reader.close()


@pytest.mark.files
def test_encrypt_emptyfile_1(tmp_path):
    tmp_path.joinpath("src").mkdir()
    with tmp_path.joinpath("src", "x").open(mode="wb") as f:
        f.write(b"")
    archive = py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "w", password="123")
    archive.set_encrypted_header(True)
    archive.write(tmp_path.joinpath("src", "x"), "y")
    archive.close()
    #
    with py7zr.SevenZipFile(tmp_path.joinpath("target.7z"), "r", password="123") as arc:
        arc.extractall(path=tmp_path / "tgt")
    #
    assert tmp_path.joinpath("tgt", "y").is_file()


@pytest.mark.basic
def test_encrypt_simple_file_0(tmp_path):
    with tmp_path.joinpath("target.7z").open(mode="wb") as target:
        with py7zr.SevenZipFile(target, mode="w", password="secret") as archive:
            archive.writeall(os.path.join(testdata_path, "src"), "src")


@pytest.mark.files
def test_encrypt_file_8(tmp_path):
    filters = [
        {"id": py7zr.FILTER_X86},
        {"id": py7zr.FILTER_LZMA2},
        {"id": py7zr.FILTER_CRYPTO_AES256_SHA256},
    ]
    tmp_path.joinpath("src").mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, "test_1.7z"), path=tmp_path.joinpath("src"))
    target = tmp_path.joinpath("target.7z")
    os.chdir(str(tmp_path.joinpath("src")))
    archive = py7zr.SevenZipFile(target, "w", password="secret", filters=filters)
    archive.writeall(".")
    archive.close()
    #
    tmp_path.joinpath("tgt").mkdir()
    reader = py7zr.SevenZipFile(target, "r", password="secret")
    reader.extractall(path=tmp_path.joinpath("tgt"))
    reader.close()
    #
    if shutil.which("7z"):
        result = subprocess.run(
            ["7z", "t", "-psecret", (tmp_path / "target.7z").as_posix()],
            stdout=subprocess.PIPE,
        )
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail("7z command report error")
