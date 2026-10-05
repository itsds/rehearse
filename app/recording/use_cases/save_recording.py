# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Store uploaded answer clips and the calibration clip."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import BinaryIO

from app.interview.repositories.uow import InterviewUnitOfWork
from app.recording.domain import clips as clip_rules
from app.recording.domain.exceptions import (
    RecordingInterviewNotFoundError,
    RecordingRoundNotFoundError,
    RecordingTooLargeError,
    UnsupportedRecordingTypeError,
)
from app.recording.domain.models import CalibrationMeta, CalibrationSegment, ClipMeta
from app.recording.repositories.metadata import RecordingMetadataRepository
from app.recording.use_cases.rebuild_manifest import RebuildRecordingManifest
from app.shared.infrastructure.gateways.recording_storage import (
    StorageLimitExceededError,
)
from app.theory.domain.exceptions import TheoryTaskNotFoundError


class SaveRecording:
    """Validate an upload against the session and write it to disk.

    The unit of work is only read from (no write transaction), so streaming a
    large video to disk never holds an SQLite lock (CLAUDE.md rule 5).
    """

    def __init__(
        self,
        uow: InterviewUnitOfWork,
        metadata: RecordingMetadataRepository,
    ) -> None:
        """Initialize with a read-only unit of work and the metadata repository."""
        self._uow = uow
        self._metadata = metadata

    def save_clip(
        self,
        *,
        interview_id: str,
        question_id: str,
        round_num: int,
        content_type: str | None,
        source: BinaryIO,
        started_at: datetime | None,
        duration_s: float | None,
    ) -> ClipMeta:
        """Store the clip for one question round and refresh the manifest.

        Re-uploading the same round replaces the previous clip.

        Raises:
            RecordingInterviewNotFoundError: Unknown session.
            RecordingRoundNotFoundError: Unknown question round.
            UnsupportedRecordingTypeError: Not WebM/MP4 video.
            RecordingTooLargeError: Over ``MAX_CLIP_BYTES``.
        """
        if self._uow.interviews.get_aggregate(interview_id) is None:
            raise RecordingInterviewNotFoundError(interview_id)
        section = self._uow.theory_sections.get_aggregate(interview_id)
        if section is None:
            raise RecordingRoundNotFoundError(f"{question_id}:{round_num}")
        try:
            task = section.find_task(question_id, round_num)
        except TheoryTaskNotFoundError as exc:
            raise RecordingRoundNotFoundError(f"{question_id}:{round_num}") from exc

        extension = self._extension(content_type)
        stem = clip_rules.clip_stem(task.order, round_num)
        filename = f"{stem}.{extension}"
        size = self._store(interview_id, filename, source)
        self._remove_other_formats(interview_id, stem, keep=filename)
        meta = ClipMeta(
            file=filename,
            question_id=question_id,
            order=task.order,
            round=round_num,
            mime_type=clip_rules.media_type_for(filename),
            size_bytes=size,
            started_at=started_at,
            duration_s=duration_s,
        )
        self._metadata.save_clip_meta(interview_id, stem, meta)
        RebuildRecordingManifest(self._uow, self._metadata).execute(interview_id)
        return meta

    def save_calibration(
        self,
        *,
        interview_id: str,
        content_type: str | None,
        source: BinaryIO,
        recorded_at: datetime | None,
        segments: Sequence[CalibrationSegment],
    ) -> CalibrationMeta:
        """Store the gaze-calibration clip (latest one wins) and refresh the manifest.

        Raises:
            RecordingInterviewNotFoundError: Unknown session.
            UnsupportedRecordingTypeError: Not WebM/MP4 video.
            RecordingTooLargeError: Over ``MAX_CLIP_BYTES``.
        """
        if self._uow.interviews.get_aggregate(interview_id) is None:
            raise RecordingInterviewNotFoundError(interview_id)
        stem = clip_rules.CALIBRATION_STEM
        filename = f"{stem}.{self._extension(content_type)}"
        size = self._store(interview_id, filename, source)
        self._remove_other_formats(interview_id, stem, keep=filename)
        meta = CalibrationMeta(
            file=filename,
            mime_type=clip_rules.media_type_for(filename),
            size_bytes=size,
            recorded_at=recorded_at,
            segments=list(segments),
        )
        self._metadata.save_calibration_meta(interview_id, meta)
        RebuildRecordingManifest(self._uow, self._metadata).execute(interview_id)
        return meta

    @staticmethod
    def _extension(content_type: str | None) -> str:
        extension = clip_rules.extension_for(content_type)
        if extension is None:
            raise UnsupportedRecordingTypeError(content_type or "unknown")
        return extension

    def _store(self, interview_id: str, filename: str, source: BinaryIO) -> int:
        try:
            return self._metadata.storage.save_stream(
                interview_id, filename, source, max_bytes=clip_rules.MAX_CLIP_BYTES
            )
        except StorageLimitExceededError as exc:
            raise RecordingTooLargeError(filename) from exc

    def _remove_other_formats(self, interview_id: str, stem: str, *, keep: str) -> None:
        """Drop a same-round clip in the other container (WebM vs MP4)."""
        for extension in ("webm", "mp4"):
            name = f"{stem}.{extension}"
            if name != keep:
                self._metadata.storage.remove(interview_id, name)
