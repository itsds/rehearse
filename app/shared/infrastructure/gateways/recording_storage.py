# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Filesystem storage for interview recordings under ``data/recordings/``."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import BinaryIO, Final

_ID_RE: Final = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_NAME_RE: Final = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_CHUNK_BYTES: Final = 1024 * 1024
# mkstemp creates 0600 files; use normal permissions so the host user can open
# recordings written by the container user.
_FILE_MODE: Final = 0o644


class StorageLimitExceededError(Exception):
    """The streamed upload was larger than the allowed size."""


class RecordingStorage:
    """Store recording files per interview: ``<root>/<interview_id>/<name>``.

    Every write goes to a temp file first and is then renamed into place, so a
    reader (or a crash) never sees a half-written video or manifest.
    """

    def __init__(self, root: Path) -> None:
        """Initialize with the recordings root directory (created lazily)."""
        self._root = root

    def save_stream(
        self,
        interview_id: str,
        name: str,
        source: BinaryIO,
        *,
        max_bytes: int,
    ) -> int:
        """Copy ``source`` into ``name``, refusing anything over ``max_bytes``.

        Args:
            interview_id: Session UUID (folder name).
            name: Target file name.
            source: Readable binary stream.
            max_bytes: Size limit.

        Returns:
            Bytes written.

        Raises:
            StorageLimitExceededError: If the stream is larger than ``max_bytes``.
        """
        folder = self._folder(interview_id, create=True)
        fd, tmp_name = tempfile.mkstemp(dir=folder, prefix=".upload-")
        written = 0
        try:
            with os.fdopen(fd, "wb") as target:
                while chunk := source.read(_CHUNK_BYTES):
                    written += len(chunk)
                    if written > max_bytes:
                        raise StorageLimitExceededError(name)
                    target.write(chunk)
            os.chmod(tmp_name, _FILE_MODE)
            os.replace(tmp_name, folder / self._checked(name))
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
        return written

    def write_text(self, interview_id: str, name: str, text: str) -> None:
        """Atomically write a UTF-8 text file (metadata, manifest)."""
        folder = self._folder(interview_id, create=True)
        fd, tmp_name = tempfile.mkstemp(dir=folder, prefix=".write-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as target:
                target.write(text)
            os.chmod(tmp_name, _FILE_MODE)
            os.replace(tmp_name, folder / self._checked(name))
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    def read_text(self, interview_id: str, name: str) -> str | None:
        """Return a text file's content, or None when it does not exist."""
        path = self.path_for(interview_id, name)
        return path.read_text(encoding="utf-8") if path is not None else None

    def path_for(self, interview_id: str, name: str) -> Path | None:
        """Return the path of an existing file, or None."""
        folder = self._folder(interview_id, create=False)
        path = folder / self._checked(name)
        return path if path.is_file() else None

    def list_names(self, interview_id: str) -> list[str]:
        """Return the sorted file names stored for an interview (no temp files)."""
        folder = self._folder(interview_id, create=False)
        if not folder.is_dir():
            return []
        return sorted(
            entry.name
            for entry in folder.iterdir()
            if entry.is_file() and not entry.name.startswith(".")
        )

    def remove(self, interview_id: str, name: str) -> None:
        """Delete one file if it exists."""
        path = self.path_for(interview_id, name)
        if path is not None:
            path.unlink()

    def total_bytes(self, interview_id: str) -> int:
        """Return the combined size of an interview's stored files."""
        folder = self._folder(interview_id, create=False)
        return sum(
            (folder / name).stat().st_size for name in self.list_names(interview_id)
        )

    def delete_all(self, interview_id: str) -> bool:
        """Delete an interview's recording folder.

        Returns:
            True when something was deleted.
        """
        folder = self._folder(interview_id, create=False)
        if not folder.is_dir():
            return False
        shutil.rmtree(folder)
        return True

    def _folder(self, interview_id: str, *, create: bool) -> Path:
        """Return the interview folder, rejecting IDs that could escape the root."""
        if not _ID_RE.fullmatch(interview_id):
            msg = f"Invalid interview id for recordings: {interview_id!r}"
            raise ValueError(msg)
        folder = self._root / interview_id
        if create:
            folder.mkdir(parents=True, exist_ok=True)
        return folder

    @staticmethod
    def _checked(name: str) -> str:
        """Reject file names with path separators or a leading dot."""
        if not _NAME_RE.fullmatch(name) or name.startswith("."):
            msg = f"Invalid recording file name: {name!r}"
            raise ValueError(msg)
        return name
