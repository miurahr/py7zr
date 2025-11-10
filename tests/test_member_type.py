import stat
import sys
from typing import NamedTuple

import pytest

from py7zr.member import FILE_ATTRIBUTE_UNIX_EXTENSION, FILE_ATTRIBUTE_UNIX_SHIFT, FILE_ATTRIBUTE_WINDOWS_MASK, MemberType


class MockStatResult(NamedTuple):
    st_mode: int
    st_file_attributes: int


@pytest.mark.parametrize(
    ("type", "unix_file_type_bits", "win32_file_attributes"),
    (
        (MemberType.FILE, stat.S_IFREG, stat.FILE_ATTRIBUTE_ARCHIVE),
        (MemberType.DIRECTORY, stat.S_IFDIR, stat.FILE_ATTRIBUTE_DIRECTORY),
        (MemberType.SYMLINK, stat.S_IFLNK, stat.FILE_ATTRIBUTE_ARCHIVE | stat.FILE_ATTRIBUTE_REPARSE_POINT),
    ),
)
def test_member_type(type: MemberType, unix_file_type_bits: int, win32_file_attributes: int) -> None:
    assert type.unix_file_type_bits == unix_file_type_bits
    assert type.win32_file_attributes == win32_file_attributes
    mock_stat_result = MockStatResult(0o644, win32_file_attributes)

    assert type.unix_extension_bits() == (
        FILE_ATTRIBUTE_UNIX_EXTENSION | (type.unix_file_type_bits << FILE_ATTRIBUTE_UNIX_SHIFT)
    )

    assert type.unix_extension_bits(mock_stat_result) == (  # type: ignore[arg-type]
        FILE_ATTRIBUTE_UNIX_EXTENSION
        | (type.unix_file_type_bits << FILE_ATTRIBUTE_UNIX_SHIFT)
        | (stat.S_IMODE(mock_stat_result.st_mode) << FILE_ATTRIBUTE_UNIX_SHIFT)
    )

    assert type.attributes() == win32_file_attributes | type.unix_extension_bits()
    attributes = type.attributes(mock_stat_result)  # type: ignore[arg-type]

    if sys.platform == "win32":
        if type is MemberType.FILE:
            assert attributes == (stat.FILE_ATTRIBUTE_ARCHIVE | type.unix_extension_bits())
        else:
            assert attributes == (
                mock_stat_result.st_file_attributes & FILE_ATTRIBUTE_WINDOWS_MASK | type.unix_extension_bits()
            )
    else:
        assert attributes == win32_file_attributes | type.unix_extension_bits(mock_stat_result)  # type: ignore[arg-type]
