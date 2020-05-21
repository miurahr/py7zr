import ctypes
import os
import pathlib
import sys

import pytest

import py7zr.helpers
import py7zr.win32compat

PATH_PREFIX = '\\\\?\\'


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
@pytest.mark.skipif(sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
                    reason="Administrator rights is required to make symlink on windows")
def test_symlink_readlink_absolute(tmp_path):
    origin = tmp_path / 'parent' / 'original.txt'
    origin.parent.mkdir(parents=True, exist_ok=True)
    with origin.open('w') as f:
        f.write("Original")
    slink = tmp_path / "target" / "link"
    slink.parent.mkdir(parents=True, exist_ok=True)
    target = origin.resolve()
    slink.symlink_to(target, False)
    if sys.platform.startswith("win"):
        assert py7zr.win32compat.readlink(str(tmp_path / "target" / "link")) == PATH_PREFIX + str(target)
        assert py7zr.helpers.readlink(str(slink)) == PATH_PREFIX + str(target)
        assert py7zr.helpers.readlink(slink) == pathlib.WindowsPath(PATH_PREFIX + str(target))
    else:
        assert py7zr.helpers.readlink(str(slink)) == str(target)
        assert py7zr.helpers.readlink(slink) == target
    assert slink.open('r').read() == 'Original'


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
@pytest.mark.skipif(sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
                    reason="Administrator rights is required to make symlink on windows")
def test_symlink_readlink_relative(tmp_path):
    origin = tmp_path / 'parent' / 'original.txt'
    origin.parent.mkdir(parents=True, exist_ok=True)
    with origin.open('w') as f:
        f.write("Original")
    slink = tmp_path / "target" / "link"
    slink.parent.mkdir(parents=True, exist_ok=True)
    target = pathlib.Path('../parent/original.txt')
    slink.symlink_to(target, False)
    if sys.platform.startswith("win"):
        assert py7zr.win32compat.readlink(str(tmp_path / "target" / "link")) == str(target)
        assert py7zr.win32compat.readlink(tmp_path / "target" / "link") == target
    assert slink.open('r').read() == 'Original'
    assert py7zr.helpers.readlink(slink) == target
    assert py7zr.helpers.readlink(str(slink)) == str(target)


def test_hardlink_readlink(tmp_path):
    target = tmp_path / 'parent' / 'original.txt'
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w') as f:
        f.write("Original")
    hard = tmp_path / "target" / "link"
    hard.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.system('mklink /H %s %s' % (str(hard), str(target.resolve())))
    else:
        os.link(str(target.resolve()), str(hard))
    assert hard.open('r').read() == 'Original'
    assert os.path.samefile(str(hard), str(target.resolve()))
    assert not py7zr.helpers.islink(hard)
    if sys.platform.startswith("win"):
        with pytest.raises(ValueError):
            py7zr.win32compat.readlink(str(hard))


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="test on windows")
def test_junction_readlink(tmp_path):
    target = tmp_path / 'parent'
    target.mkdir(parents=True, exist_ok=True)
    with target.joinpath("original.txt").open('w') as f:
        f.write("Original")
    junction = tmp_path / "target" / "link"
    junction.parent.mkdir(parents=True, exist_ok=True)
    os.system('mklink /J %s %s' % (str(junction), str(target.resolve())))
    assert not os.path.islink(str(junction))
    assert py7zr.win32compat.is_reparse_point(str(junction))
    assert py7zr.win32compat.readlink(str(junction)) == PATH_PREFIX + str(target.resolve())
    assert py7zr.helpers.readlink(str(junction)) == PATH_PREFIX + str(target.resolve())
    assert py7zr.win32compat.is_reparse_point(junction)
    assert py7zr.win32compat.readlink(junction) == pathlib.WindowsPath(PATH_PREFIX + str(target.resolve()))
    assert py7zr.helpers.readlink(junction) == pathlib.WindowsPath(PATH_PREFIX + str(target.resolve()))
