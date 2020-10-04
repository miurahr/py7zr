import os
import pathlib

import pytest

import py7zr

testdata_path = pathlib.Path(os.path.dirname(__file__)).joinpath('data')
os.umask(0o022)


@pytest.mark.files
def test_bcj_file(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('copy_bcj_1.7z').open(mode='rb')) as ar:
        ar.extractall(tmp_path)
