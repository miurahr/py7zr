import stat
import struct
import sys

if sys.platform == "win32" and sys.version_info < (3, 8) :
    from ctypes import WinDLL

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

    def _check_bit(val, flag):
        return bool(val & flag == flag)

    def _parse_reparse_buffer(buf):
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

    def is_reparse_point(path):
        return _check_bit(GetFileAttributesW(path), stat.FILE_ATTRIBUTE_REPARSE_POINT)

    def readlink(path):
        # FILE_FLAG_OPEN_REPARSE_POINT alone is not enough if 'path'
        # is a symbolic link to a directory or a NTFS junction.
        # We need to set FILE_FLAG_BACKUP_SEMANTICS as well.
        # See https://docs.microsoft.com/en-us/windows/desktop/api/fileapi/nf-fileapi-createfilea
        handle = CreateFileW(path, GENERIC_READ, 0, None, OPEN_EXISTING,
                             FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, 0)
        buf = DeviceIoControl(handle, FSCTL_GET_REPARSE_POINT, None, MAXIMUM_REPARSE_DATA_BUFFER_SIZE)
        CloseHandle(handle)
        result = _parse_reparse_buffer(buf)
        if result['tag'] in (IO_REPARSE_TAG_MOUNT_POINT, IO_REPARSE_TAG_SYMLINK):
            offset = result['substitute_name_offset']
            ending = offset + result['substitute_name_length']
            rpath = result['buffer'][offset:ending].decode('UTF-16-LE')
        else:
            rpath = result['buffer']
        if result['tag'] == IO_REPARSE_TAG_MOUNT_POINT:
            rpath[:0] = '\\??\\'
        return rpath
