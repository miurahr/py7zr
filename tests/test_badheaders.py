# Malformed archive header test cases
#
# Every test here feeds a hostile *header* to the parser and asserts that it is
# rejected with Bad7zFile.  A 7z header is parsed in full by SevenZipFile() before
# a single byte is extracted, so anything reachable from here runs against an
# attacker-supplied file that the caller has not yet chosen to trust.
#
# Attacks on archive *content* -- path traversal, symlink escapes, zip-slip --
# belong in test_badfiles.py instead.  See docs/contribution.rst.
import io

import pytest

import py7zr.archiveinfo
from py7zr import SevenZipFile
from py7zr.exceptions import Bad7zFile
from py7zr.helpers import calculate_crc32

# A UINT64 whose first byte is 0xff is followed by 8 raw bytes, so this is the
# shortest encoding of 2**64-1 and the cheapest way to ask for a huge allocation.
HUGE_UINT64 = b"\xff" + b"\xff" * 8


def _craft_archive(nextheader: bytes, packed: bytes = b"") -> bytes:
    """Build a 7z file whose signature header CRC is valid but whose next header is hostile.

    The signature header CRC is checked before the next header is parsed, so it has
    to be correct for the parser to reach the code under test.  calccrc() computes
    it the same way the writer does.
    """
    sig = py7zr.archiveinfo.SignatureHeader()
    sig.nextheaderofs = len(packed)
    sig.calccrc(len(nextheader), calculate_crc32(nextheader))
    buf = io.BytesIO()
    sig.write(buf)
    buf.seek(32)
    buf.write(packed)
    buf.write(nextheader)
    return buf.getvalue()


# PackInfo/UnpackInfo describing a single COPY-coded folder over 16 packed bytes
_PACK_INFO = b"\x06\x00\x01\x09\x10\x00"
_UNPACK_INFO = b"\x07\x0b\x01\x00\x01\x01\x00"


#
# Parser level: hand-built byte strings driven straight into an archiveinfo class.
# These pin the precise structure that is rejected, without the noise of a
# surrounding archive.
#


@pytest.mark.security
def test_filesinfo_numfiles_bomb():
    # numfiles = 2**64-1 declared in 9 bytes
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.FilesInfo.retrieve(io.BytesIO(HUGE_UINT64 + b"\x00"))


@pytest.mark.security
def test_filesinfo_numfiles_not_backed_by_input():
    # numfiles = 255 is modest, but only one byte of payload follows it
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.FilesInfo.retrieve(io.BytesIO(b"\x80\xff" + b"\x00"))


@pytest.mark.security
def test_filesinfo_property_size_bomb():
    # one file, then a property claiming to be 2**64-1 bytes long
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.FilesInfo.retrieve(io.BytesIO(b"\x01\x0e" + HUGE_UINT64 + b"\x00"))


@pytest.mark.security
def test_unpackinfo_numfolders_bomb():
    # UnpackInfo._read consumes the FOLDER id itself
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.UnpackInfo.retrieve(io.BytesIO(b"\x0b" + HUGE_UINT64 + b"\x00"))


@pytest.mark.security
def test_substreamsinfo_num_unpackstreams_bomb():
    folders = [py7zr.archiveinfo.Folder()]
    folders[0].unpacksizes = [1]
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.SubstreamsInfo.retrieve(io.BytesIO(b"\x0d" + HUGE_UINT64 + b"\x00"), 1, folders)


@pytest.mark.security
def test_substreamsinfo_substream_total_bomb():
    # each folder's count is small, but the sum is what sizes the digest vectors
    folders = []
    for _ in range(4):
        folder = py7zr.archiveinfo.Folder()
        folder.unpacksizes = [1]
        folders.append(folder)
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.SubstreamsInfo.retrieve(io.BytesIO(b"\x0d\x7f\x7f\x7f\x7f\x00"), 4, folders)


@pytest.mark.security
@pytest.mark.parametrize(
    "blob, reason",
    [
        (HUGE_UINT64, "num_coders"),
        (b"\x01\x11\x21" + HUGE_UINT64 + HUGE_UINT64, "numinstreams/numoutstreams"),
        (b"\x01\x21\x21" + HUGE_UINT64, "coder property length"),
    ],
)
def test_folder_count_bombs(blob, reason):
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.Folder.retrieve(io.BytesIO(blob))


@pytest.mark.security
def test_read_crcs_bomb():
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.read_crcs(io.BytesIO(b"\x00\x00\x00\x00"), 1 << 40)


@pytest.mark.security
def test_read_boolean_all_defined_bomb():
    # with checkall the all-defined byte returns [True] * count without reading
    # any further input at all
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.read_boolean(io.BytesIO(b"\x01"), 1 << 40, checkall=True)


@pytest.mark.security
def test_truncated_folder_raises_bad7zfile():
    # walking off the end of the header used to surface a bare TypeError from
    # ord(b"") rather than Bad7zFile
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.Folder.retrieve(io.BytesIO(b"\x02\x01\x00"))


@pytest.mark.security
def test_truncated_uint64_raises_bad7zfile():
    # first byte announces trailing bytes that are not there
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.read_uint64(io.BytesIO(b"\xc0\x01"))


@pytest.mark.security
def test_unterminated_utf16_raises_bad7zfile():
    # an unterminated name used to spin to MAX_LENGTH and then seek before the
    # start of the buffer, raising ValueError
    with pytest.raises(Bad7zFile):
        py7zr.archiveinfo.read_utf16(io.BytesIO(b"t\x00e\x00s\x00t\x00"))


#
# Whole file level: a complete 7z file through the public constructor.  These
# prove the parser-level guards are actually reachable by an attacker, which the
# tests above do not.
#


@pytest.mark.security
def test_truncated_signature_header():
    # a file with the 7z magic but a signature header truncated before its
    # uint32/uint64 fields used to raise a bare struct.error instead of Bad7zFile
    magic = b"7z\xbc\xaf\x27\x1c\x00\x04"
    for data in (magic, magic + b"\x00" * 10):
        with pytest.raises(Bad7zFile):
            SevenZipFile(io.BytesIO(data), "r")


@pytest.mark.security
def test_header_numfiles_bomb():
    # FILES_INFO declaring 2**64-1 files; used to allocate that many dicts
    nextheader = b"\x01\x05" + HUGE_UINT64 + b"\x00\x00"
    with pytest.raises(Bad7zFile):
        SevenZipFile(io.BytesIO(_craft_archive(nextheader)), "r")


@pytest.mark.security
def test_next_header_size_exceeds_archive():
    # fp.read() pre-allocates, so an oversized nextheadersize must be caught first
    sig = py7zr.archiveinfo.SignatureHeader()
    sig.nextheaderofs = 0
    sig.calccrc(1 << 62, 0)
    buf = io.BytesIO()
    sig.write(buf)
    with pytest.raises(Bad7zFile):
        SevenZipFile(io.BytesIO(buf.getvalue()), "r")


@pytest.mark.security
def test_encoded_header_size_bomb():
    # encoded header declaring a 2**64-1 byte decoded size
    nextheader = b"\x17" + _PACK_INFO + _UNPACK_INFO + b"\x0c" + HUGE_UINT64 + b"\x00\x00"
    with pytest.raises(Bad7zFile):
        SevenZipFile(io.BytesIO(_craft_archive(nextheader, packed=b"\x00" * 16)), "r")


@pytest.mark.security
@pytest.mark.timeout(60)
def test_encoded_header_truncated_stream_does_not_hang():
    # decoded size 1000 but only 16 packed bytes exist.  The decompressor returns
    # b"" forever once the packed stream is spent, which used to spin the loop in
    # Header._read at 100% CPU indefinitely.  The timeout marker is the assertion:
    # without the no-progress guard this test never returns.
    nextheader = b"\x17" + _PACK_INFO + _UNPACK_INFO + b"\x0c\x83\xe8\x00\x00"
    with pytest.raises(Bad7zFile):
        SevenZipFile(io.BytesIO(_craft_archive(nextheader, packed=b"\x00" * 16)), "r")
