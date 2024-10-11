import os

import pytest

from py7zr import SevenZipFile

testdata_path = os.path.join(os.path.dirname(__file__), "data")


def test_getinfo_file():
    with SevenZipFile(os.path.join(testdata_path, "copy.7z")) as archive:
        member = archive.getinfo("test1.txt")
        assert member.filename == "test1.txt"
        assert member.is_directory is False


def test_getinfo_dir():
    with SevenZipFile(os.path.join(testdata_path, "copy.7z")) as archive:
        member = archive.getinfo("test")
        assert member.filename == "test"
        assert member.is_directory is True


def test_getinfo_file_with_trailing_slash():
    with SevenZipFile(os.path.join(testdata_path, "copy.7z")) as archive:
        member = archive.getinfo("test1.txt/")
        assert member.filename == "test1.txt"
        assert member.is_directory is False


def test_getinfo_dir_with_trailing_slash():
    with SevenZipFile(os.path.join(testdata_path, "copy.7z")) as archive:
        member = archive.getinfo("test/")
        assert member.filename == "test"
        assert member.is_directory is True


def test_getinfo_missing_member():
    with pytest.raises(KeyError):
        with SevenZipFile(os.path.join(testdata_path, "copy.7z")) as archive:
            archive.getinfo("doesn't exist")
