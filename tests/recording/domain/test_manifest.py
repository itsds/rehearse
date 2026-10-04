# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the pure manifest builder."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.recording.domain.manifest import build_manifest
from app.recording.domain.models import CalibrationMeta, CalibrationSegment, ClipMeta


@dataclass(frozen=True)
class Round:
    question_id: str
    order: int
    round: int
    question_text: str
    question_code: str | None
    answer_text: str | None
    score: int | None = 4
    feedback: str | None = "SECRET-FEEDBACK"


def _clip(qid: str, order: int, round_num: int) -> ClipMeta:
    return ClipMeta(
        file=f"q{order:02d}-r{round_num}.webm",
        question_id=qid,
        order=order,
        round=round_num,
        mime_type="video/webm",
        size_bytes=10,
        duration_s=12.5,
    )


def _build(clips, calibration=None):
    return build_manifest(
        interview_id="int-1",
        title="Kafka Interview",
        locale="en",
        selection=["Kafka / senior: Consumers"],
        started_at=datetime(2026, 10, 4, 9, tzinfo=UTC),
        completed_at=None,
        generated_at=datetime(2026, 10, 4, 10, tzinfo=UTC),
        tasks=[
            Round("k1", 1, 0, "What is a consumer group?", None, "It is..."),
            Round("k1", 1, 1, "What triggers a rebalance?", None, "When..."),
            Round("k2", 2, 0, "Explain this:", "print(1)", None),
        ],
        clips=clips,
        calibration=calibration,
    )


def test_joins_clips_with_rounds_in_order() -> None:
    manifest = _build([_clip("k2", 2, 0), _clip("k1", 1, 1), _clip("k1", 1, 0)])
    assert [(c.order, c.round) for c in manifest.clips] == [(1, 0), (1, 1), (2, 0)]
    first = manifest.clips[0]
    assert first.question_text == "What is a consumer group?"
    assert first.answer_text == "It is..."
    assert first.file == "q01-r0.webm"
    assert first.duration_s == 12.5
    assert manifest.clips[2].question_code == "print(1)"
    assert manifest.version == 1


def test_skips_clips_without_matching_round() -> None:
    manifest = _build([_clip("gone", 9, 0), _clip("k1", 1, 0)])
    assert [c.question_id for c in manifest.clips] == ["k1"]


def test_includes_calibration() -> None:
    calibration = CalibrationMeta(
        file="calibration.webm",
        mime_type="video/webm",
        size_bytes=5,
        segments=[
            CalibrationSegment(target="camera", start_s=0, end_s=5),
            CalibrationSegment(target="screen", start_s=5, end_s=10),
        ],
    )
    manifest = _build([], calibration)
    assert manifest.calibration is not None
    assert [s.target for s in manifest.calibration.segments] == ["camera", "screen"]


def test_never_contains_scores_or_feedback() -> None:
    dumped = _build([_clip("k1", 1, 0)]).model_dump_json()
    assert "SECRET-FEEDBACK" not in dumped
    assert "score" not in dumped
    assert "feedback" not in dumped
