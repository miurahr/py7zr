import ctypes
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

import py7zr.archiveinfo
import py7zr.compressor
import py7zr.helpers
import py7zr.properties
from py7zr.properties import CompressionMethod

testdata_path = pathlib.Path(os.path.dirname(__file__)).joinpath('data')
os.umask(0o022)


@pytest.mark.files
def test_extract_encrypted_1(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('encrypted_1.7z').open(mode='rb'), password='secret')
    archive.extractall(path=tmp_path)
    archive.close()


@pytest.mark.files
def test_extract_encrypted_1_mem():
    archive = py7zr.SevenZipFile(testdata_path.joinpath('encrypted_1.7z').open(mode='rb'), password='secret')
    _dict = archive.readall()
    archive.close()


@pytest.mark.files
@pytest.mark.timeout(30)
@pytest.mark.skipif(sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
                    reason="Administrator rights is required to make symlink on windows")
def test_extract_encrypted_2(tmp_path):
    archive = py7zr.SevenZipFile(testdata_path.joinpath('encrypted_2.7z').open(mode='rb'), password='secret')
    assert archive.header.main_streams.unpackinfo.folders[0].coders[0]['method'] == CompressionMethod.CRYPT_AES256_SHA256
    assert archive.header.main_streams.unpackinfo.folders[0].coders[1]['method'] == CompressionMethod.LZMA2
    assert archive.header.main_streams.unpackinfo.folders[1].coders[0]['method'] == CompressionMethod.CRYPT_AES256_SHA256
    assert archive.header.main_streams.unpackinfo.folders[1].coders[1]['method'] == CompressionMethod.LZMA2
    assert archive.header.main_streams.unpackinfo.folders[1].coders[2]['method'] == CompressionMethod.P7Z_BCJ
    archive.extractall(path=tmp_path)
    archive.close()


@pytest.mark.files
@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_encrypt_file_0(tmp_path):
    filters = [
        {"id": py7zr.FILTER_LZMA},
        {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}
    ]
    tmp_path.joinpath('src').mkdir()
    tmp_path.joinpath('tgt').mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, 'test_1.7z'), path=tmp_path.joinpath('src'))
    target = tmp_path.joinpath('target.7z')
    os.chdir(str(tmp_path.joinpath('src')))
    archive = py7zr.SevenZipFile(target, 'w', password='secret', filters=filters)
    archive.set_encoded_header_mode(False)
    archive.writeall('.')
    archive.close()
    #
    reader = py7zr.SevenZipFile(target, 'r', password='secret')
    reader.extractall(path=tmp_path.joinpath('tgt1'))
    reader.close()
    #
    if shutil.which('7z'):
        result = subprocess.run(['7z', 't', '-psecret', (tmp_path / 'target.7z').as_posix()], stdout=subprocess.PIPE)
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail('7z command report error')


@pytest.mark.files
@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_encrypt_file_1(tmp_path):
    target = tmp_path.joinpath('target.7z')
    archive = py7zr.SevenZipFile(target, 'w', password='secret')
    archive.writeall(os.path.join(testdata_path, "src"), "src")
    archive.set_encoded_header_mode(False)
    assert archive.header.main_streams.unpackinfo.folders[0].coders[0]['numinstreams'] == 1
    assert archive.header.main_streams.unpackinfo.folders[0].coders[0]['numoutstreams'] == 1
    archive._write_archive()
    assert len(archive.header.main_streams.unpackinfo.folders[0].coders[0]['properties']) == 18
    assert archive.header.main_streams.substreamsinfo.unpacksizes == [11]
    assert archive.header.main_streams.unpackinfo.folders[0].unpacksizes == [17, 11]
    assert archive.header.main_streams.packinfo.packsizes == [32]
    archive._fpclose()
    #
    with py7zr.SevenZipFile(target, 'r', password='secret') as arc:
        arc.extractall(path=tmp_path / "tgt")
    #
    if shutil.which('7z'):
        result = subprocess.run(['7z', 't', '-psecret', (tmp_path / 'target.7z').as_posix()], stdout=subprocess.PIPE)
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail('7z command report error')


@pytest.mark.files
@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_encrypt_file_2(tmp_path):
    filters = [{"id": py7zr.FILTER_BZIP2}, {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}]
    tmp_path.joinpath('src').mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, 'test_1.7z'), path=tmp_path.joinpath('src'))
    target = tmp_path.joinpath('target.7z')
    os.chdir(str(tmp_path.joinpath('src')))
    archive = py7zr.SevenZipFile(target, 'w', password='secret', filters=filters)
    archive.writeall('.')
    archive.close()
    #
    tmp_path.joinpath('tgt').mkdir()
    reader = py7zr.SevenZipFile(target, 'r', password='secret')
    reader.extractall(path=tmp_path.joinpath('tgt'))
    reader.close()
    #
    if shutil.which('7z'):
        result = subprocess.run(['7z', 't', '-psecret', (tmp_path / 'target.7z').as_posix()], stdout=subprocess.PIPE)
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail('7z command report error')


@pytest.mark.files
@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_encrypt_file_3(tmp_path):
    filters = [{"id": py7zr.FILTER_DELTA}, {"id": py7zr.FILTER_LZMA2}, {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}]
    tmp_path.joinpath('src').mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, 'test_1.7z'), path=tmp_path.joinpath('src'))
    target = tmp_path.joinpath('target.7z')
    os.chdir(str(tmp_path.joinpath('src')))
    archive = py7zr.SevenZipFile(target, 'w', password='secret', filters=filters)
    archive.writeall('.')
    archive.close()
    #
    tmp_path.joinpath('tgt').mkdir()
    reader = py7zr.SevenZipFile(target, 'r', password='secret')
    reader.extractall(path=tmp_path.joinpath('tgt'))
    reader.close()
    #
    if shutil.which('7z'):
        result = subprocess.run(['7z', 't', '-psecret', (tmp_path / 'target.7z').as_posix()], stdout=subprocess.PIPE)
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail('7z command report error')


@pytest.mark.files
@pytest.mark.skip(reason="The combination which cannot handle correctly.")
@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_encrypt_file_4(tmp_path):
    filters = [{"id": py7zr.FILTER_X86}, {"id": py7zr.FILTER_BZIP2}, {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}]
    tmp_path.joinpath('src').mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, 'test_1.7z'), path=tmp_path.joinpath('src'))
    target = tmp_path.joinpath('target.7z')
    os.chdir(str(tmp_path.joinpath('src')))
    archive = py7zr.SevenZipFile(target, 'w', password='secret', filters=filters)
    archive.writeall('.')
    archive.close()
    #
    tmp_path.joinpath('tgt').mkdir()
    reader = py7zr.SevenZipFile(target, 'r', password='secret')
    reader.extractall(path=tmp_path.joinpath('tgt'))
    reader.close()
    #
    if shutil.which('7z'):
        result = subprocess.run(['7z', 't', '-psecret', (tmp_path / 'target.7z').as_posix()], stdout=subprocess.PIPE)
        if result.returncode != 0:
            print(result.stdout)
            pytest.fail('7z command report error')
