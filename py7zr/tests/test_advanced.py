import py7zr
import hashlib
import io
import os
import pytest
import shutil
import tempfile

from binascii import unhexlify
from py7zr.tests import decode_all, check_archive


testdata_path = os.path.join(os.path.dirname(__file__), 'data')


@pytest.mark.files
def test_solid():
    f = 'solid.7z'
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, '%s' % f), 'rb'))
    check_archive(archive)


@pytest.mark.files
@pytest.mark.xfail
def test_copy():
    # test loading of copy compressed files
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
    assert actual == bytes('Hello GitHub issue #14.\n', 'ascii')


@pytest.mark.files
@pytest.mark.skip
def test_github_14_multi():
    """ multiple unnamed objects."""
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'github_14_multi.7z'), 'rb'))
    assert archive.getnames() == ['github_14_multi', 'github_14_multi']
    outbuf = []
    for i, cf in enumerate(archive.files):
        assert cf is not None
        buf = io.BytesIO()
        archive.worker.register_filelike(cf.id, buf)
        outbuf.append(buf)
    archive.worker.extract(archive.fp)
    # check here
    expected = [bytes('Hello GitHub issue #14 1/2.\n', 'ascii'), bytes('Hello GitHub issue #14 2/2.\n', 'ascii')]
    buf = outbuf[0]
    buf.seek(0)
    actual = buf.read()
    assert actual == expected[0]
    buf = outbuf[1]
    buf.seek(0)
    actual = buf.read()
    assert actual == expected[1]


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
    decode_all(archive)


@pytest.mark.files
@pytest.mark.xfail(reason='Not support LZMA1.')
def test_bugzilla_16():
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'bugzilla_16.7z'), 'rb'))
    decode_all(archive)


@pytest.mark.files
def test_github_43_provided():
    # test loading file submitted by @mikenye
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, 'test-issue-43.7z'), 'rb'))
    assert sorted(archive.getnames()) == ['blah.txt'] + ['blah%d.txt' % x for x in range(2, 10)]
    decode_all(archive)


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
    assert m.digest() == unhexlify('963641a718f9cae2705d5299eae9b7444e84e72ab3bef96a691510dd05fa1da4')
    shutil.rmtree(tmpdir)
