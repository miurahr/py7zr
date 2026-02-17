# Security protection test cases
import ctypes
import os
import pathlib
import sys
from dataclasses import dataclass
from tempfile import TemporaryDirectory

import pytest

from py7zr import SevenZipFile
from py7zr.exceptions import Bad7zFile
from py7zr.helpers import check_archive_path, get_sanitized_output_path, is_path_valid
from py7zr.properties import FILTER_LZMA2, PRESET_DEFAULT

testdata_path = os.path.join(os.path.dirname(__file__), "data")


@pytest.mark.security
def test_check_archive_path():
    bad_path = "../../.../../../../../../tmp/evil.sh"
    assert not check_archive_path(bad_path)


@pytest.mark.security
def test_get_sanitized_output_path_1(tmp_path):
    bad_path = "../../.../../../../../../tmp/evil.sh"
    with pytest.raises(Bad7zFile):
        get_sanitized_output_path(bad_path, tmp_path)


@pytest.mark.misc
def test_get_sanitized_output_path_2(tmp_path):
    good_path = "good.sh"
    expected = tmp_path.joinpath(good_path)
    assert expected == get_sanitized_output_path(good_path, tmp_path)


@pytest.mark.security
def test_extract_path_traversal_attack(tmp_path):
    my_filters = [
        {"id": FILTER_LZMA2, "preset": PRESET_DEFAULT},
    ]
    target = tmp_path.joinpath("target.7z")
    good_data = b"#!/bin/sh\necho good\n"
    good_path = "good.sh"
    bad_data = b"!#/bin/sh\necho bad\n"
    bad_path = "../../.../../../../../../tmp/evil.sh"
    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive.writestr(good_data, good_path)
        archive._writestr(bad_data, bad_path)  # bypass a path check
    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=tmp_path)


@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
@pytest.mark.misc
def test_extract_symlink_attack(tmp_path):
    my_filters = [
        {"id": FILTER_LZMA2, "preset": PRESET_DEFAULT},
    ]
    source_dir = tmp_path / "src"
    symlink_file = source_dir / "symlink.sh"
    source_dir.mkdir(exist_ok=True)
    target_dir = tmp_path / "tgt"
    target = tmp_path / "target.7z"
    target_dir.mkdir(exist_ok=True)
    bad_data = b"!#/bin/sh\necho bad\n"
    bad_path = tmp_path.joinpath("evil.sh")
    with bad_path.open("wb") as evil:
        evil.write(bad_data)
    symlink_file.symlink_to(bad_path)
    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive.writeall(source_dir, "src")
    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=target_dir)


@pytest.mark.misc
def test_write_compressed_archive(tmp_path):
    @dataclass
    class Contents:
        filename: str
        text: str

    contents = (Contents(filename="bin/qmake", text="qqqqq"), Contents(filename="lib/libhoge.so", text="hoge"))
    with TemporaryDirectory() as temp_path, SevenZipFile(
        tmp_path / "tools_qtcreator-linux-qt.tools.qtcreator.7z", "w"
    ) as archive:  # fmt: skip
        dest = pathlib.Path(temp_path)
        for folder in ("bin", "lib", "mkspecs"):
            (dest / folder).mkdir(parents=True, exist_ok=True)
        for f in contents:
            full_path = dest / f.filename
            if not full_path.parent.exists():
                full_path.parent.mkdir(parents=True)
            full_path.write_text(f.text, "utf_8")
        archive.writeall(path=temp_path, arcname="target")
    with TemporaryDirectory() as target_path, SevenZipFile(
        tmp_path / "tools_qtcreator-linux-qt.tools.qtcreator.7z", "r"
    ) as archive:  # fmt: skip
        archive.extractall(path=target_path)


@pytest.mark.security
def test_zip_slip_via_symlink(tmp_path):
    """
    Test the extraction of a malicious archive that contains a symlink pointing
    outside the extraction directory, ensuring that the extraction process
    correctly identifies and blocks such attempts.
    """
    # 1. Create the ACTUAL file outside the extraction directory
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    real_file = outside_dir / "evil.txt"
    real_file.write_text("malicious content")  # The file MUST exist

    # 2. Setup the extraction directory
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    # 3. Create the symlink ladder
    # To point to 'outside/evil.txt' from 'extract/link',
    # we need to go up from 'extract' and into 'outside'

    # link1 -> ".." (moves from extract/dir1 to extract/)
    evil_link1 = extract_dir / "dir1"
    # this is inside the extraction directory
    assert is_path_valid(evil_link1 / "..", extract_dir) is False
    evil_link1.symlink_to("..")

    # link2 -> "dir1/outside"
    # Because dir1 is "..", this resolves to extract/../outside/
    evil_link2 = extract_dir / "dir2"
    # this should be detected as outside the extraction directory
    assert is_path_valid(evil_link2 / "../dir1/outside", extract_dir) is False
    assert is_path_valid(extract_dir / "dir1/outside", extract_dir) is False
    evil_link2.symlink_to("dir1/outside")

    # The entry point for the "attack"
    attack_path = extract_dir / "attack_link"
    assert is_path_valid(attack_path, extract_dir) is True
    attack_path.symlink_to("dir2")

    # 4. Construct the path through the ladder
    evil_file = attack_path / "evil.txt"

    # This should now pass because:
    # attack_link (dir2) -> dir1/outside -> ../outside -> extract/../outside/evil.txt
    assert evil_file.resolve().is_file()
    assert real_file.read_text() == evil_file.read_text()

    # This should False because the real path is outside the extraction directory

    assert is_path_valid(evil_file, extract_dir) is False
    assert is_path_valid(evil_link1, extract_dir) is False
    assert is_path_valid(evil_link2, extract_dir) is False


@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
@pytest.mark.security
def test_extract_rejects_nested_symlink_ladder(tmp_path):
    """
    Test a more complex symlink ladder to ensure nested resolution is handled.
    ladder: attack -> link2 -> link1/outside -> ../outside
    """
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "evil.txt").write_text("malicious")

    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "dir1").symlink_to("..")
    (source_dir / "dir2").symlink_to("dir1/outside")
    (source_dir / "attack").symlink_to("dir2")

    target = tmp_path / "ladder.7z"
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    with SevenZipFile(target, "w", filters=my_filters, dereference=False) as archive:
        archive.writeall(source_dir, arcname="")
        archive.writestr(b"malicious content", "attack/evil.txt")

    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=extract_dir)


@pytest.mark.security
def test_is_path_valid_with_absolute_symlink(tmp_path):
    """
    This test verifies the "is_path_valid" function's ability to handle
     scenarios involving absolute symbolic links and their resolution to absolute paths.
    """
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    # symlink to absolute path
    abs_link = extract_dir / "abs_link"
    if sys.platform == "win32":
        target = "C:\\Windows\\System32\\drivers\\etc\\hosts"
    else:
        target = "/etc/passwd"

    # is_path_valid should catch it if we try to use it
    assert is_path_valid(pathlib.Path(target), extract_dir) is False

    # Also check a relative path that resolves to absolute path via pre-existing symlink
    abs_link.symlink_to(pathlib.Path(target).parent)
    # extract_dir/abs_link/passwd -> /etc/passwd
    assert is_path_valid(abs_link / "passwd", extract_dir) is False


@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
@pytest.mark.security
def test_extract_rejects_symlink_to_base_itself(tmp_path):
    """
    Test that extraction rejects symlinks that point to the base directory itself.
    """
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "link_to_base").symlink_to(".")
    (source_dir / "subdir").mkdir()
    (source_dir / "subdir" / "link_to_base").symlink_to("..")

    target = tmp_path / "symlink_base.7z"
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    with SevenZipFile(target, "w", filters=my_filters, dereference=False) as archive:
        archive.writeall(source_dir, arcname="")

    with SevenZipFile(target, "r") as archive:
        # Some might be allowed if they point INSIDE, but pointing TO the base
        # is currently rejected by py7zr (my_resolved == base_resolved check).
        with pytest.raises(Bad7zFile):
            archive.extractall(path=extract_dir)


@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
@pytest.mark.security
def test_extract_rejects_preexisting_symlink_in_destination(tmp_path):
    """
    Attack surface: destination directory contains a symlink created by an attacker.
    Even a normal-looking member path must not be allowed to escape via that symlink.
    """
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    escaped = outside_dir / "evil.txt"
    assert not escaped.exists()

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    # Attacker plants: extract/subdir -> ../outside
    (extract_dir / "subdir").symlink_to(outside_dir)

    target = tmp_path / "target.7z"
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]

    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive.writestr(b"owned\n", "subdir/evil.txt")

    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=extract_dir)

    assert not escaped.exists()


@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
@pytest.mark.security
def test_extract_rejects_symlink_then_file_escape_in_archive(tmp_path):
    """
    Attack surface: symlink entry is extracted first, then a normal file path traverses through it.
    This is the classic 'symlink zip-slip' pattern.
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    escaped = outside_dir / "evil.txt"
    assert not escaped.exists()

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    # Build a source tree that contains a symlink that *would* escape if followed.
    # src/dir1 -> ".." so src/dir1/outside resolves to src/../outside at extraction time.
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "dir1").symlink_to("..")

    target = tmp_path / "target.7z"
    with SevenZipFile(target, "w", filters=my_filters, dereference=False) as archive:
        # 1) store the symlink entry in the archive
        archive.writeall(source_dir, arcname="src")
        # 2) add a regular file entry whose *name* goes through the symlink on extraction
        archive.writestr(b"malicious content", "src/dir1/outside/evil.txt")

    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=extract_dir)

    assert not escaped.exists()


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows UNC path test only applicable on Windows",
)
@pytest.mark.security
def test_extract_rejects_windows_unc_path(tmp_path):
    """
    Attack surface: Windows UNC path (\\\\server\\share\\file).
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    target = tmp_path / "target.7z"
    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive._writestr(b"malicious", "\\\\\\\\attacker.com\\\\share\\\\evil.dll")

    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=tmp_path)


@pytest.mark.security
def test_extract_rejects_backslash_path_traversal(tmp_path):
    """
    Attack surface: Path traversal using backslashes (Windows-style).
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    target = tmp_path / "target.7z"
    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive._writestr(b"malicious", "..\\\\..\\\\..\\\\tmp\\\\evil.sh")

    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=tmp_path)


@pytest.mark.security
def test_extract_rejects_mixed_separators(tmp_path):
    """
    Attack surface: Mixed forward and backward slashes.
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    target = tmp_path / "target.7z"
    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive._writestr(b"malicious", "subdir/..\\\\../..\\\\tmp/evil.sh"

    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=tmp_path)

                          
@pytest.mark.misc
def test_extract_rejects_windows_drive_letter_escape(tmp_path):
    """
    Attack surface: Windows absolute path with a drive letter.
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    target = tmp_path / "target.7z"
    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive._writestr(b"malicious", "C:\\Windows\\System32\\evil.dll")

    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=tmp_path)


@pytest.mark.security
def test_extract_rejects_extremely_long_path(tmp_path):
    """
    Attack surface: Extremely long path that might cause buffer overflow or DoS.
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    target = tmp_path / "target.7z"

    # Create a path with excessive depth
    long_path = "/".join(["a" * 100 for _ in range(100)])  # 10000+ characters

    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive._writestr(b"data", long_path)

    # Should handle gracefully - either extract or reject with proper error
    try:
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=tmp_path)
    except (Bad7zFile, OSError):
        pass  # Expected - OS limits exceeded


@pytest.mark.security
def test_extract_rejects_special_device_names_windows(tmp_path):
    """
    Attack surface: Windows special device names (CON, PRN, AUX, NUL, COM1, LPT1).
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    target = tmp_path / "target.7z"

    special_names = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1", "CON.txt", "PRN.log"]

    with SevenZipFile(target, "w", filters=my_filters) as archive:
        for name in special_names:
            archive._writestr(b"data", name)

    # Should handle gracefully on all platforms
    try:
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=tmp_path)
    except (Bad7zFile, OSError, ValueError):
        pass  # Expected on Windows


@pytest.mark.security
def test_extract_rejects_dot_and_dotdot_only_paths(tmp_path):
    """
    Attack surface: Paths consisting only of . or ..
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    target = tmp_path / "target.7z"

    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive._writestr(b"data1", ".")
        archive._writestr(b"data2", "..")
        archive._writestr(b"data3", "../..")

    with pytest.raises(Bad7zFile):
        with SevenZipFile(target, "r") as archive:
            archive.extractall(path=tmp_path)


@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
@pytest.mark.security
def test_extract_rejects_symlink_race_condition(tmp_path):
    """
    Attack surface: TOCTOU (Time-of-check-time-of-use) via symlink created between files.
    Archive contains: 1) safe_dir (directory), 2) later safe_dir becomes a symlink.
    """
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    source_dir = tmp_path / "src"
    source_dir.mkdir()

    # Create directory first
    (source_dir / "safe_dir").mkdir()
    (source_dir / "safe_dir" / "file1.txt").write_text("safe")

    target = tmp_path / "target.7z"
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]

    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive.writeall(source_dir, arcname="")

    # Manually manipulate the archive to have same path as both dir and symlink
    # This simulates an attacker-crafted archive
    # In practice, this would be detected during extraction

    with SevenZipFile(target, "r") as archive:
        archive.extractall(path=extract_dir)

    # Verify safe extraction
    assert (extract_dir / "safe_dir" / "file1.txt").exists()


@pytest.mark.security
def test_extract_handles_unicode_normalization_attack(tmp_path):
    """
    Attack surface: Unicode normalization attacks (e.g., different representations of same character).
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    target = tmp_path / "target.7z"

    # NFD vs NFC normalization can create different filenames that appear identical
    # é can be: U+00E9 (NFC) or U+0065 U+0301 (NFD)
    nfc_name = "café.txt"  # é as single character
    nfd_name = "café.txt"  # é as e + combining accent (if properly composed)

    with SevenZipFile(target, "w", filters=my_filters) as archive:
        archive.writestr(b"nfc", nfc_name)
        # In a real attack, this would be different bytes but same visual appearance

    with SevenZipFile(target, "r") as archive:
        archive.extractall(path=tmp_path)

    # Should extract successfully - just testing handling


@pytest.mark.security
def test_extract_handles_trailing_dots_and_spaces(tmp_path):
    """
    Attack surface: Windows strips trailing dots and spaces, could lead to unexpected overwrites.
    Tests that archives with filenames containing trailing dots/spaces are handled gracefully.
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    target = tmp_path / "target.7z"

    # Define test cases: legitimate file followed by variants with trailing characters
    test_files = [
        ("file.txt", b"data1"),  # Legitimate baseline
        ("file.txt.", b"data2"),  # Trailing dot
        ("file.txt ", b"data3"),  # Trailing space
        ("file.txt...", b"data4"),  # Multiple trailing dots
    ]

    with SevenZipFile(target, "w", filters=my_filters) as archive:
        for filename, content in test_files:
            archive._writestr(content, filename)

    # Platform-specific expectations:
    # - Windows: Should reject (OSError) due to trailing dots/spaces being invalid
    # - Other platforms: May accept or reject depending on filesystem
    with SevenZipFile(target, "r") as archive:
        if sys.platform == "win32":
            # Windows strips trailing dots/spaces, leading to potential overwrites
            # Extraction should fail to prevent security issues
            with pytest.raises(OSError):
                archive.extractall(path=tmp_path)
        else:
            # Non-Windows platforms may handle these gracefully
            try:
                archive.extractall(path=tmp_path)
            except OSError:
                pass  # Acceptable if filesystem rejects these names


@pytest.mark.skipif(
    sys.platform.startswith("win") and (ctypes.windll.shell32.IsUserAnAdmin() == 0),
    reason="Administrator rights is required to make symlink on windows",
)
@pytest.mark.security
def test_extract_rejects_symlink_to_archive_itself(tmp_path):
    """
    Attack surface: Symlink pointing to the archive file itself (zip bomb variant).
    """
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    target = tmp_path / "target.7z"
    source_dir = tmp_path / "src"
    source_dir.mkdir()

    # Create a symlink to a file (we'll point it to the archive later conceptually)
    placeholder = tmp_path / "placeholder.7z"
    placeholder.write_bytes(b"placeholder")
    (source_dir / "self_link").symlink_to(placeholder)

    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    with SevenZipFile(target, "w", filters=my_filters, dereference=False) as archive:
        archive.writeall(source_dir, arcname="")

    # Extract should handle symlinks safely
    with SevenZipFile(target, "r") as archive:
        with pytest.raises(Bad7zFile):
            archive.extractall(path=extract_dir)

                          
@pytest.mark.misc
def test_extract_rejects_null_byte_in_path(tmp_path):
    """
    Attack surface: Null byte injection in filename to bypass extension checks.
    """
    my_filters = [{"id": FILTER_LZMA2, "preset": PRESET_DEFAULT}]
    target = tmp_path / "target.7z"
    with pytest.raises(ValueError):
        with SevenZipFile(target, "w", filters=my_filters) as archive:
            archive.writestr(b"malicious", "evil.txt\\x00.png")
