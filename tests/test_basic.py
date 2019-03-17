import py7zr
from io import StringIO


def test_list_1():
    archive = py7zr.Archive(open('tests/archive/test_1.7z', 'rb'))
    output = StringIO()
    archive.list(file=output)
    contents = output.getvalue()
    expected = """total 3 files in solid archive
       111       441 b36aaedb scripts/py7zr
        58       441 dcbf8d07 setup.cfg
       559       441 80fc72be setup.py
"""
    assert expected == contents

def test_extract_1():
    archive = py7zr.Archive(open('tests/archive/test_1.7z', 'rb'))
    archive.extract_all(dest='/tmp/py7zr-test')
    with open("tests/origin/test_1/setup.cfg") as expected:
        with open("/tmp/py7zr-test/setup.cfg", "r") as f:
            assert expected.read() == f.read()
