# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the progress page and the dashboard trend card."""

from datetime import UTC, datetime

import pytest

from app.interview.domain.rules.progress_trend import QuestionTopic
from tests.helpers.progress_seed import seed_scored_session

TOPICS = {
    "k1": QuestionTopic(track="kafka", category="consumers"),
    "a1": QuestionTopic(track="airflow", category="scheduling"),
}


@pytest.fixture
def topic_index(monkeypatch):
    monkeypatch.setattr(
        "app.interview.queries.progress.theory_topic_index", lambda: TOPICS
    )


def _seed(count: int) -> None:
    for day in range(1, count + 1):
        seed_scored_session(
            f"trend-{day}",
            [("k1", 0, 3, "a"), ("a1", 0, 4, "b")],
            completed_at=datetime(2026, 10, day, 9, tzinfo=UTC),
            tracks=("kafka", "airflow"),
        )


class TestDashboardTrendCard:
    def test_hidden_without_completed_sessions(
        self, client, isolated_db, topic_index
    ) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert "Progress trend" not in response.text
        assert "progress_trend.js" not in response.text

    def test_hint_with_one_session(self, client, isolated_db, topic_index) -> None:
        _seed(1)
        response = client.get("/")
        assert "Progress trend" in response.text
        assert "Complete one more to see your trend" in response.text
        assert "data-trend-chart" not in response.text

    def test_chart_with_two_sessions(self, client, isolated_db, topic_index) -> None:
        _seed(2)
        response = client.get("/")
        assert "data-trend-chart" in response.text
        assert 'href="/progress"' in response.text
        assert "/interview/trend-1/results" in response.text
        assert "progress_trend.js" in response.text
        assert "SECRET-FEEDBACK" not in response.text


class TestProgressPage:
    def test_empty_state(self, client, isolated_db, topic_index) -> None:
        response = client.get("/progress")
        assert response.status_code == 200
        assert "No scored rehearsals yet" in response.text

    def test_overall_and_topic_charts(self, client, isolated_db, topic_index) -> None:
        _seed(2)
        response = client.get("/progress")
        assert response.status_code == 200
        assert 'id="trend-overall"' in response.text
        assert 'id="trend-kafka"' in response.text
        assert 'id="trend-airflow"' in response.text
        assert "Scheduling" in response.text

    def test_single_session_topic_shows_hint(
        self, client, isolated_db, topic_index
    ) -> None:
        _seed(1)
        response = client.get("/progress")
        assert "1 rehearsal so far" in response.text

    def test_nav_has_progress_link(self, client, isolated_db, topic_index) -> None:
        response = client.get("/progress")
        assert '<a href="/progress" class="nav-link">Progress</a>' in response.text
