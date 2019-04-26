from datetime import datetime
import os
import shutil
import tempfile
from py7zr.helpers import UTC


def decode_all(archive):
    tmpdir = tempfile.mkdtemp()
    for i, file_info in enumerate(archive.files):
        assert file_info.lastwritetime is not None
        assert file_info.filename is not None
    archive.extractall(path=tmpdir)
    shutil.rmtree(tmpdir)


def check_archive(archive):
    assert sorted(archive.getnames()) == ['test', 'test/test2.txt', 'test1.txt']
    expected = []
    expected.append({'filename': 'test'})
    expected.append({'lastwritetime': 12786932616, 'as_datetime': datetime(2006, 3, 15, 21, 43, 36, 0, UTC),
                     'filename': 'test/test2.txt'})
    expected.append({'lastwritetime': 12786932628, 'as_datetime': datetime(2006, 3, 15, 21, 43, 48, 0, UTC),
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
