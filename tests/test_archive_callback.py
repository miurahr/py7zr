import errno
import io
import os
import pathlib
import sys
import threading

import pytest

import py7zr
import py7zr.compressor
from py7zr.callbacks import ArchiveCallback
from py7zr.io import BytesIOFactory, MemIO


class RecordingCallback(ArchiveCallback):
    def __init__(self):
        self.events = []
        self.threads = []

    def record(self, *event):
        self.events.append(event)
        self.threads.append(threading.get_ident())

    def report_start_preparation(self):
        self.record("preparation")

    def report_start(self, processing_file_path, processing_bytes):
        self.record("start", processing_file_path, processing_bytes)

    def report_update(self, decompressed_bytes):
        self.record("update", decompressed_bytes)

    def report_end(self, processing_file_path, wrote_bytes):
        self.record("end", processing_file_path, wrote_bytes)

    def report_postprocess(self):
        self.record("postprocess")

    def report_warning(self, message):
        self.record("warning", message)


def read_members(target, password=None):
    target.seek(0)
    factory = BytesIOFactory(limit=100000)
    with py7zr.SevenZipFile(target, password=password) as archive:
        archive.extractall(factory=factory)
    return {name: product.read() for name, product in factory.products.items()}


def write_member(archive, method, source, data, callback):
    if method in ("write", "writeall"):
        getattr(archive, method)(source, "payload", callback=callback)
    elif method == "writef":
        archive.writef(io.BytesIO(data), "payload", callback=callback)
    else:
        archive.writestr(data, "payload", callback=callback)


@pytest.mark.parametrize("method", ["write", "writeall", "writef", "writestr"])
@pytest.mark.parametrize("data", [b"", b"a test payload" * 9])
def test_archive_callback_lifecycle(tmp_path, method, data):
    source = tmp_path / "source"
    source.write_bytes(data)
    callback = RecordingCallback()
    target = io.BytesIO()
    with py7zr.SevenZipFile(target, "w", filters=[{"id": py7zr.FILTER_COPY}]) as archive:
        write_member(archive, method, source, data, callback)
        assert callback.events == [
            ("preparation",),
            ("start", "payload", str(len(data))),
            ("update", str(len(data))),
            ("end", "payload", str(len(data))),
            ("postprocess",),
        ]
        assert callback.threads == [threading.get_ident()] * len(callback.events)
    assert len(callback.events) == 5  # Closing the archive does not retain the callback.
    assert read_members(target) == {"payload": data}


@pytest.mark.parametrize("stream_type", [io.BytesIO, io.BufferedReader])
@pytest.mark.parametrize("offset", [0, 3, 15, 20])
def test_archive_callback_stream_position(stream_type, offset):
    data = b"stream contents"
    raw = io.BytesIO(data)
    stream = raw if stream_type is io.BytesIO else stream_type(raw)
    stream.seek(offset)
    callback = RecordingCallback()
    target = io.BytesIO()
    with py7zr.SevenZipFile(target, "w") as archive:
        archive.writef(stream, "stream", callback=callback)
    expected = data[offset:]
    assert callback.events[1] == ("start", "stream", str(len(expected)))
    assert sum(int(e[1]) for e in callback.events if e[0] == "update") == len(expected)
    assert not stream.closed
    assert read_members(target) == {"stream": expected}


@pytest.mark.parametrize("use_callback", [False, True])
@pytest.mark.parametrize("offset", [0, 3, 15, 20])
def test_archive_callback_memio_position(use_callback, offset):
    data = b"stream contents"
    source = MemIO("input", BytesIOFactory(limit=100))
    source.open()
    source.write(data)
    source.seek(offset)
    callback = RecordingCallback()
    kwargs = {"callback": callback} if use_callback else {}
    target = io.BytesIO()
    expected = data[offset:]
    try:
        with py7zr.SevenZipFile(target, "w") as archive:
            archive.writef(source, "stream", **kwargs)
            assert archive.files[0].uncompressed == len(expected)
        assert not source.closed
        if use_callback:
            assert callback.events[1] == ("start", "stream", str(len(expected)))
            assert sum(int(e[1]) for e in callback.events if e[0] == "update") == len(expected)
        assert read_members(target) == {"stream": expected}
    finally:
        source.close()


@pytest.mark.parametrize("use_callback", [False, True])
def test_archive_callback_rejects_unopened_memio(use_callback):
    source = MemIO("input", BytesIOFactory(limit=100))
    callback = RecordingCallback()
    kwargs = {"callback": callback} if use_callback else {}
    with py7zr.SevenZipFile(io.BytesIO(), "w") as archive:
        before = archive.fp.tell()
        with pytest.raises(ValueError, match="MemIO.*open"):
            archive.writef(source, "stream", **kwargs)
        assert archive.fp.tell() == before
        assert archive.getnames() == []
    assert callback.events == ([("preparation",)] if use_callback else [])
    assert source.closed


@pytest.mark.parametrize("data", ["你好, archive", bytearray(b"abc"), memoryview(b"def")])
def test_archive_callback_writestr_data_types(data):
    target = io.BytesIO()
    callback = RecordingCallback()
    expected = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    with py7zr.SevenZipFile(target, "w") as archive:
        archive.writestr(data, "text", callback=callback)
    assert callback.events[1] == ("start", "text", str(len(expected)))
    assert callback.events[2] == ("update", str(len(expected)))
    assert read_members(target) == {"text": expected}


def test_archive_callback_recursive(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a-empty").write_bytes(b"")
    (source / "b-directory").mkdir()
    (source / "b-directory" / "nested").write_bytes(b"nested")
    (source / "c-file").write_bytes(b"last")
    callback = RecordingCallback()
    target = io.BytesIO()
    with py7zr.SevenZipFile(target, "w", filters=[{"id": py7zr.FILTER_COPY}]) as archive:
        archive.writeall(source, "tree", callback=callback)
    assert callback.events.count(("preparation",)) == 1
    assert callback.events.count(("postprocess",)) == 1
    expected = [
        ("tree", 0),
        ("tree/a-empty", 0),
        ("tree/b-directory", 0),
        ("tree/b-directory/nested", 6),
        ("tree/c-file", 4),
    ]
    assert [e[1:] for e in callback.events if e[0] == "start"] == [(name, str(size)) for name, size in expected]
    assert [e[1:] for e in callback.events if e[0] == "end"] == [(name, str(size)) for name, size in expected]
    assert sum(int(e[1]) for e in callback.events if e[0] == "update") == 10
    assert read_members(target) == {"tree/a-empty": b"", "tree/b-directory/nested": b"nested", "tree/c-file": b"last"}


@pytest.mark.parametrize("mode", ["w", "x"])
@pytest.mark.parametrize("password", [None, "secret"])
def test_archive_callback_modes_and_solid_flush(tmp_path, mode, password):
    target = tmp_path / "archive.7z"
    callback = RecordingCallback()
    with py7zr.SevenZipFile(target, mode, password=password) as archive:
        before = archive.fp.tell()
        archive.writestr(b"a" * 1000, "first", callback=callback)
        first_written = archive.fp.tell() - before
        assert ("end", "first", str(first_written)) in callback.events
        archive.writestr(b"b" * 1000, "second", callback=callback)
        snapshot = list(callback.events)
        archive.writestr(b"unobserved", "third")
        assert callback.events == snapshot
    assert callback.events == snapshot
    with target.open("rb") as stream:
        expected = {"first": b"a" * 1000, "second": b"b" * 1000, "third": b"unobserved"}
        assert read_members(stream, password=password) == expected


def test_archive_callback_append(tmp_path):
    target = tmp_path / "archive.7z"
    with py7zr.SevenZipFile(target, "w") as archive:
        archive.writestr(b"existing", "old")
    callback = RecordingCallback()
    with py7zr.SevenZipFile(target, "a") as archive:
        archive.writestr(b"appended", "new", callback=callback)
    assert callback.events[1] == ("start", "new", "8")
    assert callback.events[2] == ("update", "8")
    with target.open("rb") as stream:
        assert read_members(stream) == {"old": b"existing", "new": b"appended"}


@pytest.mark.parametrize("elapsed, expected", [(0, ["11"]), (0.5, ["8", "3"]), (1, ["4", "4", "3"])])
def test_archive_callback_incremental_input(monkeypatch, elapsed, expected):
    monkeypatch.setattr(py7zr.compressor, "get_default_blocksize", lambda: 4)
    ticks = iter(range(100))
    monkeypatch.setattr(py7zr.compressor.time, "monotonic", lambda: next(ticks) * elapsed)
    callback = RecordingCallback()
    target = io.BytesIO()
    with py7zr.SevenZipFile(target, "w") as archive:
        archive.writestr(b"abcdefghijk", "large", callback=callback)
    assert [e for e in callback.events if e[0] == "update"] == [("update", size) for size in expected]
    assert read_members(target) == {"large": b"abcdefghijk"}


@pytest.mark.parametrize("method", ["write", "writeall", "writef", "writestr"])
@pytest.mark.parametrize("callback", [object(), RecordingCallback])
def test_archive_callback_rejects_invalid_before_writing(tmp_path, method, callback):
    source = tmp_path / "source"
    source.write_bytes(b"payload")
    with py7zr.SevenZipFile(io.BytesIO(), "w") as archive:
        before = archive.fp.tell()
        with pytest.raises(ValueError, match="ArchiveCallback"):
            write_member(archive, method, source, b"payload", callback)
        assert archive.fp.tell() == before
        assert archive.getnames() == []


@pytest.mark.parametrize("stage", ["preparation", "start", "update", "end", "postprocess"])
@pytest.mark.parametrize("error_number", [errno.ELOOP, errno.ENOENT])
def test_archive_callback_error_propagates_from_recursive_write(tmp_path, stage, error_number):
    source = tmp_path / "source"
    source.mkdir()
    (source / "file").write_bytes(b"data")
    error = OSError(error_number, "callback failed")

    class FailingCallback(RecordingCallback):
        def record(self, *event):
            super().record(*event)
            is_file = event[0] in ("start", "end") and event[1] == "tree/file"
            is_input = event[0] == "update" and event[1] != "0"
            if event[0] == stage and (is_file or is_input or stage in ("preparation", "postprocess")):
                raise error

    callback = FailingCallback()
    with pytest.raises(OSError) as caught:
        with py7zr.SevenZipFile(io.BytesIO(), "w", dereference=True) as archive:
            archive.writeall(source, "tree", callback=callback)
    assert caught.value is error
    assert callback.events[-1][0] == stage


@pytest.mark.parametrize("operation", ["is_symlink", "listdir"])
@pytest.mark.parametrize("error_number", [errno.ELOOP, errno.ENOENT])
def test_archive_callback_skips_traversal_loops(tmp_path, monkeypatch, operation, error_number):
    if error_number == errno.ENOENT and sys.platform != "win32":
        pytest.skip("ENOENT loop workaround applies only on Windows")
    source = tmp_path / "source"
    source.mkdir()
    problem = source / "loop"
    problem.mkdir()
    (source / "z-file").write_bytes(b"valid")
    error = OSError(error_number, "loop")
    owner = pathlib.Path if operation == "is_symlink" else os
    original = getattr(owner, operation)

    def fail_on_loop(path):
        if pathlib.Path(path) == problem:
            raise error
        return original(path)

    monkeypatch.setattr(owner, operation, fail_on_loop)
    callback = RecordingCallback()
    target = io.BytesIO()
    with py7zr.SevenZipFile(target, "w", dereference=True) as archive:
        archive.writeall(source, "tree", callback=callback)
    assert callback.events[-1] == ("postprocess",)
    assert ("start", "tree/z-file", "5") in callback.events
    assert read_members(target) == {"tree/z-file": b"valid"}


def test_archive_callback_source_error():
    error = OSError(errno.EIO, "input failed")

    class BrokenInput(io.BytesIO):
        def read(self, size=-1):
            if self.tell():
                raise error
            return super().read(4)

    source = BrokenInput(b"data remains")
    callback = RecordingCallback()
    with pytest.raises(OSError) as caught:
        with py7zr.SevenZipFile(io.BytesIO(), "w") as archive:
            archive.writef(source, "broken", callback=callback)
    assert caught.value is error
    assert not source.closed
    assert not any(e[0] in ("end", "postprocess") for e in callback.events)


def test_archive_callback_output_error():
    error = OSError(errno.EIO, "output failed")

    class BrokenOutput(io.BytesIO):
        fail = False

        def write(self, data):
            if self.fail:
                self.fail = False
                raise error
            return super().write(data)

    target = BrokenOutput()
    callback = RecordingCallback()
    archive = py7zr.SevenZipFile(target, "w", filters=[{"id": py7zr.FILTER_COPY}])
    try:
        with pytest.raises(OSError) as caught:
            target.fail = True
            archive.writestr(b"payload", "broken", callback=callback)
    finally:
        target.fail = False
        archive.close()
    assert caught.value is error
    assert not any(e[0] in ("update", "end", "postprocess") for e in callback.events)


@pytest.mark.skipif(os.name == "nt", reason="symlink payload semantics are tested on Unix")
@pytest.mark.parametrize("dereference", [False, True])
def test_archive_callback_symlink(tmp_path, dereference):
    source = tmp_path / "source"
    source.mkdir()
    (source / "目标").write_bytes(b"target data")
    link = source / "link"
    link.symlink_to("目标")
    callback = RecordingCallback()
    target = io.BytesIO()
    with py7zr.SevenZipFile(target, "w", dereference=dereference) as archive:
        archive.write(link, "link", callback=callback)
    expected = b"target data" if dereference else "目标".encode("utf-8")
    assert callback.events[1] == ("start", "link", str(len(expected)))
    assert callback.events[2] == ("update", str(len(expected)))
    assert read_members(target) == {"link": expected}
