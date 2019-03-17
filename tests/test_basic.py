import os
import py7zr
import pytest


def test_extract_all():
    archive = py7zr.Archive(open('tests/test.7z', 'rb'))
    archive.extract_all(dest='/tmp/py7zr-test')
