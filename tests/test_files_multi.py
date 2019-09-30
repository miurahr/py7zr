import binascii
import hashlib
import os
import shutil
import stat
import tempfile

import py7zr
import pytest

testdata_path = os.path.join(os.path.dirname(__file__), 'data')
os.umask(0o022)


def rmtree_onerror(func, path, exc_info):
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


@pytest.mark.files
def test_github_14_multi():
    """ multiple unnamed objects."""
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'github_14_multi.7z'), 'rb'))
    assert archive.getnames() == ['github_14_multi', 'github_14_multi']
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    with open(os.path.join(tmpdir, 'github_14_multi'), 'rb') as f:
        assert f.read() == bytes('Hello GitHub issue #14 2/2.\n', 'ascii')
    shutil.rmtree(tmpdir)


@pytest.mark.files
def test_multiblock():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'mblock_1.7z'), 'rb'))
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    m = hashlib.sha256()
    m.update(open(os.path.join(tmpdir, 'bin/7zdec.exe'), 'rb').read())
    assert m.digest() == binascii.unhexlify('e14d8201c5c0d1049e717a63898a3b1c7ce4054a24871daebaa717da64dcaff5')
    shutil.rmtree(tmpdir, onerror=rmtree_onerror)


@pytest.mark.files
def test_multiblock_zerosize():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'mblock_2.7z'), 'rb'))
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    shutil.rmtree(tmpdir)


@pytest.mark.files
@pytest.mark.timeout(5, method='thread')
def test_multiblock_last_padding():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'mblock_3.7z'), 'rb'))
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    m = hashlib.sha256()
    m.update(open(os.path.join(tmpdir, '5.13.0/mingw73_64/plugins/canbus/qtvirtualcanbusd.dll'), 'rb').read())
    assert m.digest() == binascii.unhexlify('98985de41ddba789d039bb10d86ea3015bf0d8d9fa86b25a0490044c247233d3')
    shutil.rmtree(tmpdir)
