# Security protection test cases
import ctypes
import os
import pathlib
import sys
from dataclasses import dataclass
from tempfile import TemporaryDirectory

import pytest

from py7zr import SevenZipFile
from py7zr.exceptions import Bad7zFile
from py7zr.helpers import check_archive_path, get_sanitized_output_path
from py7zr.properties import FILTER_LZMA2, PRESET_DEFAULT

testdata_path = os.path.join(os.path.dirname(__file__), "data")


@pytest.mark.misc
def test_check_archive_path():
    bad_path = "../../.../../../../../../tmp/evil.sh"
    assert not check_archive_path(bad_path)


@pytest.mark.misc
def test_get_sanitized_output_path_1(tmp_path):
    bad_path = "../../.../../../../../../tmp/evil.sh"
    with pytest.raises(Bad7zFile):
        get_sanitized_output_path(bad_path, tmp_path)


@pytest.mark.misc
def test_get_sanitized_output_path_2(tmp_path):
    good_path = "good.sh"
    expected = tmp_path.joinpath(good_path)
    assert expected == get_sanitized_output_path(good_path, tmp_path)


@pytest.mark.misc
def test_extract_path_traversal_attack(tmp_path):
    my_filters = [
        {"id": FILTER_LZMA2, "preset": PRESET_DEFAULT},
    ]
    target = tmp_path.joinpath("target.7z")
    good_data = b"#!/bin/sh\necho good\n"
    good_path = "good.sh"
    bad_data = b"!#/bin/sh\necho bad\n"
    bad_path = "../../.../../../../../../tmp/evil.sh"
    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive.writestr(good_data, good_path)
        archive._writestr(bad_data, bad_path)  # bypass a path check
    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=tmp_path)


@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
@pytest.mark.misc
def test_extract_symlink_attack(tmp_path):
    my_filters = [
        {"id": FILTER_LZMA2, "preset": PRESET_DEFAULT},
    ]
    source_dir = tmp_path / "src"
    symlink_file = source_dir / "symlink.sh"
    source_dir.mkdir(exist_ok=True)
    target_dir = tmp_path / "tgt"
    target = tmp_path / "target.7z"
    target_dir.mkdir(exist_ok=True)
    bad_data = b"!#/bin/sh\necho bad\n"
    bad_path = tmp_path.joinpath("evil.sh")
    with bad_path.open("wb") as evil:
        evil.write(bad_data)
    symlink_file.symlink_to(bad_path)
    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive.writeall(source_dir, "src")
    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=target_dir)


def test_write_compressed_archive(tmp_path):
    @dataclass
    class Contents:
        filename: str
        text: str

    contents = (Contents(filename="bin/qmake", text="qqqqq"), Contents(filename="lib/libhoge.so", text="hoge"))
    with TemporaryDirectory() as temp_path, SevenZipFile(
        tmp_path / "tools_qtcreator-linux-qt.tools.qtcreator.7z", "w"
    ) as archive:  # fmt: skip
        dest = pathlib.Path(temp_path)
        for folder in ("bin", "lib", "mkspecs"):
            (dest / folder).mkdir(parents=True, exist_ok=True)
        for f in contents:
            full_path = dest / f.filename
            if not full_path.parent.exists():
                full_path.parent.mkdir(parents=True)
            full_path.write_text(f.text, "utf_8")
        archive.writeall(path=temp_path, arcname="target")
    with TemporaryDirectory() as target_path, SevenZipFile(
        tmp_path / "tools_qtcreator-linux-qt.tools.qtcreator.7z", "r"
    ) as archive:  # fmt: skip
        archive.extractall(path=target_path)
