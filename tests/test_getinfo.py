import os

import pytest

from py7zr import FileInfo, SevenZipFile

testdata_path = os.path.join(os.path.dirname(__file__), "data")


def test_getinfo_file():
    with SevenZipFile(os.path.join(testdata_path, "copy.7z")) as archive:
        member = archive.getinfo("test1.txt")
        assert member.filename == "test1.txt"
        assert member.is_directory is False
        assert isinstance(member, FileInfo)


def test_getinfo_dir():
    with SevenZipFile(os.path.join(testdata_path, "copy.7z")) as archive:
        member = archive.getinfo("test")
        assert member.filename == "test"
        assert member.is_directory is True
        assert isinstance(member, FileInfo)


def test_getinfo_file_with_trailing_slash():
    with SevenZipFile(os.path.join(testdata_path, "copy.7z")) as archive:
        member = archive.getinfo("test1.txt/")
        assert member.filename == "test1.txt"
        assert member.is_directory is False
        assert isinstance(member, FileInfo)


def test_getinfo_dir_with_trailing_slash():
    with SevenZipFile(os.path.join(testdata_path, "copy.7z")) as archive:
        member = archive.getinfo("test/")
        assert member.filename == "test"
        assert member.is_directory is True
        assert isinstance(member, FileInfo)


def test_is_symlink():
    with SevenZipFile(os.path.join(testdata_path, "symlink.7z")) as archive:
        member = archive.getinfo("lib")
        assert member.filename == "lib"
        assert member.is_directory is True
        assert member.is_file is False
        assert member.is_symlink is False
        assert isinstance(member, FileInfo)

        member = archive.getinfo("lib64")
        assert member.filename == "lib64"
        assert member.is_directory is False
        assert member.is_file is False
        assert member.is_symlink is True
        assert isinstance(member, FileInfo)

        member = archive.getinfo("lib/libabc.so")
        assert member.filename == "lib/libabc.so"
        assert member.is_directory is False
        assert member.is_file is False
        assert member.is_symlink is True
        assert isinstance(member, FileInfo)

        member = archive.getinfo("lib/libabc.so.1")
        assert member.filename == "lib/libabc.so.1"
        assert member.is_directory is False
        assert member.is_file is False
        assert member.is_symlink is True
        assert isinstance(member, FileInfo)

        member = archive.getinfo("lib/libabc.so.1.2")
        assert member.filename == "lib/libabc.so.1.2"
        assert member.is_directory is False
        assert member.is_file is False
        assert member.is_symlink is True
        assert isinstance(member, FileInfo)


def test_getinfo_missing_member():
    with pytest.raises(KeyError):
        with SevenZipFile(os.path.join(testdata_path, "copy.7z")) as archive:
            archive.getinfo("doesn't exist")
