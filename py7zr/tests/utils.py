from datetime import datetime
import io
from py7zr.helpers import UTC


def decode_all(archive):
    filenames = archive.getnames()
    extracted = []
    for i, filename in enumerate(filenames):
        cf = archive.getmember(i)
        assert cf.filename == filename
        assert cf.lastwritetime is not None
        buf = io.BytesIO()
        extracted.append([cf, buf])
        archive.get(cf, buf)
    archive.extract()
    for cf, buf in extracted:
        actual = len(buf.getvalue())
        assert actual == cf.size


def check_archive(archive):
    assert sorted(archive.getnames()) == ['test', 'test/test2.txt', 'test1.txt']
    cf = archive.getmember(1)
    assert cf.lastwritetime // 10000000 == 12786932628
    assert cf.lastwritetime.as_datetime().replace(microsecond=0) == datetime(2006, 3, 15, 21, 43, 48, 0, UTC)
    outbuf1 = io.BytesIO()
    outbuf2 = io.BytesIO()
    archive.get(cf, outbuf1)
    cf = archive.getmember(2)
    assert cf.lastwritetime // 10000000 == 12786932616
    assert cf.lastwritetime.as_datetime().replace(microsecond=0) == datetime(2006, 3, 15, 21, 43, 36, 0, UTC)
    archive.get(cf, outbuf2)
    archive.extract()
    actual = outbuf1.read()
    assert actual == bytes('This file is located in the root.', 'ascii')
    actual = outbuf2.read()
    assert actual == bytes('This file is located in a folder.', 'ascii')
