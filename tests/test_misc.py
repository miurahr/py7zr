import os
import pathlib

import pytest

import py7zr

try:
    import multivolumefile as MVF
except ImportError:
    MVF = None

testdata_path = pathlib.Path(os.path.dirname(__file__)).joinpath('data')
os.umask(0o022)


@pytest.mark.misc
@pytest.mark.skipif(MVF is None, reason="multivolume support is not loaded.")
def test_extract_multi_volume(tmp_path):
    with testdata_path.joinpath('lzma2bcj.7z').open('rb') as src:
        with tmp_path.joinpath('lzma2bcj.7z.001').open('wb') as tgt:
            tgt.write(src.read(25000))
        with tmp_path.joinpath('lzma2bcj.7z.002').open('wb') as tgt:
            tgt.write(src.read(27337))
    with MVF.open(tmp_path.joinpath('lzma2bcj.7z'), mode='rb') as tgt:
        with py7zr.SevenZipFile(tgt) as arc:
            arc.extractall(tmp_path.joinpath('tgt'))


@pytest.mark.misc
@pytest.mark.skipif(MVF is None, reason="multivolume support is not loaded.")
def test_compress_to_multi_volume(tmp_path):
    tmp_path.joinpath('src').mkdir()
    py7zr.unpack_7zarchive(os.path.join(testdata_path, 'lzma2bcj.7z'), path=tmp_path.joinpath('src'))
    with MVF.open(tmp_path.joinpath('target.7z'), mode='wb', volume=10240) as tgt:
        with py7zr.SevenZipFile(tgt, 'w') as arc:
            arc.writeall(tmp_path.joinpath('src'), 'src')
    target = tmp_path.joinpath('target.7z.0001')
    assert target.exists()
    assert target.stat().st_size == 10240


@pytest.mark.file
def test_bcj_file(tmp_path):
    with py7zr.SevenZipFile(testdata_path.joinpath('copy_bcj_1.7z').open(mode='rb')) as ar:
        ar.extractall(tmp_path)
