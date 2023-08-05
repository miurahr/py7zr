#
# p7zr library
#
# Copyright (c) 2019 Hiroshi Miura <miurahr@linux.com>
# Copyright (c) 2004-2015 by Joachim Bauch, mail@joachim-bauch.de
# 7-Zip Copyright (C) 1999-2010 Igor Pavlov
# LZMA SDK Copyright (C) 1999-2010 Igor Pavlov
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#


class ArchiveError(Exception):
    """Base class for exceptions."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Bad7zFile(ArchiveError):
    pass


class CrcError(ArchiveError):
    """Exception raised for CRC error when decompression.

    Attributes:
      expected -- expected CRC bytes
      actual -- actual CRC data
      filename -- filename that has CRC error
    """

    def __init__(self, expected, actual, filename):
        super().__init__(expected, actual, filename)
        self.expected = expected
        self.actual = actual
        self.filename = filename


class UnsupportedCompressionMethodError(ArchiveError):
    """Exception raised for unsupported compression parameter given.

    Attributes:
      data -- unknown property data
      message -- explanation of error
    """

    def __init__(self, data, message):
        super().__init__(data, message)
        self.data = data
        self.message = message


class DecompressionError(ArchiveError):
    pass


class InternalError(ArchiveError):
    pass


class PasswordRequired(Exception):
    pass


class AbsolutePathError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
