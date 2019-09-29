import os

import py7zr
import pytest
from py7zr import UnsupportedCompressionMethodError

from . import check_archive

testdata_path = os.path.join(os.path.dirname(__file__), 'data')
os.umask(0o022)


@pytest.mark.files
@pytest.mark.xfail(raises=UnsupportedCompressionMethodError)
def test_copy():
    """ test loading of copy compressed files.(help wanted)"""
    check_archive(py7zr.SevenZipFile(open(os.path.join(testdata_path, 'copy.7z'), 'rb')))
