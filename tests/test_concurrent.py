import logging
import threading
import time
from urllib.request import urlopen

import pytest

import py7zr


def download(pool, archive, url, results):
    pool.acquire()
    try:
        logging.getLogger().info("Start Downloading {}".format(url))
        resp = urlopen(url)
        with archive.open('wb') as fd:
            while True:
                chunk = resp.read(8196)
                if not chunk:
                    break
                fd.write(chunk)
    except Exception:
        results[archive] = False
    else:
        results[archive] = True
    pool.release()


def extract(pool, archive, base_dir, results):
    pool.acquire()
    try:
        logging.getLogger().info("Extracting {}".format(archive))
        py7zr.SevenZipFile(archive).extractall(path=base_dir)
    except Exception:
        results[archive] = False
    else:
        results[archive] = True
    pool.release()


@pytest.mark.timeout(600)
@pytest.mark.remote_data
def test_concurrent_run(tmp_path, caplog):
    archives = [(tmp_path.joinpath('qt3d.7z'),
                 'https://ftp.jaist.ac.jp/pub/qtproject/online/qtsdkrepository/'
                 'windows_x86/desktop/qt5_5126/qt.qt5.5126.win64_mingw73/'
                 '5.12.6-0-201911111120qt3d-Windows-Windows_10-Mingw73-Windows-Windows_10-X86_64.7z'),
                (tmp_path.joinpath('qtconnectivity.7z'),
                 'http://ftp.jaist.ac.jp/pub/qtproject/online/qtsdkrepository/linux_x64/desktop/'
                 'qt5_5126/qt.qt5.5126.gcc_64/'
                 '5.12.6-0-201911111601qtconnectivity-Linux-RHEL_7_4-GCC-Linux-RHEL_7_4-X86_64.7z'),
                (tmp_path.joinpath('qtxmlpatterns.7z'),
                 'https://ftp1.nluug.nl/languages/qt/online/qtsdkrepository/'
                 'windows_x86/desktop/qt5_5132/qt.qt5.5132.win64_mingw73/'
                 '5.13.2-0-201910281254qtxmlpatterns-Windows-Windows_10-Mingw73-Windows-Windows_10-X86_64.7z'),
                (tmp_path.joinpath('qtactiveqt.7z'),
                 'http://mirrors.dotsrc.org/qtproject/online/qtsdkrepository/'
                 'windows_x86/desktop/qt5_5132/qt.qt5.5132.win64_mingw73/'
                 '5.13.2-0-201910281254qtactiveqt-Windows-Windows_10-Mingw73-Windows-Windows_10-X86_64.7z'),
                (tmp_path.joinpath('qtbase.7z'),
                 # 'http://qt.mirrors.tds.net/qt/online/qtsdkrepository/'
                 'https://ftp.jaist.ac.jp/pub/qtproject/online/qtsdkrepository/'
                 'windows_x86/desktop/qt5_5132/qt.qt5.5132.win32_mingw73/'
                 '5.13.2-0-201910281254qtbase-Windows-Windows_7-Mingw73-Windows-Windows_7-X86.7z'),
                (tmp_path.joinpath('opengl32sw.7z'),
                 'http://mirrors.ocf.berkeley.edu/qt/online/qtsdkrepository/windows_x86/desktop/'
                 'qt5_5132/qt.qt5.5132.win64_mingw73/'
                 '5.13.2-0-201910281254opengl32sw-64-mesa_12_0_rc2.7z'),
                (tmp_path.joinpath('EnvVarUpdate.7z'), 'https://nsis.sourceforge.io/'
                                                       'mediawiki/images/a/ad/EnvVarUpdate.7z'),
                (tmp_path.joinpath('GTKVICE-3.3.7z'), 'https://downloads.sourceforge.net/project/'
                                                      'vice-emu/releases/binaries/windows/GTK3VICE-3.4-win64.7z'),
                (tmp_path.joinpath('lpng1634.7z'), 'https://github.com/glennrp/libpng-releases/raw/master/lpng1634.7z')
                ]
    caplog.set_level(logging.INFO)
    start_time = time.perf_counter()
    # Limit a number of threads of download.
    pool = threading.BoundedSemaphore(3)
    # Limit a number of extraction threads.
    ex_pool = threading.BoundedSemaphore(6)
    download_threads = {}
    download_results = {}
    extract_threads = {}
    completed_downloads = {}
    completed_extracts = {}
    extract_results = {}
    for ar in archives:
        fname = ar[0]
        url = ar[1]
        t = threading.Thread(target=download, args=(pool, fname, url, download_results))
        download_threads[fname] = t
        extract_threads[fname] = None
        completed_downloads[fname] = False
        completed_extracts[fname] = False
        t.start()
    while True:
        all_done = True
        for a in download_threads:
            if not completed_downloads[a]:
                t = download_threads[a]
                t.join(0.05)
                if not t.is_alive():
                    completed_downloads[a] = True
                    ex = threading.Thread(target=extract, args=(ex_pool, a, tmp_path, extract_results))
                    extract_threads[a] = ex
                    ex.start()
                else:
                    all_done = False
            elif completed_extracts[a] or extract_threads[a] is None:
                pass
            else:
                ex = extract_threads[a]
                ex.join(0.005)
                if not ex.is_alive():
                    if extract_results[a]:
                        completed_extracts[a] = True
                    else:
                        raise Exception("Extraction error.")
        if all_done:
            break
        time.sleep(0.5)
    for a in extract_threads:
        if not completed_extracts[a]:
            ex = extract_threads[a]
            ex.join()
            if not extract_results[a]:
                raise Exception("Extraction error.")
            else:
                completed_extracts[a] = True
    logging.getLogger().info("Elapsed time {:.8f}".format(time.perf_counter() - start_time))
