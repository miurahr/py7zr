import logging
import multiprocessing
import threading
import time
from urllib.request import urlopen

import pytest

import py7zr


def download(pool, archive, url):
    pool.acquire(blocking=True)
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
        raise Exception('Download Error.')
    pool.release()


def extract(archive, base_dir):
    logging.getLogger().info("Extracting {}".format(archive))
    py7zr.SevenZipFile(archive).extractall(path=base_dir)


@pytest.mark.timeout(120)
@pytest.mark.remote_data
def test_concurrent_run(tmp_path, caplog):
    archives = [(tmp_path.joinpath('qt3d.7z'),
                 'https://ftp.jaist.ac.jp/pub/qtproject/online/qtsdkrepository/windows_x86/desktop/'
                 'qt5_5126/qt.qt5.5126.win64_mingw73/'
                 '5.12.6-0-201911111120qt3d-Windows-Windows_10-Mingw73-Windows-Windows_10-X86_64.7z'),
                (tmp_path.joinpath('qtactiveqt.7z'),
                 'http://mirrors.dotsrc.org/qtproject/online/qtsdkrepository/windows_x86/desktop/'
                 'qt5_5132/qt.qt5.5132.win64_mingw73/'
                 '5.13.2-0-201910281254qtactiveqt-Windows-Windows_10-Mingw73-Windows-Windows_10-X86_64.7z'),
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
    # Limit the number of threads of download.
    pool = threading.BoundedSemaphore(6)
    download_threads = []
    extract_processes = []
    completed_downloads = []
    ctx = multiprocessing.get_context(method='spawn')
    for ar in archives:
        t = threading.Thread(target=download, args=(pool, ar[0], ar[1]))
        download_threads.append((t, ar[0]))
        completed_downloads.append(False)
        t.start()
    while True:
        all_done = True
        for i, (t, a) in enumerate(download_threads):
            if not completed_downloads[i]:
                t.join(0.05)
                if not t.is_alive():
                    completed_downloads[i] = True
                    p = ctx.Process(target=extract, args=(a, tmp_path))
                    extract_processes.append(p)
                    p.start()
                else:
                    all_done = False
        if all_done:
            break
    for p in extract_processes:
        p.join()
    logging.getLogger().info("Elapsed time {:.8f}".format(time.perf_counter() - start_time))
