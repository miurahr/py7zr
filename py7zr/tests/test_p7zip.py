import os
import pytest
import py7zr
from py7zr.tests import utils

testdata_path = os.path.join(os.path.dirname(__file__), 'data')


@pytest.mark.xfail(reason="should fix")
def test_7za433_7zip_lzma_7z():
    utils.decode_all(py7zr.SevenZipFile(open(os.path.join(testdata_path, '7za433_7zip_lzma.7z'), 'rb')))


@pytest.mark.xfail(reason="Not supported yet")
def test_7za433_7zip_lzma_bcj2_7z():
    utils.decode_all(py7zr.SevenZipFile(open(os.path.join(testdata_path, '7za433_7zip_lzma_bcj2.7z'), 'rb')))


@pytest.mark.xfail(reason="should fix")
def test_7za433_7zip_lzma2_7z():
    utils.decode_all(py7zr.SevenZipFile(open(os.path.join(testdata_path, '7za433_7zip_lzma2.7z'), 'rb')))


@pytest.mark.xfail(reason="Not supported yet")
def test_7za433_7zip_lzma2_bcj2_7z():
    utils.decode_all(py7zr.SevenZipFile(open(os.path.join(testdata_path, '7za433_7zip_lzma2_bcj2.7z'), 'rb')))
