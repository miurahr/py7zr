from datetime import datetime
import io
from py7zr.helpers import UTC


def decode_all(archive):
    for file_info in archive.files:
        assert file_info.lastwritetime is not None


def check_archive(archive):
    assert sorted(archive.getnames()) == ['test', 'test/test2.txt', 'test1.txt']
    num = archive.get_num_files()
    expected = []
    outbuf = []
    expected[0]['lastwritetime'] = 12786932628
    expected[0]['as_datetime'] = datetime(2006, 3, 15, 21, 43, 48, 0, UTC)
    expected[0]['contents'] = bytes('This file is located in the root.', 'ascii')
    expected[1]['lastwritetime'] = 12786932616
    expected[1]['as_datetime'] = datetime(2006, 3, 15, 21, 43, 36, 0, UTC)
    expected[1]['contents'] = bytes('This file is located in a folder.', 'ascii')
    for i, cf in enumerate(archive.files):
        assert cf.lastwritetime // 10000000 == expected[i]['lastwritetime']
        assert cf.lastwritetime.as_datetime().replace(microsecond=0) == expected[i]['as_datetime']
        outbuf[i] = io.BytesIO()
        archive._register_filelike(cf.id, outbuf[i])
    archive.extract()
    for i in range(num):
        outbuf[i].seek(0, 0)
        actual = outbuf[i].read()
        assert actual == expected[i]['contents']
