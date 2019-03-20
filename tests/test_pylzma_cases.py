import py7zr
import test7zr


def test_archive():
    test_archive_files = ['non_solid.7z',  'solid.7z']
    for f in test_archive_files:
        archive = py7zr.Archive(open('tests/archive/%s' % f, 'rb'))
        test7zr.check_archive(archive)

def test_copy():
    # test loading of copy compressed files
    test7zr.check_archive(py7zr.Archive(open('tests/archive/copy.7z','rb')))


def test_empty():
    # decompress empty archive
    archive = py7zr.Archive(open('tests/archive/empty.7z', 'rb'))
    assert archive.getnames() == []

def test_github_14():
    archive = py7zr.Archive(open('tests/archive/github_14.7z', 'rb'))
    assert archive.getnames() == ['github_14']
    cf = archive.getmember('github_14')
    assert cf != None
    data = cf.read()
    assert len(data) == cf.uncompressed
    assert data == bytes('Hello GitHub issue #14.\n', 'ascii')
    # accessing by name returns an arbitrary compressed streams
    # if both don't have a name in the archive
    archive = py7zr.Archive(open('tests/archive/github_14_multi.7z', 'rb'))
    assert archive.getnames() == ['github_14_multi', 'github_14_multi']
    cf = archive.getmember('github_14_multi')
    assert cf != None
    data = cf.read()
    assert len(data) == cf.uncompressed
    assert (data in (bytes('Hello GitHub issue #14 1/2.\n', 'ascii'), bytes('Hello GitHub issue #14 2/2.\n', 'ascii'))) == True
    # accessing by index returns both values
    cf = archive.getmember(0)
    assert cf != None
    data = cf.read()
    assert len(data) == cf.uncompressed
    assert data == bytes('Hello GitHub issue #14 1/2.\n', 'ascii')
    cf = archive.getmember(1)
    assert cf != None
    data = cf.read()
    assert len(data) == cf.uncompressed
    assert data == bytes('Hello GitHub issue #14 2/2.\n', 'ascii')

def test_github_37():
    archive = py7zr.Archive(open('tests/archive/github_37_dummy.7z', 'rb'))
    test7zr.check_archive(archive)
