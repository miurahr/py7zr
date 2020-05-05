import pathlib
import stat
import sys
from typing import Optional, Union

from py7zr.exceptions import InternalError

if sys.platform == "win32" and sys.version_info < (3, 8):
    import ctypes
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

    def readlink(path: Union[str, pathlib.Path]) -> Optional[str]:
        # FILE_FLAG_OPEN_REPARSE_POINT alone is not enough if 'path'
        # is a symbolic link to a directory or a NTFS junction.
        # We need to set FILE_FLAG_BACKUP_SEMANTICS as well.
        # See https://docs.microsoft.com/en-us/windows/desktop/api/fileapi/nf-fileapi-createfilea
        if isinstance(path, pathlib.Path):
            target = str(path.resolve())
        else:
            target = str(path)
        if not is_reparse_point(target):
            return None
        CreateFileW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                wintypes.DWORD, wintypes.HANDLE]
        CreateFileW.restype = wintypes.HANDLE
        DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.LPVOID,
                                    wintypes.DWORD, wintypes.LPDWORD, wintypes.LPVOID]
        DeviceIoControl.restype = wintypes.BOOL
        handle = wintypes.HANDLE(CreateFileW(target, GENERIC_READ, 0, None, OPEN_EXISTING,
                                             FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, 0))
        buf = ReparseBuffer()
        dwBytesRet = wintypes.DWORD(0)
        lpBytesRet = ctypes.byref(dwBytesRet)
        status = DeviceIoControl(handle, FSCTL_GET_REPARSE_POINT, None, 0, ctypes.byref(buf),
                                 MAXIMUM_REPARSE_DATA_BUFFER_SIZE, lpBytesRet, None)
        CloseHandle(handle)
        if not status:
            raise InternalError("Failed IOCTL access to get REPARSE_POINT.")
        if buf.reparse_tag == IO_REPARSE_TAG_SYMLINK:
            offset = buf.substitute_name_offset
            ending = offset + buf.substitute_name_length
            rpath = b''.join(buf.symlink.path_buffer[offset:ending]).decode('UTF-16-LE')
        elif buf.reparse_tag == IO_REPARSE_TAG_MOUNT_POINT:
            offset = buf.substitute_name_offset
            ending = offset + buf.substitute_name_length
            rpath = b''.join([i.to_bytes(1, byteorder='little') for i in buf.mount.path_buffer[offset:ending]]).decode('UTF-16-LE')
        else:
            rpath = ''
        return rpath
