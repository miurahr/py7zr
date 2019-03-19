import py7zr
from datetime import datetime
from py7zr.timestamp import UTC

#['bugzilla_16.7z', 'bugzilla_4.7z', 'bzip2.7z', 'copy.7z',
        #'regress_1.7z', 
#        'github_14.7z', 'github_14_multi.7z', 'github_33.7z', 'github_37_dummy.7z',
#        'github_43.7z', 'github_53.7z',
#        'test-issue-43.7z', 'umlaut-non_solid.7z', 'umlaut-solid.7z']


def decode_all(archive):
    filenames = archive.getnames()
    for filename in filenames:
        cf = archive.getmember(filename)
        #assert cf == filename
        assert cf.checkcrc() == True, 'crc failed for %s' % (filename)
        assert len(cf.read()) == cf.uncompressed

def check_archive(archive):
    assert sorted(archive.getnames()) == ['test/test2.txt', 'test1.txt']
    assert archive.getmember('test2.txt') == None
    cf = archive.getmember('test1.txt')
    assert cf.checkcrc() == True
    assert cf.lastwritetime // 10000000 == 12786932628
    assert cf.lastwritetime.as_datetime().replace(microsecond=0) == \
        datetime(2006, 3, 15, 21, 43, 48, 0, UTC)
    assert cf.read() == bytes('This file is located in the root.', 'ascii')
    cf.reset()
    assert cf.read() == bytes('This file is located in the root.', 'ascii')
    cf = archive.getmember('test/test2.txt')
    assert cf.checkcrc() == True
    assert cf.lastwritetime // 10000000 == 12786932616
    assert cf.lastwritetime.as_datetime().replace(microsecond=0) == \
        datetime(2006, 3, 15, 21, 43, 36, 0, UTC)
    assert cf.read() == bytes('This file is located in a folder.', 'ascii')
    cf.reset()
    assert cf.read() == bytes('This file is located in a folder.', 'ascii')

def test_archive():
    test_archive_files = ['non_solid.7z',  'solid.7z']
    for f in test_archive_files:
        archive = py7zr.Archive(open('tests/archive/%s' % f, 'rb'))
        check_archive(archive)

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


