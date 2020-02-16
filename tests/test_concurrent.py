import concurrent.futures
import functools
import logging
import time
from operator import and_

import pytest
from urllib.request import urlopen

import py7zr


def retrieve_archive(archive, url):
    resp = urlopen(url)
    try:
        with archive.open('wb') as fd:
            while True:
                chunk = resp.read(8196)
                if not chunk:
                    break
                fd.write(chunk)
    except Exception as e:
        return None
    return archive


def extract_archive(archive, base_dir):
    py7zr.SevenZipFile(archive).extractall(path=base_dir)
    return archive, time.process_time()


@pytest.mark.timeout(300)
@pytest.mark.remote_data
def test_concurrent_futures(tmp_path):
    archives = [(tmp_path.joinpath('qt3d.7z'),
                 'https://ftp.jaist.ac.jp/pub/qtproject/online/qtsdkrepository/windows_x86/desktop/qt5_5126/qt.qt5.5126.win64_mingw73/5.12.6-0-201911111120qt3d-Windows-Windows_10-Mingw73-Windows-Windows_10-X86_64.7z'),
                (tmp_path.joinpath('lpng1634.7z'), 'https://github.com/glennrp/libpng-releases/raw/master/lpng1634.7z'),
                ]
    with concurrent.futures.ProcessPoolExecutor(2) as pexec:
        download_task = []
        completed_downloads = []
        extract_task = []
        completed_extract = []
        with concurrent.futures.ThreadPoolExecutor(2) as texec:
            for ar in archives:
                logging.warning("Downloading {}...".format(ar[1]))
                download_task.append(texec.submit(retrieve_archive, ar[0], ar[1]))
                completed_downloads.append(False)
                completed_extract.append(False)
            while True:
                for i, t in enumerate(download_task):
                    if completed_downloads[i]:
                        continue
                    elif t.done():
                        archive = t.result()
                        if archive is None:
                            pytest.fail('Failed to download test data.')
                        logging.warning("Extracting {}...".format(archive))
                        extract_task.append(pexec.submit(extract_archive, archive, tmp_path))
                        completed_downloads[i] = True
                if functools.reduce(and_, completed_downloads):
                    logging.warning("Downloads are Completed.")
                    break
                else:
                    time.sleep(0.5)
        while True:
            for i, t in enumerate(extract_task):
                if not completed_extract[i] and t.done():
                    (archive, elapsed) = t.result()
                    logging.warning("Done {} extraction in {:.8f}.".format(archive, elapsed))
                    completed_extract[i] = True
            if functools.reduce(and_, completed_extract):
                break
            else:
                time.sleep(0.5)
