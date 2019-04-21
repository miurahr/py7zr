from datetime import datetime
import io
from py7zr.helpers import UTC


def decode_all(archive):
    for file_info in archive.files:
        assert file_info.lastwritetime is not None


def check_archive(archive):
    assert sorted(archive.getnames()) == ['test', 'test/test2.txt', 'test1.txt']
    expected = []
    outbuf = []
    expected.append({'filename':'test'})
    expected.append({'lastwritetime':12786932616, 'as_datetime':datetime(2006, 3, 15, 21, 43, 36, 0, UTC),
                     'filename':'test/test2.txt',
                     'contents':bytes('This file is located in a folder.', 'ascii')})
    expected.append({'lastwritetime':12786932628, 'as_datetime':datetime(2006, 3, 15, 21, 43, 48, 0, UTC),
                     'filename':'test1.txt',
                     'contents':bytes('This file is located in the root.', 'ascii')})
    for i, cf in enumerate(archive.files):
        assert cf.filename == expected[i]['filename']
        if not cf.is_directory:
            assert cf.lastwritetime // 10000000 == expected[i]['lastwritetime']
            assert cf.lastwritetime.as_datetime().replace(microsecond=0) == expected[i]['as_datetime']
            buf  = io.BytesIO()
            outbuf.append(buf)
            archive.worker.register_filelike(cf.id, buf)
    archive.worker.extract(archive.fp)
    outbuf[0].seek(0, 0)
    actual = outbuf[0].read()
    assert actual == bytes('This file is located in a folder.', 'ascii')
    outbuf[1].seek(0, 0)
    actual = outbuf[1].read()
    assert actual == bytes('This file is located in the root.', 'ascii')
