# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Recording metadata and the on-disk ``manifest.json`` contract (version 1).

The manifest is read by tools outside Rehearse (e.g. a local video-review app),
so field names are a public contract: add fields, never rename or remove them
without bumping ``version``. Rehearse scores and feedback are intentionally
absent so external analysis is not anchored by them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ClipMeta(BaseModel):
    """Sidecar metadata stored next to one answer-round clip.

    Attributes:
        file: Video file name inside the interview's recording folder.
        question_id: Bank question ID.
        order: Question display order (1-based).
        round: Follow-up round (0 = main question).
        mime_type: Stored media type (``video/webm`` or ``video/mp4``).
        size_bytes: File size.
        started_at: When the clip started (question shown or recording enabled).
        duration_s: Clip length reported by the browser.
    """

    model_config = ConfigDict(frozen=True)

    file: str
    question_id: str
    order: int
    round: int
    mime_type: str
    size_bytes: int
    started_at: datetime | None = None
    duration_s: float | None = None


class CalibrationSegment(BaseModel):
    """Where the candidate was asked to look during part of the calibration clip.

    Attributes:
        target: ``camera`` (the lens) or ``screen`` (centre of the screen).
        start_s: Segment start within the clip, in seconds.
        end_s: Segment end within the clip, in seconds.
    """

    model_config = ConfigDict(frozen=True)

    target: Literal["camera", "screen"]
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)


class CalibrationMeta(BaseModel):
    """Sidecar metadata for the gaze-calibration clip.

    Attributes:
        file: Video file name.
        mime_type: Stored media type.
        size_bytes: File size.
        recorded_at: When the calibration was recorded.
        segments: Look-at-camera / look-at-screen segments.
    """

    model_config = ConfigDict(frozen=True)

    file: str
    mime_type: str
    size_bytes: int
    recorded_at: datetime | None = None
    segments: list[CalibrationSegment]


class ManifestClip(BaseModel):
    """One answer round in the manifest: the question, the answer text and the clip.

    Attributes:
        question_id: Bank question ID.
        order: Question display order (1-based).
        round: Follow-up round (0 = main question).
        question_text: Question or follow-up as shown to the candidate.
        question_code: Optional code snippet shown with the question.
        answer_text: The candidate's final answer text (transcript or typed).
        file: Video file name.
        mime_type: Stored media type.
        started_at: When the clip started.
        duration_s: Clip length.
    """

    model_config = ConfigDict(frozen=True)

    question_id: str
    order: int
    round: int
    question_text: str
    question_code: str | None
    answer_text: str | None
    file: str
    mime_type: str
    started_at: datetime | None
    duration_s: float | None


class RecordingManifest(BaseModel):
    """``manifest.json``: everything an external tool needs to read a rehearsal.

    Attributes:
        version: Manifest schema version.
        interview_id: Session UUID.
        title: Session display title.
        locale: Interview language code.
        selection: Human-readable track/level/topic lines.
        started_at: Session start time.
        completed_at: Session end time, or None while active.
        generated_at: When this manifest was written.
        calibration: Gaze-calibration clip, or None when not recorded.
        clips: Recorded answer rounds in question order.
    """

    model_config = ConfigDict(frozen=True)

    version: Literal[1] = 1
    interview_id: str
    title: str
    locale: str
    selection: list[str]
    started_at: datetime | None
    completed_at: datetime | None
    generated_at: datetime
    calibration: CalibrationMeta | None
    clips: list[ManifestClip]
