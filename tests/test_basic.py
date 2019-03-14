import pytest
import py7zr

def test_extract_all():
    archive = py7zr.Archive7z(open('tests/test.7z', 'rb'))
    for name in archive.getnames():
        outfilename = os.path.join('/tmp/py7zrtest', name)
        outdir = os.path.dirname(outfilename)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        outfile = open(outfilename, 'wb')
        outfile.write(archive.getmember(name).read())
        outfile.close()
