import asyncio
import binascii
import functools
import hashlib
import os
import pathlib
import shutil
import subprocess
from datetime import datetime, timezone

import pytest

import py7zr

try:
    import libarchive.public as LAPublic
except ImportError:
    LAPublic = None

testdata_path = os.path.join(os.path.dirname(__file__), 'data')
os.umask(0o022)


def check_output(expected, tmpdir):
    for exp in expected:
        if isinstance(tmpdir, str):
            target = pathlib.Path(tmpdir).joinpath(exp['filename'])
        else:
            target = tmpdir.joinpath(exp['filename'])
        if os.name == 'posix':
            if exp.get('mode', None):
                assert target.stat().st_mode == exp['mode'],\
                    "%s, actual: %d, expected: %d" % (exp['filename'], target.stat().st_mode, exp['mode'])
        if exp.get('mtime', None):
            assert target.stat().st_mtime == exp['mtime'],\
                "%s, actual: %d, expected: %d" % (exp['filename'], target.stat().st_mtime, exp['mtime'])
        m = hashlib.sha256()
        m.update(target.open('rb').read())
        assert m.digest() == binascii.unhexlify(exp['digest']), "Fails digest for %s" % exp['filename']


def decode_all(archive, expected, tmpdir):
    for i, file_info in enumerate(archive.files):
        assert file_info.lastwritetime is not None
        assert file_info.filename is not None
    archive.extractall(path=tmpdir)
    archive.close()
    check_output(expected, tmpdir)


async def aio7zr(archive, path):
    loop = asyncio.get_event_loop()
    sevenzip = py7zr.SevenZipFile(archive)
    partial_py7zr = functools.partial(sevenzip.extractall, path=path)
    loop.run_in_executor(None, partial_py7zr)
    loop.run_in_executor(None, sevenzip.close)


def ltime(dt_utc):
    return dt_utc.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%Y-%m-%d %H:%M:%S")


def ltime2(y, m, d, h, min, s):
    return ltime(datetime(y, m, d, h, min, s))


def p7zip_test(archive):
    if shutil.which('7z'):
        result = subprocess.run(['7z', 't', archive.as_posix()], stdout=subprocess.PIPE)
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail('7z command report error')


def libarchive_extract(archive, tmpdir):
    if LAPublic:
        if not tmpdir.exists():
            tmpdir.mkdir(parents=True)
        with LAPublic.file_reader(str(archive)) as e:
            for entry in e:
                if entry.filetype.IFDIR:
                    tmpdir.joinpath(entry.pathname).mkdir(parents=True)
                elif entry.filetype.IFLNK:
                    tmpdir.joinpath(entry.pathname).link_to(entry.symlink_targetpath)
                else:
                    with tmpdir.joinpath(entry.pathname).open(mode='wb') as f:
                        for block in entry.get_blocks():
                            f.write(block)
