import binascii
import hashlib
import os
import shutil
import tempfile
from datetime import datetime

import py7zr
from py7zr.helpers import UTC

testdata_path = os.path.join(os.path.dirname(__file__), 'data')
os.umask(0o022)


def check_output(expected, tmpdir):
    for exp in expected:
        target = os.path.join(tmpdir, exp['filename'])
        if os.name == 'posix':
            if exp.get('mode', None):
                assert os.stat(target).st_mode == exp['mode'],\
                    "%s, actual: %d, expected: %d" % (exp['filename'], os.stat(target).st_mode, exp['mode'])
        if exp.get('mtime', None):
            assert os.stat(target).st_mtime == exp['mtime'],\
                "%s, actual: %d, expected: %d" % (exp['filename'], os.stat(target).st_mtime, exp['mode'])
        m = hashlib.sha256()
        m.update(open(target, 'rb').read())
        assert m.digest() == binascii.unhexlify(exp['digest']), "Fails digest for %s" % exp['filename']


def decode_all(archive, expected):
    tmpdir = tempfile.mkdtemp()
    for i, file_info in enumerate(archive.files):
        assert file_info.lastwritetime is not None
        assert file_info.filename is not None
    archive.extractall(path=tmpdir)
    check_output(expected, tmpdir)
    shutil.rmtree(tmpdir)


def check_archive(archive):
    assert sorted(archive.getnames()) == ['test', 'test/test2.txt', 'test1.txt']
    expected = []
    expected.append({'filename': 'test'})
    expected.append({'lastwritetime': 12786932616, 'as_datetime': datetime(2006, 3, 15, 21, 43, 36, 0, UTC()),
                     'filename': 'test/test2.txt'})
    expected.append({'lastwritetime': 12786932628, 'as_datetime': datetime(2006, 3, 15, 21, 43, 48, 0, UTC()),
                     'filename': 'test1.txt'})
    for i, cf in enumerate(archive.files):
        assert cf.filename == expected[i]['filename']
        if not cf.is_directory:
            assert cf.lastwritetime // 10000000 == expected[i]['lastwritetime']
            assert cf.lastwritetime.as_datetime().replace(microsecond=0) == expected[i]['as_datetime']
    tmpdir = tempfile.mkdtemp()
    archive.extractall(path=tmpdir)
    assert open(os.path.join(tmpdir, 'test/test2.txt'), 'rb').read() == bytes('This file is located in a folder.', 'ascii')
    assert open(os.path.join(tmpdir, 'test1.txt'), 'rb').read() == bytes('This file is located in the root.', 'ascii')
    shutil.rmtree(tmpdir)


def extract_files(f):
    tmpdir = tempfile.mkdtemp()
    archive = py7zr.SevenZipFile(open(os.path.join(testdata_path, '%s' % f), 'rb'))
    archive.extractall(tmpdir)
    shutil.rmtree(tmpdir)
