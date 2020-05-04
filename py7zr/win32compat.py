import pathlib
import stat
import sys
from typing import Union

from py7zr.exceptions import InternalError

if sys.platform == "win32" and sys.version_info < (3, 8):
    import ctypes
    import ctypes.byref as byref
    import ctypes.wintypes as wintypes

    _stdcall_libraries = {}
    _stdcall_libraries['kernel32'] = ctypes.WinDLL('kernel32')
    CloseHandle = _stdcall_libraries['kernel32'].CloseHandle
    CreateFileW = _stdcall_libraries['kernel32'].CreateFileW
    DeviceIoControl = _stdcall_libraries['kernel32'].DeviceIoControl
    GetFileAttributesW = _stdcall_libraries['kernel32'].GetFileAttributesW
    OPEN_EXISTING = 3
    GENERIC_READ = 2147483648
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    FSCTL_GET_REPARSE_POINT = 0x000900A8
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003
    IO_REPARSE_TAG_SYMLINK = 0xA000000C
    MAXIMUM_REPARSE_DATA_BUFFER_SIZE = 16 * 1024

    def _check_bit(val: int, flag: int) -> bool:
        return bool(val & flag == flag)

    class SymbolicLinkReparseBuffer(ctypes.Structure):
        """ Implementing the below in Python:

        typedef struct _REPARSE_DATA_BUFFER {
            ULONG  ReparseTag;
            USHORT ReparseDataLength;
            USHORT Reserved;
            union {
                struct {
                    USHORT SubstituteNameOffset;
                    USHORT SubstituteNameLength;
                    USHORT PrintNameOffset;
                    USHORT PrintNameLength;
                    ULONG Flags;
                    WCHAR PathBuffer[1];
                } SymbolicLinkReparseBuffer;
                struct {
                    USHORT SubstituteNameOffset;
                    USHORT SubstituteNameLength;
                    USHORT PrintNameOffset;
                    USHORT PrintNameLength;
                    WCHAR PathBuffer[1];
                } MountPointReparseBuffer;
                struct {
                    UCHAR  DataBuffer[1];
                } GenericReparseBuffer;
            } DUMMYUNIONNAME;
        } REPARSE_DATA_BUFFER, *PREPARSE_DATA_BUFFER;
        """
        # See https://docs.microsoft.com/en-us/windows-hardware/drivers/ddi/content/ntifs/ns-ntifs-_reparse_data_buffer
        _fields_ = [
            ('flags', ctypes.c_ulong),
            ('path_buffer', ctypes.c_byte * (MAXIMUM_REPARSE_DATA_BUFFER_SIZE - 20))
        ]

    class MountReparseBuffer(ctypes.Structure):
        _fields_ = [
            ('path_buffer', ctypes.c_byte * (MAXIMUM_REPARSE_DATA_BUFFER_SIZE - 16)),
        ]

    class ReparseBufferField(ctypes.Union):
        _fields_ = [
            ('symlink', SymbolicLinkReparseBuffer),
            ('mount', MountReparseBuffer)
        ]

    class ReparseBuffer(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [
            ('reparse_tag', ctypes.c_ulong),
            ('reparse_data_length', ctypes.c_ushort),
            ('reserved', ctypes.c_ushort),
            ('substitute_name_offset', ctypes.c_ushort),
            ('substitute_name_length', ctypes.c_ushort),
            ('print_name_offset', ctypes.c_ushort),
            ('print_name_length', ctypes.c_ushort),
            ('u', ReparseBufferField)
        ]

    def is_reparse_point(path: Union[str, pathlib.Path]) -> bool:
        GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
        GetFileAttributesW.restype = wintypes.DWORD
        return _check_bit(GetFileAttributesW(str(path)), stat.FILE_ATTRIBUTE_REPARSE_POINT)

    def readlink(path: Union[str, pathlib.Path]) -> str:
        # FILE_FLAG_OPEN_REPARSE_POINT alone is not enough if 'path'
        # is a symbolic link to a directory or a NTFS junction.
        # We need to set FILE_FLAG_BACKUP_SEMANTICS as well.
        # See https://docs.microsoft.com/en-us/windows/desktop/api/fileapi/nf-fileapi-createfilea
        if isinstance(path, pathlib.Path):
            target = str(str(path.resolve()))
        else:
            target = str(path)
        CreateFileW.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE]
        CreateFileW.restype = wintypes.HANDLE
        handle = wintypes.HANDLE(CreateFileW(target, GENERIC_READ, 0, None, OPEN_EXISTING,
                             FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, 0))
        buf = ReparseBuffer()
        status, _ = _DeviceIoControl(handle, FSCTL_GET_REPARSE_POINT, None, 0, byref(buf), MAXIMUM_REPARSE_DATA_BUFFER_SIZE)
        CloseHandle(handle)
        if not status:
            raise InternalError("Failed IOCTL access to get REPARSE_POINT.")
        if buf.reparse_tag == IO_REPARSE_TAG_SYMLINK:
            offset = buf.substitute_name_offset
            ending = offset + buf.substitute_name_length
            rpath = buf.symlink.path_buffer[offset:ending].decode('UTF-16-LE')
        elif buf.reparse_tag == IO_REPARSE_TAG_MOUNT_POINT:
            offset = buf.substitute_name_offset
            ending = offset + buf.substitute_name_length
            rpath = buf.mount.path_buffer[offset:ending].decode('UTF-16-LE')
            rpath[:0] = '\\??\\'
        else:
            rpath = ''
        return rpath

    def _DeviceIoControl(devhandle, ioctl, inbuf, inbufsiz, outbuf, outbufsiz):
        # The MIT License (MIT)
        #
        # Copyright © 2014-2016 Santoso Wijaya <santoso.wijaya@gmail.com>
        #
        # Permission is hereby granted, free of charge, to any person
        # obtaining a copy of this software and associated documentation files
        # (the "Software"), to deal in the Software without restriction,
        # including without limitation the rights to use, copy, modify, merge,
        # publish, distribute, sub-license, and/or sell copies of the Software,
        # and to permit persons to whom the Software is furnished to do so,
        # subject to the following conditions:
        #
        # The above copyright notice and this permission notice shall be
        # included in all copies or substantial portions of the Software.
        #
        # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
        # EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
        # MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
        # NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
        # BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
        # ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
        # CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        # SOFTWARE.
        """See: DeviceIoControl function
        http://msdn.microsoft.com/en-us/library/aa363216(v=vs.85).aspx
        """
        DeviceIoControl.argtypes = [
                wintypes.HANDLE,                    # _In_          HANDLE hDevice
                wintypes.DWORD,                     # _In_          DWORD dwIoControlCode
                wintypes.LPVOID,                    # _In_opt_      LPVOID lpInBuffer
                wintypes.DWORD,                     # _In_          DWORD nInBufferSize
                wintypes.LPVOID,                    # _Out_opt_     LPVOID lpOutBuffer
                wintypes.DWORD,                     # _In_          DWORD nOutBufferSize
                wintypes.LPDWORD,                   # _Out_opt_     LPDWORD lpBytesReturned
                wintypes.LPVOID]                    # _Inout_opt_   LPOVERLAPPED lpOverlapped
        DeviceIoControl.restype = wintypes.BOOL
        # allocate a DWORD, and take its reference
        dwBytesReturned = wintypes.DWORD(0)
        lpBytesReturned = ctypes.byref(dwBytesReturned)
        status = DeviceIoControl(devhandle,
                      ioctl,
                      inbuf,
                      inbufsiz,
                      outbuf,
                      outbufsiz,
                      lpBytesReturned,
                      None)
        return status, dwBytesReturned
