import ctypes
import os
import sys

import pytest

import py7zr.helpers
import py7zr.win32compat

PATH_PREFIX = '\\\\?\\'


@pytest.mark.skipif(not sys.platform.startswith("win") or (ctypes.windll.shell32.IsUserAnAdmin() == 0),
                    reason="Administrator rights is required to make symlink on windows")
def test_symlink_readlink(tmp_path):
    target = tmp_path / 'parent' / 'original.txt'
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w') as f:
        f.write("Original")
    slink = tmp_path / "target" / "link"
    slink.parent.mkdir(parents=True, exist_ok=True)
    slink.symlink_to(target, False)
    if sys.version_info < (3, 8):
        assert py7zr.win32compat.readlink(str(tmp_path / "target" / "link")) == PATH_PREFIX + str(target)
    assert slink.open('r').read() == 'Original'
    assert py7zr.helpers.readlink(str(slink)) == PATH_PREFIX + str(target)


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="test on windows")
def test_hardlink_readlink(tmp_path):
    target = tmp_path / 'parent' / 'original.txt'
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w') as f:
        f.write("Original")
    hard = tmp_path / "target" / "link"
    hard.parent.mkdir(parents=True, exist_ok=True)
    os.system('mklink /H %s %s' % (str(hard), str(target.resolve())))
    assert hard.open('r').read() == 'Original'
    assert os.path.samefile(str(hard), str(target.resolve()))
    assert not py7zr.helpers.islink(str(hard))
    if sys.version_info < (3, 8):
        assert py7zr.win32compat.readlink(hard) is None


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="test on windows")
def test_junction_readlink(tmp_path):
    target = tmp_path / 'parent'
    target.mkdir(parents=True, exist_ok=True)
    with target.joinpath("original.txt").open('w') as f:
        f.write("Original")
    junction = tmp_path / "target" / "link"
    junction.parent.mkdir(parents=True, exist_ok=True)
    os.system('mklink /J %s %s' % (str(junction), str(target.resolve())))
    if sys.version_info < (3, 8):
        assert py7zr.win32compat.is_reparse_point(junction)
        assert py7zr.win32compat.readlink(str(junction)) == PATH_PREFIX + str(target.resolve())
    assert not os.path.islink(str(junction))
    assert py7zr.helpers.readlink(str(junction)) == PATH_PREFIX + str(target.resolve())
