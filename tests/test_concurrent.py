import concurrent.futures
import functools
import logging
import ssl
import sys
import threading
import time
from urllib.request import urlopen
from operator import and_

import pytest

import py7zr

# hack only for the test, it is highly discouraged for production.
ssl._create_default_https_context = ssl._create_unverified_context


class MyThreadRun:
    def __init__(self):
        pass

    def download(self, pool, archive, url, results):
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

    def extract(self, pool, archive, base_dir, results):
        pool.acquire()
        try:
            logging.getLogger().info("Extracting {}".format(archive))
            szf = py7zr.SevenZipFile(archive)
            szf.extractall(path=base_dir)
            szf.close()
        except Exception:
            results[archive] = False
        else:
            results[archive] = True
        pool.release()

    def download_and_extract(self, archives, tmp_path):
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
            fname = tmp_path.joinpath(ar[0])
            url = ar[1]
            t = threading.Thread(target=self.download, args=(pool, fname, url, download_results))
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
                        ex = threading.Thread(target=self.extract, args=(ex_pool, a, tmp_path, extract_results))
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


class FuturesRun:
    def __init__(self):
        pass

    def download(self, ar, path):
        archive = path.joinpath(ar[0])
        url = ar[1]
        try:
            resp = urlopen(url)
            with open(archive, 'wb') as fd:
                while True:
                    chunk = resp.read(8196)
                    if not chunk:
                        break
                    fd.write(chunk)
        except Exception:
            exc = sys.exc_info()
            logging.error("Caught download error: %s" % exc[1])
            return False, None
        return True, time.process_time()

    def extract(self, ar, path):
        archive = path.joinpath(ar[0])
        try:
            szf = py7zr.SevenZipFile(archive)
            szf.extractall(path=path)
            szf.close()
        except Exception:
            exc = sys.exc_info()
            logging.error("Caught extraction error: %s" % exc[1])
            return False, None
        return True, time.process_time()

    def download_and_extract(self, archives, tmp_path):
        download_task = []
        extract_task = []
        completed_downloads = []
        completed_extracts = []
        with concurrent.futures.ThreadPoolExecutor() as texec:
            for i, ar in enumerate(archives):
                url = ar[1]
                logging.info("Downloading {}...".format(url))
                download_task.append(texec.submit(self.download, ar, tmp_path))
                extract_task.append(None)
                completed_downloads.append(False)
                completed_extracts.append(False)
            while True:
                for i, ar in enumerate(archives):
                    if not completed_downloads[i]:
                        # check download status
                        task = download_task[i]
                        if task.done():
                            (res, elapsed) = task.result()
                            if not res:
                                raise Exception("Failed to download {}".format(ar[0]))
                            completed_downloads[i] = True
                            # start extraction
                            logging.info("Extracting {}...".format(ar[0]))
                            extract_task[i] = texec.submit(self.extract, ar, tmp_path)
                    time.sleep(0.005)
                if functools.reduce(and_, completed_downloads):
                    logging.info("Downloads are Completed.")
                    break
                else:
                    for j, arc in enumerate(archives):
                        task = extract_task[j]
                        if task is None:
                            continue
                        if task.done():
                            (res, elapsed) = task.result()
                            if not res:
                                raise Exception("Failed to extract {}".format(arc[0]))
                            logging.info("Done {} extraction in {:.8f}.".format(arc[0], elapsed))
                            completed_extracts[j] = True
                time.sleep(0.05)
            while True:
                for i, ar in enumerate(archives):
                    if not completed_extracts[i]:
                        task = extract_task[i]
                        if task is None:
                            raise Exception("Unconsidered status")
                        if task.done():
                            (res, elapsed) = task.result()
                            logging.info("Done {} extraction in {:.8f}.".format(ar[0], elapsed))
                            completed_extracts[i] = True
                if functools.reduce(and_, completed_extracts):
                    break
                else:
                    time.sleep(0.5)


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


@pytest.mark.timeout(180)
@pytest.mark.remote_data
def test_concurrent_run(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    start_time = time.perf_counter()
    runner = MyThreadRun()
    runner.download_and_extract(archives, tmp_path)
    logging.getLogger().info("Elapsed time {:.8f}".format(time.perf_counter() - start_time))


@pytest.mark.timeout(180)
@pytest.mark.remote_data
def test_concurrent_futures(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    start_time = time.perf_counter()
    runner = FuturesRun()
    runner.download_and_extract(archives, tmp_path)
    logging.getLogger().info("Elapsed time {:.8f}".format(time.perf_counter() - start_time))
