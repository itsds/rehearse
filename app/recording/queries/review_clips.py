# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Recording links for the theory review page."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.recording.repositories.metadata import RecordingMetadataRepository


class ReviewRecordingsRead(BaseModel):
    """Replay data for one session.

    Attributes:
        clips: Video URL per round, keyed ``"<question_id>:<round>"``.
        total_bytes: Combined size of the session's recording files.
        total_mb: The same size formatted for display, e.g. ``"42.1"``.
        delete_url: Endpoint that deletes all of the session's recordings.
    """

    model_config = ConfigDict(frozen=True)

    clips: dict[str, str]
    total_bytes: int
    total_mb: str
    delete_url: str

    @property
    def has_any(self) -> bool:
        """Whether there is anything to replay or delete."""
        return self.total_bytes > 0


def review_recordings(
    metadata: RecordingMetadataRepository,
    interview_id: str,
) -> ReviewRecordingsRead:
    """Build replay links for every stored answer clip of a session."""
    base = f"/interview/{interview_id}/recordings"
    clips = {
        f"{meta.question_id}:{meta.round}": f"{base}/{meta.file}"
        for meta in metadata.clip_metas(interview_id)
    }
    total = metadata.storage.total_bytes(interview_id)
    return ReviewRecordingsRead(
        clips=clips,
        total_bytes=total,
        total_mb=f"{total / (1024 * 1024):.1f}",
        delete_url=base,
    )
