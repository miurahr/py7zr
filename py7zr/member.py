from __future__ import annotations

import enum
import os
import stat
import sys
from typing import Final

FILE_ATTRIBUTE_UNIX_EXTENSION: Final = 0x8000
# Attribute is a UINT32 integer value.
# From bit 0 to 15 are as same as Windows attributes.
# Bit 16 to 31 is used for storing unix attributes.
FILE_ATTRIBUTE_UNIX_SHIFT: Final = 16
FILE_ATTRIBUTE_WINDOWS_MASK: Final = 0xFFFF


class MemberType(enum.Enum):
    FILE = enum.auto()
    DIRECTORY = enum.auto()
    SYMLINK = enum.auto()

    @property
    def unix_file_type_bits(self) -> int:
        """Get the stat S_IF* constant for this member type."""
        member2stat = {
            MemberType.FILE: stat.S_IFREG,
            MemberType.DIRECTORY: stat.S_IFDIR,
            MemberType.SYMLINK: stat.S_IFLNK,
        }
        return member2stat[self]

    @property
    def win32_file_attributes(self) -> int:
        """Get the default Windows FILE_ATTRIBUTE_* flags for this member type."""
        # Useless getattr to suppress mypy because typeshed
        # decided you would never need stat.FILE_ATTRIBUTE_*
        # on non-Windows platforms.
        # See: https://github.com/python/typeshed/issues/14865
        member2stat: dict[MemberType, int] = {
            MemberType.FILE: getattr(stat, "FILE_ATTRIBUTE_ARCHIVE"),
            MemberType.DIRECTORY: getattr(stat, "FILE_ATTRIBUTE_DIRECTORY"),
            MemberType.SYMLINK: getattr(stat, "FILE_ATTRIBUTE_ARCHIVE") | getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT"),
        }
        return member2stat[self]

    def unix_extension_bits(self, fstat: os.stat_result | None = None, /) -> int:
        """Get the Unix extension bits (file type and permissions)."""
        base = FILE_ATTRIBUTE_UNIX_EXTENSION | (self.unix_file_type_bits << FILE_ATTRIBUTE_UNIX_SHIFT)

        if fstat is not None:
            return base | (stat.S_IMODE(fstat.st_mode) << FILE_ATTRIBUTE_UNIX_SHIFT)

        return base

    def attributes(self, fstat: os.stat_result | None = None, /) -> int:
        """
        Get platform-appropriate file attributes by combining Windows attributes
        (bits 0-15) with Unix extensions (bits 16-31). Unix extensions are always
        included, even on Windows, so downstream code can use stat.S_IS*() checks
        without platform-specific logic. When no stat result is provided, synthesizes
        default attributes suitable for in-memory files.
        """
        if fstat is None:
            # There are cases where we might not have the stat_result,
            # like a file generated in memory. In this case, we synthesize
            # a sensible default by combining basic Windows and Unix attributes.
            return self.win32_file_attributes | self.unix_extension_bits()

        if sys.platform == "win32":
            # NOTE: We set Unix extensions bits on Windows so things behave the same
            # everywhere. That way, downstream code can just use stat.S_IS*() checks
            # without caring what platform the file came from.
            if self is MemberType.FILE:
                return stat.FILE_ATTRIBUTE_ARCHIVE | self.unix_extension_bits()
            return fstat.st_file_attributes & FILE_ATTRIBUTE_WINDOWS_MASK | self.unix_extension_bits()

        # Unix-like platforms
        return self.win32_file_attributes | self.unix_extension_bits(fstat)
