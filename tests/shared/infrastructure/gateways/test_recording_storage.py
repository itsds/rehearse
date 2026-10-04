# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for filesystem recording storage."""

import io

import pytest

from app.shared.infrastructure.gateways.recording_storage import (
    RecordingStorage,
    StorageLimitExceededError,
)


def test_save_and_read_back(tmp_path) -> None:
    storage = RecordingStorage(tmp_path)
    size = storage.save_stream("int-1", "q01-r0.webm", io.BytesIO(b"abc"), max_bytes=10)
    assert size == 3
    assert (tmp_path / "int-1" / "q01-r0.webm").read_bytes() == b"abc"
    storage.write_text("int-1", "manifest.json", "{}")
    assert storage.read_text("int-1", "manifest.json") == "{}"
    assert storage.list_names("int-1") == ["manifest.json", "q01-r0.webm"]
    assert storage.total_bytes("int-1") == 5
    assert (tmp_path / "int-1" / "q01-r0.webm").stat().st_mode & 0o777 == 0o644


def test_size_limit_leaves_no_partial_file(tmp_path) -> None:
    storage = RecordingStorage(tmp_path)
    with pytest.raises(StorageLimitExceededError):
        storage.save_stream("int-1", "q01-r0.webm", io.BytesIO(b"x" * 11), max_bytes=10)
    assert list((tmp_path / "int-1").iterdir()) == []


@pytest.mark.parametrize("interview_id", ["../x", "a/b", "", "x" * 65])
def test_rejects_unsafe_interview_ids(tmp_path, interview_id) -> None:
    with pytest.raises(ValueError):
        RecordingStorage(tmp_path).list_names(interview_id)


@pytest.mark.parametrize("name", ["../x.webm", ".hidden", "a/b.webm"])
def test_rejects_unsafe_file_names(tmp_path, name) -> None:
    with pytest.raises(ValueError):
        RecordingStorage(tmp_path).write_text("int-1", name, "x")


def test_missing_folder_is_empty_and_delete_all(tmp_path) -> None:
    storage = RecordingStorage(tmp_path)
    assert storage.list_names("int-1") == []
    assert storage.path_for("int-1", "q01-r0.webm") is None
    assert storage.delete_all("int-1") is False
    storage.write_text("int-1", "manifest.json", "{}")
    assert storage.delete_all("int-1") is True
    assert not (tmp_path / "int-1").exists()
