import py7zr
from io import StringIO


def test_list_1():
    archive = py7zr.Archive(open('tests/test.7z', 'rb'))
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
    archive = py7zr.Archive(open('tests/test.7z', 'rb'))
    archive.extract_all(dest='/tmp/py7zr-test')
    expected = """[flake8]
max-line-length = 125

[bdist_wheel]
universal=1
"""
    f = open("/tmp/py7zr-test/setup.cfg", "r")
    assert expected == f.read()
