# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the progress trend query against an isolated database."""

from datetime import UTC, datetime

import pytest

from app.interview.domain.rules.progress_trend import QuestionTopic
from app.interview.queries.progress import ProgressTrends
from app.interview.repositories.uow import InterviewUnitOfWork
from tests.helpers.interview_seed import seed_two_question_interview
from tests.helpers.progress_seed import seed_scored_session

TOPICS = {
    "k1": QuestionTopic(track="kafka", category="consumers"),
    "k2": QuestionTopic(track="kafka", category="delivery-semantics"),
    "a1": QuestionTopic(track="airflow", category="scheduling"),
    "s1": QuestionTopic(track="system-design", category="caching"),
    "s2": QuestionTopic(track="system-design", category="caching"),
}


@pytest.fixture
def topic_index(monkeypatch):
    monkeypatch.setattr(
        "app.interview.queries.progress.theory_topic_index", lambda: TOPICS
    )


def _seed_history() -> None:
    seed_scored_session(
        "older-kafka",
        [("k1", 0, 2, "a"), ("k1", 1, 3, "b"), ("k2", 0, 4, "c")],
        completed_at=datetime(2026, 10, 1, 9, tzinfo=UTC),
    )
    seed_scored_session(
        "newer-mixed",
        [
            ("k1", 0, 4, "a"),
            ("k2", 0, 4, "b"),
            ("a1", 0, 5, "c"),
            ("s1", 0, 3, "d"),
            ("s2", 0, 0, "[Time expired]"),
        ],
        completed_at=datetime(2026, 10, 3, 9, tzinfo=UTC),
        tracks=("kafka", "airflow", "system-design"),
    )


def test_overall_chart_uses_completed_sessions_oldest_first(
    isolated_db, topic_index
) -> None:
    _seed_history()
    seed_two_question_interview("still-active")
    with InterviewUnitOfWork() as uow:
        chart = ProgressTrends(uow).overall_chart()
    assert chart is not None
    assert [p.interview_id for p in chart.points] == ["older-kafka", "newer-mixed"]
    assert [p.average_display for p in chart.points] == ["3.0", "3.2"]
    assert chart.points[1].question_count == 5
    assert chart.points[1].timed_out_count == 1
    assert chart.points[0].follow_up_count == 1
    assert chart.delta_display == "+0.2"


def test_overall_chart_none_without_completed_sessions(
    isolated_db, topic_index
) -> None:
    seed_two_question_interview("only-active")
    with InterviewUnitOfWork() as uow:
        assert ProgressTrends(uow).overall_chart() is None


def test_page_splits_mixed_session_into_topics(isolated_db, topic_index) -> None:
    _seed_history()
    with InterviewUnitOfWork() as uow:
        page = ProgressTrends(uow).build_page()

    assert page.overall is not None
    topics = {topic.track: topic for topic in page.topics}
    assert set(topics) == {"kafka", "airflow", "system-design"}

    kafka = topics["kafka"]
    assert kafka.label == "Kafka"
    assert kafka.session_count == 2
    assert [p.average_display for p in kafka.chart.points] == ["3.0", "4.0"]
    assert [c.label for c in kafka.categories] == ["Consumers", "Delivery Semantics"]

    assert topics["airflow"].session_count == 1
    assert topics["airflow"].chart.points[0].average_display == "5.0"
    assert topics["system-design"].label == "System Design"
    assert topics["system-design"].chart.points[0].average_display == "1.5"
    # Only the overall chart carries the whole-session percent.
    assert kafka.chart.points[0].overall_percent is None


def test_page_empty_without_sessions(isolated_db, topic_index) -> None:
    with InterviewUnitOfWork() as uow:
        page = ProgressTrends(uow).build_page()
    assert page.overall is None
    assert page.topics == []
