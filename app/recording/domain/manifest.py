# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure assembly of the recording manifest from task rows and clip metadata."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Protocol

from app.recording.domain.models import (
    CalibrationMeta,
    ClipMeta,
    ManifestClip,
    RecordingManifest,
)


class TaskRound(Protocol):
    """Theory round fields the manifest needs (``TheoryTaskRead`` fits)."""

    @property
    def question_id(self) -> str: ...

    @property
    def order(self) -> int: ...

    @property
    def round(self) -> int: ...

    @property
    def question_text(self) -> str: ...

    @property
    def question_code(self) -> str | None: ...

    @property
    def answer_text(self) -> str | None: ...


def build_manifest(
    *,
    interview_id: str,
    title: str,
    locale: str,
    selection: Sequence[str],
    started_at: datetime | None,
    completed_at: datetime | None,
    generated_at: datetime,
    tasks: Iterable[TaskRound],
    clips: Iterable[ClipMeta],
    calibration: CalibrationMeta | None,
) -> RecordingManifest:
    """Join recorded clips with their question rounds.

    Only text the candidate saw or said is copied: scores, feedback and rubric
    points are never read, so external analysis stays blind to Rehearse's grade.
    Clips whose round no longer exists are skipped.

    Args:
        interview_id: Session UUID.
        title: Session display title.
        locale: Interview language code.
        selection: Track/level/topic summary lines.
        started_at: Session start time.
        completed_at: Session end time, or None while active.
        generated_at: Timestamp to record in the manifest.
        tasks: Theory rounds of the session.
        clips: Stored clip metadata.
        calibration: Calibration clip metadata, if any.

    Returns:
        Manifest with clips sorted by question order, then round.
    """
    rounds = {(task.question_id, task.round): task for task in tasks}
    entries: list[ManifestClip] = []
    for clip in clips:
        task = rounds.get((clip.question_id, clip.round))
        if task is None:
            continue
        entries.append(
            ManifestClip(
                question_id=task.question_id,
                order=task.order,
                round=task.round,
                question_text=task.question_text,
                question_code=task.question_code,
                answer_text=task.answer_text,
                file=clip.file,
                mime_type=clip.mime_type,
                started_at=clip.started_at,
                duration_s=clip.duration_s,
            )
        )
    entries.sort(key=lambda entry: (entry.order, entry.round))
    return RecordingManifest(
        interview_id=interview_id,
        title=title,
        locale=locale,
        selection=list(selection),
        started_at=started_at,
        completed_at=completed_at,
        generated_at=generated_at,
        calibration=calibration,
        clips=entries,
    )
