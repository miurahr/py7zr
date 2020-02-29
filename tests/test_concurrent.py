import concurrent.futures
import logging
import os
import ssl
import sys
from urllib.request import urlopen

import pytest

import py7zr

# hack only for the test, it is highly discouraged for production.
ssl._create_default_https_context = ssl._create_unverified_context
testdata_path = os.path.join(os.path.dirname(__file__), 'data')
archives = [('qt3d.7z',
             'https://ftp.jaist.ac.jp/pub/qtproject/online/qtsdkrepository/'
             'windows_x86/desktop/qt5_5126/qt.qt5.5126.win64_mingw73/'
             '5.12.6-0-201911111120qt3d-Windows-Windows_10-Mingw73-Windows-Windows_10-X86_64.7z'),
            ('qtxmlpatterns.7z',
             'https://ftp1.nluug.nl/languages/qt/online/qtsdkrepository/'
             'windows_x86/desktop/qt5_5132/qt.qt5.5132.win64_mingw73/'
             '5.13.2-0-201910281254qtxmlpatterns-Windows-Windows_10-Mingw73-Windows-Windows_10-X86_64.7z'),
            ('qtactiveqt.7z',
             'http://mirrors.dotsrc.org/qtproject/online/qtsdkrepository/'
             'windows_x86/desktop/qt5_5132/qt.qt5.5132.win64_mingw73/'
             '5.13.2-0-201910281254qtactiveqt-Windows-Windows_10-Mingw73-Windows-Windows_10-X86_64.7z'),
            ('qtbase.7z',
             'http://qt.mirrors.tds.net/qt/online/qtsdkrepository/'
             'windows_x86/desktop/qt5_5132/qt.qt5.5132.win32_mingw73/'
             '5.13.2-0-201910281254qtbase-Windows-Windows_7-Mingw73-Windows-Windows_7-X86.7z'),
            ('opengl32sw.7z',
             'http://mirrors.ocf.berkeley.edu/qt/online/qtsdkrepository/windows_x86/desktop/'
             'qt5_5132/qt.qt5.5132.win64_mingw73/'
             '5.13.2-0-201910281254opengl32sw-64-mesa_12_0_rc2.7z'),
            ('EnvVarUpdate.7z', 'https://nsis.sourceforge.io/'
                                'mediawiki/images/a/ad/EnvVarUpdate.7z'),
            ('GTKVICE-3.3.7z', 'https://downloads.sourceforge.net/project/'
                               'vice-emu/releases/binaries/windows/GTK3VICE-3.4-win64.7z'),
            ('lpng1634.7z', 'https://github.com/glennrp/libpng-releases/raw/master/lpng1634.7z')
            ]


@pytest.mark.timeout(360)
@pytest.mark.remote_data
def test_concurrent_futures(tmp_path):

    def download_and_extract(ar, path):
        archive = path.joinpath(ar[0])
        try:
            resp = urlopen(ar[1])
            with open(archive, 'wb') as fd:
                while True:
                    chunk = resp.read(8196)
                    if not chunk:
                        break
                    fd.write(chunk)
            szf = py7zr.SevenZipFile(archive)
            szf.extractall(path=path)
            szf.close()
        except Exception:
            exc = sys.exc_info()
            logging.error("Caught error: %s" % exc[1])
            return False
        return True

    with concurrent.futures.ThreadPoolExecutor() as texec:
        tasks = [texec.submit(download_and_extract, ar, tmp_path) for ar in archives]
        for task in concurrent.futures.as_completed(tasks):
            if not task.result():
                raise Exception("Failed to extract.")


@pytest.mark.timeout(180)
def test_concurrent_extraction(tmp_path, caplog):

    def extractor(archive, path):
        szf = py7zr.SevenZipFile(archive, 'r')
        szf.extractall(path=path)
        szf.close()

    archives = ['bugzilla_16.7z', 'bugzilla_4.7z', 'bzip2.7z', 'bzip2_2.7z', 'copy.7z',
                'empty.7z', 'github_14.7z', 'lzma2bcj.7z', 'mblock_1.7z', 'mblock_2.7z',
                'mblock_3.7z', 'solid.7z', 'symlink.7z', 'test_1.7z', 'test_2.7z',
                'test_3.7z', 'test_4.7z', 'test_5.7z', 'test_6.7z',
                'test_folder.7z', 'umlaut-non_solid.7z', 'umlaut-solid.7z', 'zerosize.7z']
    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = [executor.submit(extractor, os.path.join(testdata_path, ar), tmp_path.joinpath(ar)) for ar in archives]
        done, not_done = concurrent.futures.wait(tasks, return_when=concurrent.futures.ALL_COMPLETED)
        if len(not_done) > 0:
            raise Exception("Extraction error.")
