import pathlib
import stat
import struct
import sys
from typing import Dict, Union

from py7zr.exceptions import InternalError

if sys.platform == "win32" and sys.version_info < (3, 8):
    import ctypes
    from ctypes import WinDLL
    import ctypes.wintypes as wintypes

    _stdcall_libraries = {}
    _stdcall_libraries['kernel32'] = WinDLL('kernel32')
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

    def _parse_reparse_buffer(buf) -> Dict[str, bytes]:
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

        data = {'tag': struct.unpack('<I', buf[:4])[0],
                'data_length': struct.unpack('<H', buf[4:6])[0],
                'reserved': struct.unpack('<H', buf[6:8])[0]}
        buf = buf[8:]

        if data['tag'] in (IO_REPARSE_TAG_MOUNT_POINT, IO_REPARSE_TAG_SYMLINK):
            keys = ['substitute_name_offset',
                    'substitute_name_length',
                    'print_name_offset',
                    'print_name_length']
            if data['tag'] == IO_REPARSE_TAG_SYMLINK:
                keys.append('flags')

            # Parsing
            for k in keys:
                if k == 'flags':
                    fmt, sz = '<I', 4
                else:
                    fmt, sz = '<H', 2
                data[k] = struct.unpack(fmt, buf[:sz])[0]
                buf = buf[sz:]

        # Using the offset and lengths grabbed, we'll set the buffer.
        data['buffer'] = buf
        return data

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
        handle = CreateFileW(target, GENERIC_READ, 0, None, OPEN_EXISTING,
                             FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, 0)  # first arg is c_wchar_p
        buf = ctypes.create_string_buffer(MAXIMUM_REPARSE_DATA_BUFFER_SIZE)
        status, _ = _DeviceIoControl(handle, FSCTL_GET_REPARSE_POINT, None, 0, buf, MAXIMUM_REPARSE_DATA_BUFFER_SIZE)
        CloseHandle(handle)
        if not status:
            raise InternalError("Failed to access reparse point.")
        result = _parse_reparse_buffer(bytes(buf))
        if result['tag'] in (IO_REPARSE_TAG_MOUNT_POINT, IO_REPARSE_TAG_SYMLINK):
            offset = result['substitute_name_offset']
            ending = offset + result['substitute_name_length']
            rpath = result['buffer'][offset:ending].decode('UTF-16-LE')
        else:
            rpath = result['buffer']
        if result['tag'] == IO_REPARSE_TAG_MOUNT_POINT:
            rpath[:0] = '\\??\\'
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
