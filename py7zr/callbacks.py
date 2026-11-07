#!/usr/bin/python -u
#
# p7zr library
#
# Copyright (c) 2020,2021 Hiroshi Miura <miurahr@linux.com>
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

from abc import ABC, abstractmethod


class Callback(ABC):
    """Abstract base class for progress callbacks."""

    @abstractmethod
    def report_start_preparation(self) -> None:
        """report a start of preparation event such as making list of files and looking into its properties."""
        pass  # noqa

    @abstractmethod
    def report_start(self, processing_file_path: str, processing_bytes: str) -> None:
        """report a start event of specified archive file and its input bytes."""
        pass  # noqa

    @abstractmethod
    def report_update(self, decompressed_bytes: str) -> None:
        """report an event when large file is being extracted more than 1 second or when extraction is finished.
        receives a number of decompressed bytes since the last update."""
        pass  # noqa

    @abstractmethod
    def report_end(self, processing_file_path: str, wrote_bytes: str) -> None:
        """report an end event of specified archive file and its output bytes."""
        pass  # noqa

    @abstractmethod
    def report_warning(self, message: str) -> None:
        """report an warning event with its message"""
        pass  # noqa

    @abstractmethod
    def report_postprocess(self) -> None:
        """report a start of post processing event such as set file properties and permissions or creating symlinks."""
        pass  # noqa


class ExtractCallback(Callback):
    """Abstract base class for extraction progress callbacks."""

    pass


class ArchiveCallback(Callback):
    """Progress callbacks for ``write``, ``writeall``, ``writef`` and ``writestr``.

    Methods run synchronously in the calling thread. Each write call reports
    preparation once, then start/update/end events for each member, followed
    by postprocess once on success. Byte counts are decimal strings, as in
    :class:`ExtractCallback`.

    ``report_start`` receives the archive member name and its input size.
    Directories have size zero; stored symlinks use the UTF-8 encoded link
    target's size. ``report_update`` receives input bytes processed since the
    previous update, approximately once per second and at the end of each
    member. Empty members receive a zero-byte update.

    ``report_end`` receives compressed bytes emitted while writing the member.
    Solid compression can buffer output across members, so this is not the
    member's final compressed size. It excludes compressor flushing and archive
    headers, which are written on close. ``report_postprocess`` marks the end
    of this write call, not completion of the archive. No callback is retained
    or called by ``close``.

    Callback exceptions propagate to the caller and stop the write operation.
    An interrupted write may leave an incomplete archive; discard that archive.
    Callbacks should not modify the archive or input while it is being written.
    """

    pass
