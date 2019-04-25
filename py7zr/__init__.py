#!/usr/bin/env python
#
#    Pure python p7zr implementation
#    Copyright (C) 2019 Hiroshi Miura
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


from py7zr.exceptions import UnsupportedCompressionMethodError, Bad7zFile, DecompressionError
from py7zr.properties import FileAttribute
from py7zr.py7zr import SevenZipFile, is_7zfile, main

__copyright__ = 'Copyright (C) 2019 Hiroshi Miura'
__version__ = '0.0.5'
__license__ = 'LGPL-2.1+'
__author__ = 'Hiroshi Miura'
__author_email__ = 'miurahr@linux.com'
__url__ = 'http://github.com/miurahr/py7zr'

__all__ = ['SevenZipFile', 'is_7zfile', 'main', 'FileAttribute',
           'UnsupportedCompressionMethodError', 'Bad7zFile', 'DecompressionError']
