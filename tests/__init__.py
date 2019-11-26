import binascii
import hashlib
import os
import pathlib

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
                "%s, actual: %d, expected: %d" % (exp['filename'], target.stat().st_mtime, exp['mode'])
        m = hashlib.sha256()
        m.update(target.open('rb').read())
        assert m.digest() == binascii.unhexlify(exp['digest']), "Fails digest for %s" % exp['filename']


def decode_all(archive, expected, tmpdir):
    for i, file_info in enumerate(archive.files):
        assert file_info.lastwritetime is not None
        assert file_info.filename is not None
    archive.extractall(path=tmpdir)
    check_output(expected, tmpdir)
