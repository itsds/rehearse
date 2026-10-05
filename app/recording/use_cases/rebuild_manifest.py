# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Rebuild ``manifest.json`` from the session's rounds and stored clips."""

from __future__ import annotations

from datetime import UTC, datetime

from app.interview.domain.rules.selection import session_selection_summary_lines
from app.interview.domain.serialization import parse_session_spec
from app.interview.queries.dashboard import InterviewDashboard
from app.interview.queries.projection import load_interview_read
from app.interview.repositories.uow import InterviewUnitOfWork
from app.recording.domain.exceptions import RecordingInterviewNotFoundError
from app.recording.domain.manifest import build_manifest
from app.recording.domain.models import RecordingManifest
from app.recording.repositories.metadata import RecordingMetadataRepository


class RebuildRecordingManifest:
    """Write the manifest so external tools see the latest clips and answers."""

    def __init__(
        self,
        uow: InterviewUnitOfWork,
        metadata: RecordingMetadataRepository,
    ) -> None:
        """Initialize with a read-only unit of work and the metadata repository."""
        self._uow = uow
        self._metadata = metadata

    def execute(self, interview_id: str) -> RecordingManifest | None:
        """Rebuild and save the manifest.

        Args:
            interview_id: Session UUID.

        Returns:
            The manifest, or None when the session has no recordings.

        Raises:
            RecordingInterviewNotFoundError: If the session does not exist.
        """
        interview = load_interview_read(self._uow, interview_id)
        if interview is None:
            raise RecordingInterviewNotFoundError(interview_id)
        clips = self._metadata.clip_metas(interview_id)
        calibration = self._metadata.calibration_meta(interview_id)
        if not clips and calibration is None:
            return None
        session = parse_session_spec(interview.selection_spec)
        manifest = build_manifest(
            interview_id=interview_id,
            title=InterviewDashboard.interview_display_title(interview),
            locale=interview.locale,
            selection=session_selection_summary_lines(session),
            started_at=interview.started_at,
            completed_at=interview.completed_at,
            generated_at=datetime.now(UTC),
            tasks=interview.answers,
            clips=clips,
            calibration=calibration,
        )
        self._metadata.save_manifest(interview_id, manifest)
        return manifest
