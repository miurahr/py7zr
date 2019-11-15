import binascii
import hashlib
import os
import pathlib
import shutil
import tempfile

testdata_path = os.path.join(os.path.dirname(__file__), 'data')
os.umask(0o022)


def check_output(expected, tmpdir):
    for exp in expected:
        if isinstance(tmpdir, str):
            target = os.path.join(tmpdir, exp['filename'])
        else:
            target = tmpdir.joinpath(exp['filename'])
        if os.name == 'posix':
            if exp.get('mode', None):
                assert os.stat(target).st_mode == exp['mode'],\
                    "%s, actual: %d, expected: %d" % (exp['filename'], os.stat(target).st_mode, exp['mode'])
        if exp.get('mtime', None):
            assert os.stat(target).st_mtime == exp['mtime'],\
                "%s, actual: %d, expected: %d" % (exp['filename'], os.stat(target).st_mtime, exp['mode'])
        m = hashlib.sha256()
        if isinstance(tmpdir, pathlib.Path):
            m.update(target.open(mode='rb').read())
        else:
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
