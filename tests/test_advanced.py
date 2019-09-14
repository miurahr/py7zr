import binascii
import hashlib
import io
import os
import shutil
import stat
import tempfile

import py7zr
import pytest
from py7zr import UnsupportedCompressionMethodError, unpack_7zarchive

from . import check_archive, decode_all

testdata_path = os.path.join(os.path.dirname(__file__), 'data')
os.umask(0o022)


def rmtree_onerror(func, path, exc_info):
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


@pytest.mark.files
def test_solid():
    f = 'solid.7z'
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, '%s' % f), 'rb'))
    check_archive(archive)


@pytest.mark.files
@pytest.mark.xfail(raises=UnsupportedCompressionMethodError)
def test_copy():
    """ test loading of copy compressed files.(help wanted)"""
    check_archive(py7zr.SevenZipFile(open(os.path.join(testdata_path, 'copy.7z'), 'rb')))


@pytest.mark.files
def test_empty():
    # decompress empty archive
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'empty.7z'), 'rb'))
    assert archive.getnames() == []


@pytest.mark.files
def test_github_14():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'github_14.7z'), 'rb'))
    assert archive.getnames() == ['github_14']
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    with open(os.path.join(tmpdir, 'github_14'), 'rb') as f:
        assert f.read() == bytes('Hello GitHub issue #14.\n', 'ascii')
    shutil.rmtree(tmpdir)


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
def _test_umlaut_archive(filename):
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, filename), 'rb'))
    assert sorted(archive.getnames()) == ['t\xe4st.txt']
    outbuf = []
    for i, cf in enumerate(archive.files):
        assert cf is not None
        buf = io.BytesIO()
        archive.worker.register_filelike(cf.id, buf)
        outbuf.append(buf)
    archive.worker.extract(archive.fp)
    buf = outbuf[0]
    buf.seek(0)
    actual = buf.read()
    assert actual == bytes('This file contains a german umlaut in the filename.', 'ascii')


@pytest.mark.files
def test_non_solid_umlaut():
    # test loading of a non-solid archive containing files with umlauts
    _test_umlaut_archive('umlaut-non_solid.7z')


@pytest.mark.files
def test_solid_umlaut():
    # test loading of a solid archive containing files with umlauts
    _test_umlaut_archive('umlaut-solid.7z')


@pytest.mark.files
def test_bugzilla_4():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'bugzilla_4.7z'), 'rb'))
    expected = [{'filename': 'History.txt', 'mtime': 1133704668, 'mode': 33188,
                 'digest': '46b08f0af612371860ab39e3b47666c3bd6fb742c5e8775159310e19ebedae7e'},
                {'filename': 'License.txt', 'mtime': 1105356710, 'mode': 33188,
                 'digest': '4f49a4448499449f2864777c895f011fb989836a37990ae1ca532126ca75d25e'},
                {'filename': 'copying.txt', 'mtime': 999116366, 'mode': 33188,
                 'digest': '2c3c3ef532828bcd42bb3127349625a25291ff5ae7e6f8d42e0fe9b5be836a99'},
                {'filename': 'readme.txt', 'mtime': 1133704646, 'mode': 33188,
                 'digest': '84f2693d9746e919883cf169fc83467be6566d7501b5044693a2480ab36a4899'}]
    decode_all(archive, expected)


@pytest.mark.files
def test_bugzilla_16():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'bugzilla_16.7z'), 'rb'))
    expected = [{'filename': 'mame4all_2.5.ini',
                 'digest': 'aaebca5e140e0099a757903fc9f194f9e6da388eed22d37bfd1625c80aa25903'},
                {'filename': 'mame4all_2.5/mame',
                 'digest': '6bc23b11fbb9a64096408623d476ad16083ef71c5e7919335e8696036034987d'}]
    decode_all(archive, expected)


@pytest.mark.files
def test_symlink():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'symlink.7z'), 'rb'))
    assert sorted(archive.getnames()) == ['lib', 'lib/libabc.so', 'lib/libabc.so.1', 'lib/libabc.so.1.2',
                                          'lib/libabc.so.1.2.3', 'lib64']
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    shutil.rmtree(tmpdir)


@pytest.mark.files
def test_lzma2bcj():
    """Test extract archive compressed with LZMA2 and BCJ methods."""
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'lzma2bcj.7z'), 'rb'))
    assert archive.getnames() == ['5.12.1', '5.12.1/msvc2017_64',
                                  '5.12.1/msvc2017_64/bin', '5.12.1/msvc2017_64/bin/opengl32sw.dll']
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    m = hashlib.sha256()
    m.update(open(os.path.join(tmpdir, '5.12.1/msvc2017_64/bin/opengl32sw.dll'), 'rb').read())
    assert m.digest() == binascii.unhexlify('963641a718f9cae2705d5299eae9b7444e84e72ab3bef96a691510dd05fa1da4')
    shutil.rmtree(tmpdir)


@pytest.mark.files
def test_zerosize():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'zerosize.7z'), 'rb'))
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    shutil.rmtree(tmpdir)


@pytest.mark.files
def test_zerosize2():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_6.7z'), 'rb'))
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    shutil.rmtree(tmpdir)


@pytest.mark.files
def test_multiblock():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'mblock.7z'), 'rb'))
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    m = hashlib.sha256()
    m.update(open(os.path.join(tmpdir, 'bin/7zdec.exe'), 'rb').read())
    assert m.digest() == binascii.unhexlify('e14d8201c5c0d1049e717a63898a3b1c7ce4054a24871daebaa717da64dcaff5')
    shutil.rmtree(tmpdir, onerror=rmtree_onerror)


@pytest.mark.api
def test_register_unpack_archive():
    shutil.register_unpack_format('7zip', ['.7z'], unpack_7zarchive)
    tmpdir = tempfile.mkdtemp()
    shutil.unpack_archive(os.path.join(testdata_path, 'test_1.7z'), tmpdir)
    target = os.path.join(tmpdir, "setup.cfg")
    expected_mode = 33188
    expected_mtime = 1552522033
    if os.name == 'posix':
        assert os.stat(target).st_mode == expected_mode
    assert os.stat(target).st_mtime == expected_mtime
    m = hashlib.sha256()
    m.update(open(target, 'rb').read())
    assert m.digest() == binascii.unhexlify('ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240')
    m = hashlib.sha256()
    m.update(open(os.path.join(tmpdir, 'setup.py'), 'rb').read())
    assert m.digest() == binascii.unhexlify('b916eed2a4ee4e48c51a2b51d07d450de0be4dbb83d20e67f6fd166ff7921e49')
    m = hashlib.sha256()
    m.update(open(os.path.join(tmpdir, 'scripts/py7zr'), 'rb').read())
    assert m.digest() == binascii.unhexlify('b0385e71d6a07eb692f5fb9798e9d33aaf87be7dfff936fd2473eab2a593d4fd')
    shutil.rmtree(tmpdir)


@pytest.mark.files
def test_skip():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test_1.7z'), 'rb'))
    for i, cf in enumerate(archive.files):
        assert cf is not None
        archive.worker.register_filelike(cf.id, None)
    archive.worker.extract(archive.fp)
