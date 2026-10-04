# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for pure progress trend rules."""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.interview.domain.rules.progress_trend import (
    UNMAPPED_TRACK,
    QuestionTopic,
    SessionScores,
    category_stats,
    score_first_answers,
    tracks_by_recent_practice,
    trend_points,
)

KAFKA = QuestionTopic(track="kafka", category="consumers")
KAFKA_TX = QuestionTopic(track="kafka", category="transactions")
AIRFLOW = QuestionTopic(track="airflow", category="scheduling")
SYSDES = QuestionTopic(track="system-design", category="caching")


@dataclass(frozen=True)
class FakeRound:
    question_id: str
    round: int
    score: int | None
    answer_text: str | None = "an answer"


def _session(
    sid: str,
    day: int,
    rounds: list[FakeRound],
    topics: dict[str, QuestionTopic],
    *,
    fallback: str | None = None,
    percent: int | None = None,
) -> SessionScores:
    return SessionScores(
        interview_id=sid,
        completed_at=datetime(2026, 10, day, tzinfo=UTC),
        title=f"Session {sid}",
        questions=score_first_answers(rounds, topics, fallback_track=fallback),
        overall_percent=percent,
    )


class TestScoreFirstAnswers:
    def test_uses_round_zero_only_and_counts_follow_ups(self) -> None:
        scored = score_first_answers(
            [
                FakeRound("k1", 0, 3),
                FakeRound("k1", 1, 5),
                FakeRound("k1", 2, 1),
                FakeRound("k2", 0, 5),
            ],
            {"k1": KAFKA, "k2": KAFKA},
            fallback_track=None,
        )
        assert [(q.question_id, q.score, q.follow_up_count) for q in scored] == [
            ("k1", 3, 2),
            ("k2", 5, 0),
        ]

    def test_timeout_counts_as_zero_and_unscored_rounds_skipped(self) -> None:
        scored = score_first_answers(
            [
                FakeRound("k1", 0, 0, "[Time expired]"),
                FakeRound("k2", 0, None, None),
            ],
            {"k1": KAFKA, "k2": KAFKA},
            fallback_track=None,
        )
        assert len(scored) == 1
        assert scored[0].score == 0
        assert scored[0].timed_out is True

    def test_unknown_id_uses_fallback_track_or_unmapped(self) -> None:
        single = score_first_answers(
            [FakeRound("gone", 0, 4)], {}, fallback_track="kafka"
        )
        assert single[0].topic == QuestionTopic(track="kafka", category=None)
        mixed = score_first_answers([FakeRound("gone", 0, 4)], {}, fallback_track=None)
        assert mixed[0].topic.track == UNMAPPED_TRACK


class TestTrendPoints:
    def test_mixed_session_splits_by_track_but_counts_all_overall(self) -> None:
        topics = {
            "k1": KAFKA,
            "k2": KAFKA,
            "a1": AIRFLOW,
            "s1": SYSDES,
            "s2": SYSDES,
        }
        session = _session(
            "mix",
            4,
            [
                FakeRound("k1", 0, 4),
                FakeRound("k2", 0, 2),
                FakeRound("a1", 0, 5),
                FakeRound("s1", 0, 3),
                FakeRound("s2", 0, 1),
            ],
            topics,
            percent=60,
        )
        overall = trend_points([session])
        assert overall[0].question_count == 5
        assert overall[0].average == pytest.approx(3.0)
        assert overall[0].overall_percent == 60

        kafka = trend_points([session], track="kafka")
        assert (kafka[0].question_count, kafka[0].average) == (2, 3.0)
        assert kafka[0].overall_percent is None
        assert trend_points([session], track="airflow")[0].question_count == 1
        assert trend_points([session], track="system-design")[0].average == 2.0

    def test_points_sorted_oldest_first_and_sessions_without_track_skipped(
        self,
    ) -> None:
        topics = {"k1": KAFKA, "a1": AIRFLOW}
        newer = _session("new", 9, [FakeRound("k1", 0, 5)], topics)
        older = _session("old", 2, [FakeRound("k1", 0, 2)], topics)
        airflow_only = _session("af", 5, [FakeRound("a1", 0, 4)], topics)
        points = trend_points([newer, airflow_only, older], track="kafka")
        assert [p.interview_id for p in points] == ["old", "new"]

    def test_timeouts_and_follow_ups_summed(self) -> None:
        session = _session(
            "s",
            1,
            [
                FakeRound("k1", 0, 0, "[Time expired]"),
                FakeRound("k2", 0, 3),
                FakeRound("k2", 1, 4),
            ],
            {"k1": KAFKA, "k2": KAFKA},
        )
        point = trend_points([session])[0]
        assert point.average == 1.5
        assert point.timed_out_count == 1
        assert point.follow_up_count == 1

    def test_session_without_scored_questions_has_no_point(self) -> None:
        empty = _session("e", 1, [], {})
        assert trend_points([empty]) == []


def test_tracks_by_recent_practice() -> None:
    topics = {"k1": KAFKA, "a1": AIRFLOW, "s1": SYSDES}
    sessions = [
        _session("1", 1, [FakeRound("a1", 0, 3), FakeRound("s1", 0, 3)], topics),
        _session("2", 5, [FakeRound("k1", 0, 3)], topics),
    ]
    assert tracks_by_recent_practice(sessions) == ["kafka", "airflow", "system-design"]


def test_category_stats_weakest_first_with_latest() -> None:
    topics = {"c1": KAFKA, "c2": KAFKA, "t1": KAFKA_TX}
    sessions = [
        _session("1", 1, [FakeRound("c1", 0, 2), FakeRound("t1", 0, 5)], topics),
        _session("2", 3, [FakeRound("c1", 0, 4), FakeRound("c2", 0, 5)], topics),
    ]
    stats = category_stats(sessions, "kafka")
    assert [s.category for s in stats] == ["consumers", "transactions"]
    consumers = stats[0]
    assert consumers.question_count == 3
    assert consumers.average == pytest.approx(11 / 3)
    assert consumers.latest_average == 4.5
    assert stats[1].latest_average == 5.0
