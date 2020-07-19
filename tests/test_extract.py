import asyncio
import binascii
import ctypes
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
from datetime import datetime

import pytest

import py7zr
from py7zr import Bad7zFile, unpack_7zarchive
from py7zr.exceptions import UnsupportedCompressionMethodError
from py7zr.helpers import UTC

from . import aio7zr, decode_all

testdata_path = pathlib.Path(os.path.dirname(__file__)).joinpath('data')
os.umask(0o022)


def check_archive(archive, tmp_path, return_dict: bool):
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
    if not return_dict:
        archive.extractall(path=tmp_path)
        assert tmp_path.joinpath('test/test2.txt').open('rb').read() == bytes('This file is located in a folder.', 'ascii')
        assert tmp_path.joinpath('test1.txt').open('rb').read() == bytes('This file is located in the root.', 'ascii')
    else:
        _dict = archive.readall()
        actual = _dict['test/test2.txt'].read()
        assert actual == bytes('This file is located in a folder.', 'ascii')
        actual = _dict['test1.txt'].read()
        assert actual == bytes('This file is located in the root.', 'ascii')
    archive.close()


@pytest.mark.files
def test_solid(tmp_path):
    f = 'solid.7z'
    archive = py7zr.SevenZipFile(testdata_path.joinpath(f).open(mode='rb'))
    check_archive(archive, tmp_path, False)


@pytest.mark.files
def test_solid_mem(tmp_path):
    f = 'solid.7z'
    archive = py7zr.SevenZipFile(testdata_path.joinpath(f).open(mode='rb'))
    check_archive(archive, tmp_path, True)


@pytest.mark.files
def test_empty():
    # decompress empty archive
    archive = py7zr.SevenZipFile(testdata_path.joinpath('empty.7z').open(mode='rb'))
    assert archive.getnames() == []


@pytest.mark.files
def test_github_14(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('github_14.7z').open(mode='rb'))
    assert archive.getnames() == ['github_14']
    archive.extractall(path=tmp_path)
    with tmp_path.joinpath('github_14').open('rb') as f:
        assert f.read() == bytes('Hello GitHub issue #14.\n', 'ascii')


@pytest.mark.files
def test_github_14_mem(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('github_14.7z').open(mode='rb'))
    _dict = archive.readall()
    actual = _dict['github_14'].read()
    assert actual == bytes('Hello GitHub issue #14.\n', 'ascii')


@pytest.mark.files
def _test_umlaut_archive(filename: str, target: pathlib.Path, return_dict: bool):
    archive = py7zr.SevenZipFile(testdata_path.joinpath(filename).open(mode='rb'))
    if not return_dict:
        assert sorted(archive.getnames()) == ['t\xe4st.txt']
        archive.extractall(path=target)
        actual = target.joinpath('t\xe4st.txt').open().read()
        assert actual == 'This file contains a german umlaut in the filename.'
    else:
        _dict = archive.readall()
        actual = _dict['t\xe4st.txt'].read()
        assert actual == b'This file contains a german umlaut in the filename.'
    archive.close()


@pytest.mark.files
def test_non_solid_umlaut(tmp_path):
    # test loading of a non-solid archive containing files with umlauts
    _test_umlaut_archive('umlaut-non_solid.7z', tmp_path, False)


@pytest.mark.files
def test_non_solid_umlaut_mem(tmp_path):
    # test loading of a non-solid archive containing files with umlauts
    _test_umlaut_archive('umlaut-non_solid.7z', tmp_path, True)


@pytest.mark.files
def test_solid_umlaut(tmp_path):
    # test loading of a solid archive containing files with umlauts
    _test_umlaut_archive('umlaut-solid.7z', tmp_path, False)


@pytest.mark.files
def test_solid_umlaut_mem(tmp_path):
    # test loading of a solid archive containing files with umlauts
    _test_umlaut_archive('umlaut-solid.7z', tmp_path, True)


@pytest.mark.files
def test_bugzilla_4(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('bugzilla_4.7z').open(mode='rb'))
    expected = [{'filename': 'History.txt', 'mtime': 1133704668, 'mode': 33188,
                 'digest': '46b08f0af612371860ab39e3b47666c3bd6fb742c5e8775159310e19ebedae7e'},
                {'filename': 'License.txt', 'mtime': 1105356710, 'mode': 33188,
                 'digest': '4f49a4448499449f2864777c895f011fb989836a37990ae1ca532126ca75d25e'},
                {'filename': 'copying.txt', 'mtime': 999116366, 'mode': 33188,
                 'digest': '2c3c3ef532828bcd42bb3127349625a25291ff5ae7e6f8d42e0fe9b5be836a99'},
                {'filename': 'readme.txt', 'mtime': 1133704646, 'mode': 33188,
                 'digest': '84f2693d9746e919883cf169fc83467be6566d7501b5044693a2480ab36a4899'}]
    decode_all(archive, expected, tmp_path)


@pytest.mark.files
@pytest.mark.skipif(sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
                    reason="Administrator rights is required to make symlink on windows")
def test_extract_symlink(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('symlink.7z').open(mode='rb'))
    assert sorted(archive.getnames()) == ['lib', 'lib/libabc.so', 'lib/libabc.so.1', 'lib/libabc.so.1.2',
                                          'lib/libabc.so.1.2.3', 'lib64']
    archive.extractall(path=tmp_path)


@pytest.mark.files
def test_extract_symlink_mem():
    with py7zr.SevenZipFile(testdata_path.joinpath('symlink.7z').open(mode='rb')) as archive:
        _dict = archive.readall()


@pytest.mark.files
def test_lzma2bcj(tmp_path):
    """Test extract archive compressed with LZMA2 and BCJ methods."""
    archive = py7zr.SevenZipFile(testdata_path.joinpath('lzma2bcj.7z').open(mode='rb'))
    assert archive.getnames() == ['mingw64', 'mingw64/bin', 'mingw64/include', 'mingw64/lib', 'mingw64/share',
                                  'mingw64/share/doc', 'mingw64/share/doc/szip', 'mingw64/include/SZconfig.h',
                                  'mingw64/include/ricehdf.h', 'mingw64/include/szip_adpt.h', 'mingw64/include/szlib.h',
                                  'mingw64/lib/libszip.a', 'mingw64/lib/libszip.dll.a', 'mingw64/share/doc/szip/COPYING',
                                  'mingw64/share/doc/szip/HISTORY.txt', 'mingw64/share/doc/szip/INSTALL',
                                  'mingw64/share/doc/szip/README', 'mingw64/share/doc/szip/RELEASE.txt',
                                  'mingw64/bin/libszip-0.dll']
    archive.extractall(path=tmp_path)
    m = hashlib.sha256()
    m.update(tmp_path.joinpath('mingw64/bin/libszip-0.dll').open('rb').read())
    assert m.digest() == binascii.unhexlify('13926e3f080c9ca557165864ce5722acc4f832bb52a92d8d86c7f6e583708c4d')
    archive.close()


@pytest.mark.files
def test_lzma2bcj_mem():
    """Test extract archive compressed with LZMA2 and BCJ methods."""
    archive = py7zr.SevenZipFile(testdata_path.joinpath('lzma2bcj.7z').open(mode='rb'))
    assert archive.getnames() == ['mingw64', 'mingw64/bin', 'mingw64/include', 'mingw64/lib', 'mingw64/share',
                                  'mingw64/share/doc', 'mingw64/share/doc/szip', 'mingw64/include/SZconfig.h',
                                  'mingw64/include/ricehdf.h', 'mingw64/include/szip_adpt.h', 'mingw64/include/szlib.h',
                                  'mingw64/lib/libszip.a', 'mingw64/lib/libszip.dll.a', 'mingw64/share/doc/szip/COPYING',
                                  'mingw64/share/doc/szip/HISTORY.txt', 'mingw64/share/doc/szip/INSTALL',
                                  'mingw64/share/doc/szip/README', 'mingw64/share/doc/szip/RELEASE.txt',
                                  'mingw64/bin/libszip-0.dll']
    _dict = archive.readall()
    m = hashlib.sha256()
    m.update(_dict['mingw64/bin/libszip-0.dll'].read())
    assert m.digest() == binascii.unhexlify('13926e3f080c9ca557165864ce5722acc4f832bb52a92d8d86c7f6e583708c4d')
    archive.close()


@pytest.mark.files
def test_lzma2bcj2(tmp_path):
    """Test extract archive compressed with LZMA2 and BCJ2 methods."""
    with pytest.raises(UnsupportedCompressionMethodError):
        archive = py7zr.SevenZipFile(testdata_path.joinpath('lzma2bcj2.7z').open(mode='rb'))
        archive.extractall(path=tmp_path)
        archive.close()


@pytest.mark.files
def test_extract_lzma_1(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('lzma_1.7z').open(mode='rb')) as ar:
        ar.extractall(tmp_path)


@pytest.mark.files
def test_extract_lzma2_1(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('lzma2_1.7z').open(mode='rb')) as ar:
        _dict = ar.readall()


@pytest.mark.files
def test_zerosize(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('zerosize.7z').open(mode='rb'))
    archive.extractall(path=tmp_path)
    archive.close()


@pytest.mark.files
def test_zerosize_mem():
    archive = py7zr.SevenZipFile(testdata_path.joinpath('zerosize.7z').open(mode='rb'))
    _dict = archive.readall()
    archive.close()


@pytest.mark.api
def test_register_unpack_archive(tmp_path):
    shutil.register_unpack_format('7zip', ['.7z'], unpack_7zarchive)
    shutil.unpack_archive(str(testdata_path.joinpath('test_1.7z')), str(tmp_path))
    target = tmp_path.joinpath("setup.cfg")
    expected_mode = 33188
    expected_mtime = 1552522033
    if os.name == 'posix':
        assert target.stat().st_mode == expected_mode
    assert target.stat().st_mtime == expected_mtime
    m = hashlib.sha256()
    m.update(target.open('rb').read())
    assert m.digest() == binascii.unhexlify('ff77878e070c4ba52732b0c847b5a055a7c454731939c3217db4a7fb4a1e7240')
    m = hashlib.sha256()
    m.update(tmp_path.joinpath('setup.py').open('rb').read())
    assert m.digest() == binascii.unhexlify('b916eed2a4ee4e48c51a2b51d07d450de0be4dbb83d20e67f6fd166ff7921e49')
    m = hashlib.sha256()
    m.update(tmp_path.joinpath('scripts/py7zr').open('rb').read())
    assert m.digest() == binascii.unhexlify('b0385e71d6a07eb692f5fb9798e9d33aaf87be7dfff936fd2473eab2a593d4fd')


@pytest.mark.files
def test_skip():
    archive = py7zr.SevenZipFile(testdata_path.joinpath('test_1.7z').open(mode='rb'))
    for i, cf in enumerate(archive.files):
        assert cf is not None
        archive.worker.register_filelike(cf.id, None)
    archive.worker.extract(archive.fp, parallel=True)
    archive.close()


@pytest.mark.files
def test_github_14_multi(tmp_path):
    """ multiple unnamed objects."""
    archive = py7zr.SevenZipFile(str(testdata_path.joinpath('github_14_multi.7z')), 'r')
    assert archive.getnames() == ['github_14_multi', 'github_14_multi']
    archive.extractall(path=tmp_path)
    with tmp_path.joinpath('github_14_multi').open('rb') as f:
        assert f.read() == bytes('Hello GitHub issue #14 1/2.\n', 'ascii')
    with tmp_path.joinpath('github_14_multi_0').open('rb') as f:
        assert f.read() == bytes('Hello GitHub issue #14 2/2.\n', 'ascii')
    archive.close()


@pytest.mark.files
def test_github_14_multi_mem():
    """ multiple unnamed objects."""
    archive = py7zr.SevenZipFile(str(testdata_path.joinpath('github_14_multi.7z')), 'r')
    assert archive.getnames() == ['github_14_multi', 'github_14_multi']
    _dict = archive.readall()
    actual_1 = _dict['github_14_multi'].read()
    assert actual_1 == bytes('Hello GitHub issue #14 1/2.\n', 'ascii')
    actual_2 = _dict['github_14_multi_0'].read()
    assert actual_2 == bytes('Hello GitHub issue #14 2/2.\n', 'ascii')
    archive.close()


@pytest.mark.files
def test_multiblock(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('mblock_1.7z').open(mode='rb'))
    archive.extractall(path=tmp_path)
    m = hashlib.sha256()
    m.update(tmp_path.joinpath('bin/7zdec.exe').open('rb').read())
    assert m.digest() == binascii.unhexlify('e14d8201c5c0d1049e717a63898a3b1c7ce4054a24871daebaa717da64dcaff5')
    archive.close()


@pytest.mark.files
def test_multiblock_mem():
    archive = py7zr.SevenZipFile(testdata_path.joinpath('mblock_1.7z').open(mode='rb'))
    _dict = archive.readall()
    m = hashlib.sha256()
    m.update(_dict["bin/7zdec.exe"].read())
    assert m.digest() == binascii.unhexlify('e14d8201c5c0d1049e717a63898a3b1c7ce4054a24871daebaa717da64dcaff5')
    archive.close()


@pytest.mark.files
@pytest.mark.skipif(sys.platform.startswith('win'), reason="Cannot unlink opened file on Windows")
def test_multiblock_unlink(tmp_path):
    """When passing opened file object, even after unlink it should work."""
    shutil.copy(str(testdata_path.joinpath('mblock_1.7z')), str(tmp_path))
    src = tmp_path.joinpath('mblock_1.7z')
    archive = py7zr.SevenZipFile(open(str(src), 'rb'))
    os.unlink(str(src))
    archive.extractall(path=tmp_path)
    archive.close()


@pytest.mark.files
def test_copy(tmp_path):
    """ test loading of copy compressed files.(help wanted)"""
    check_archive(py7zr.SevenZipFile(testdata_path.joinpath('copy.7z').open(mode='rb')), tmp_path, False)


@pytest.mark.files
def test_copy_2(tmp_path):
    """ test loading of copy compressed files part2."""
    with py7zr.SevenZipFile(testdata_path.joinpath('copy_2.7z').open(mode='rb')) as ar:
        ar.extractall(path=tmp_path)


@pytest.mark.files
def test_close_unlink(tmp_path):
    shutil.copyfile(str(testdata_path.joinpath('test_1.7z')), str(tmp_path.joinpath('test_1.7z')))
    archive = py7zr.SevenZipFile(str(tmp_path.joinpath('test_1.7z')))
    archive.extractall(path=str(tmp_path))
    archive.close()
    tmp_path.joinpath('test_1.7z').unlink()


@pytest.mark.files
@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
@pytest.mark.skipif(hasattr(sys, 'pypy_version_info'), reason="Not working with pypy3")
def test_asyncio_executor(tmp_path):
    shutil.copyfile(os.path.join(testdata_path, 'test_1.7z'), str(tmp_path.joinpath('test_1.7z')))
    loop = asyncio.get_event_loop()
    task = asyncio.ensure_future(aio7zr(tmp_path.joinpath('test_1.7z'), path=tmp_path))
    loop.run_until_complete(task)
    loop.run_until_complete(asyncio.sleep(3))
    os.unlink(str(tmp_path.joinpath('test_1.7z')))


@pytest.mark.files
def test_no_main_streams(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('test_folder.7z').open(mode='rb'))
    archive.extractall(path=tmp_path)
    archive.close()


@pytest.mark.files
def test_no_main_streams_mem():
    archive = py7zr.SevenZipFile(testdata_path.joinpath('test_folder.7z').open(mode='rb'))
    _dict = archive.readall()
    archive.close()


@pytest.mark.files
@pytest.mark.skipif(sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
                    reason="Administrator rights is required to make symlink on windows")
def test_extract_symlink_with_relative_target_path(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('symlink.7z').open(mode='rb'))
    os.chdir(str(tmp_path))
    os.makedirs(str(tmp_path.joinpath('target')))  # py35 need str() against pathlib.Path
    archive.extractall(path='target')
    assert os.readlink(str(tmp_path.joinpath('target/lib/libabc.so.1.2'))) == 'libabc.so.1.2.3'
    archive.close()


@pytest.mark.files
@pytest.mark.skipif(sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
                    reason="Administrator rights is required to make symlink on windows")
def test_extract_emptystream_mix(tmp_path):
    archive = py7zr.SevenZipFile(str(testdata_path.joinpath('test_6.7z')), 'r')
    archive.extractall(path=tmp_path)
    archive.close()


@pytest.mark.files
def test_extract_longpath_file(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('longpath.7z').open('rb')) as archive:
        archive.extractall(path=tmp_path)


@pytest.mark.files
@pytest.mark.skipif(sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
                    reason="Administrator rights is required to make symlink on windows")
def test_extract_symlink_overwrite(tmp_path):
    os.chdir(str(tmp_path))
    os.makedirs(str(tmp_path.joinpath('target')))  # py35 need str() against pathlib.Path
    with py7zr.SevenZipFile(testdata_path.joinpath('symlink.7z').open(mode='rb')) as archive:
        archive.extractall(path='target')
    with py7zr.SevenZipFile(testdata_path.joinpath('symlink.7z').open(mode='rb')) as archive:
        archive.extractall(path='target')
    assert os.readlink(str(tmp_path.joinpath('target/lib/libabc.so.1.2'))) == 'libabc.so.1.2.3'


@pytest.mark.files
def test_py7zr_extract_corrupted(tmp_path):
    with pytest.raises(Bad7zFile):
        archive = py7zr.SevenZipFile(str(testdata_path.joinpath('crc_corrupted.7z')), 'r')
        archive.extract(path=tmp_path)
        archive.close()


@pytest.mark.files
def test_extract_lzma2delta(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('lzma2delta_1.7z').open('rb')) as archive:
        archive.extractall(path=tmp_path)


@pytest.mark.skipif(not shutil.which('7z'), reason="no 7z command installed")
def test_decompress_small_files(tmp_path):
    tmp_path.joinpath('t').mkdir()
    with tmp_path.joinpath('t/a').open('w') as f:
        f.write('1')
    with tmp_path.joinpath('t/b').open('w') as f:
        f.write('2')
    result = subprocess.run(['7z', 'a', (tmp_path / 'target.7z').as_posix(), (tmp_path / 't')], stdout=subprocess.PIPE)
    if result.returncode != 0:
        print(result.stdout)
        pytest.fail('7z command report error')
    #
    with py7zr.SevenZipFile(tmp_path / 'target.7z', 'r') as arc:
        arc.testzip()


@pytest.mark.files
def test_extract_lzma_bcj_x86(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('lzma_bcj_x86.7z').open(mode='rb')) as ar:
        _dict = ar.readall()


@pytest.mark.files
def test_extract_lzma_bcj_arm(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('lzma_bcj_arm.7z').open(mode='rb')) as ar:
        ar.extractall(tmp_path)


@pytest.mark.files
def test_extract_lzma_bcj_armt(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('lzma_bcj_armt.7z').open(mode='rb')) as ar:
        ar.extractall(tmp_path)


@pytest.mark.files
def test_extract_lzma_bcj_ppc(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('lzma_bcj_ppc.7z').open(mode='rb')) as ar:
        ar.extractall(tmp_path)


@pytest.mark.files
def test_extract_lzma_bcj_sparc(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('lzma_bcj_sparc.7z').open(mode='rb')) as ar:
        ar.extractall(tmp_path)
