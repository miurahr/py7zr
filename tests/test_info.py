import os

import pytest

import py7zr
from py7zr.exceptions import UnsupportedCompressionMethodError

testdata_path = os.path.join(os.path.dirname(__file__), 'data')
os.umask(0o022)


@pytest.mark.files
def test_archiveinfo_deflate():
    with pytest.raises(UnsupportedCompressionMethodError):
        with py7zr.SevenZipFile(os.path.join(testdata_path, 'deflate.7z'), 'r') as ar:
            ai = ar.archiveinfo()
            assert ai.method_names == 'Deflate'


@pytest.mark.files
def test_archiveinfo_deflate64():
    with pytest.raises(UnsupportedCompressionMethodError):
        with py7zr.SevenZipFile(os.path.join(testdata_path, 'deflate64.7z'), 'r') as ar:
            ai = ar.archiveinfo()
            assert ai.method_names == 'Deflate64'


@pytest.mark.files
def test_archiveinfo_lzma_bcj2():
    with pytest.raises(UnsupportedCompressionMethodError):
        with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj2.7z'), 'r') as ar:
            ai = ar.archiveinfo()
            assert ai.method_names == 'LZMA, BCJ2'


@pytest.mark.files
def test_archiveinfo_lzma_bcj():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj.7z'), 'r') as ar:
        ai = ar.archiveinfo()
        assert ai.method_names == 'LZMA, BCJ'


@pytest.mark.files
def test_archiveinfo_lzma2_bcj():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma2bcj.7z'), 'r') as ar:
        ai = ar.archiveinfo()
        assert ai.method_names == 'LZMA2, BCJ'


@pytest.mark.files
def test_archiveinfo_lzma_bcj_arm():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj_arm.7z'), 'r') as ar:
        ai = ar.archiveinfo()
        assert ai.method_names == 'LZMA2, BCJ(ARM)'


@pytest.mark.files
def test_archiveinfo_lzma_bcj_armt():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj_armt.7z'), 'r') as ar:
        ai = ar.archiveinfo()
        assert ai.method_names == 'LZMA2, BCJ(ARMT)'


@pytest.mark.files
def test_archiveinfo_lzma_bcj_ia64():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj_ia64.7z'), 'r') as ar:
        ai = ar.archiveinfo()
        assert ai.method_names == 'LZMA2, BCJ(IA64)'


@pytest.mark.files
def test_archiveinfo_lzma_bcj_ppc():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj_ppc.7z'), 'r') as ar:
        ai = ar.archiveinfo()
        assert ai.method_names == 'LZMA2, BCJ(POWERPC)'


@pytest.mark.files
def test_archiveinfo_lzma_bcj_sparc():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj_sparc.7z'), 'r') as ar:
        ai = ar.archiveinfo()
        assert ai.method_names == 'LZMA2, BCJ(SPARC)'


@pytest.mark.files
def test_archiveinfo_7zaes_lzma():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'encrypted_1.7z'), 'r') as ar:
        ai = ar.archiveinfo()
        assert ai.method_names == '7zAES, LZMA'


@pytest.mark.files
def test_archivetest_deflate():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'deflate.7z'), 'r') as ar:
        assert ar.test()


@pytest.mark.files
def test_archivetest_deflate64():
    with pytest.raises(UnsupportedCompressionMethodError):
        with py7zr.SevenZipFile(os.path.join(testdata_path, 'deflate64.7z'), 'r') as ar:
            assert ar.test()


@pytest.mark.files
def test_archivetest_lzma_bcj2():
    with pytest.raises(UnsupportedCompressionMethodError):
        with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj2.7z'), 'r') as ar:
            assert ar.test()


@pytest.mark.files
@pytest.mark.xfail(reason="Known issue to raise exception")
def test_archivetest_lzma_bcj():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj.7z'), 'r') as ar:
        assert ar.test()


@pytest.mark.files
def test_archivetest_lzma2_bcj():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma2bcj.7z'), 'r') as ar:
        assert ar.test()


@pytest.mark.files
def test_archivetest_lzma_bcj_arm():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj_arm.7z'), 'r') as ar:
        assert ar.test()


@pytest.mark.files
def test_archivetest_lzma_bcj_armt():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj_armt.7z'), 'r') as ar:
        assert ar.test()


@pytest.mark.files
def test_archivetest_lzma_bcj_ia64():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj_ia64.7z'), 'r') as ar:
        assert ar.test()


@pytest.mark.files
def test_archivetest_lzma_bcj_ppc():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj_ppc.7z'), 'r') as ar:
        assert ar.test()


@pytest.mark.files
def test_archivetest_lzma_bcj_sparc():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'lzma_bcj_sparc.7z'), 'r') as ar:
        assert ar.test()


@pytest.mark.files
def test_archivetest_7zaes():
    with py7zr.SevenZipFile(os.path.join(testdata_path, 'encrypted_1.7z'), 'r', password='secret') as ar:
        assert ar.test()
