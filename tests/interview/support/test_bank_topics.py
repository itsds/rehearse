# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the question ID to topic index."""

from unittest.mock import MagicMock

from app.interview.domain.rules.progress_trend import QuestionTopic
from app.interview.support.bank_topics import theory_topic_index


def test_index_merges_levels_under_track(monkeypatch) -> None:
    theory_topic_index.cache_clear()
    banks = {
        ("kafka", "junior", "basics"): [MagicMock(id="kj-1")],
        ("kafka", "senior", "consumers"): [MagicMock(id="ks-1")],
        ("airflow", "senior", "scheduling"): [MagicMock(id="af-1")],
    }
    module = "app.interview.support.bank_topics.theory_bank"
    monkeypatch.setattr(f"{module}.list_tracks", lambda: ["airflow", "kafka"])
    monkeypatch.setattr(
        f"{module}.list_levels",
        lambda track: sorted({lvl for t, lvl, _ in banks if t == track}),
    )
    monkeypatch.setattr(
        f"{module}.list_categories",
        lambda track, level: [c for t, lvl, c in banks if (t, lvl) == (track, level)],
    )
    monkeypatch.setattr(
        f"{module}.load_category",
        lambda track, level, category: banks[(track, level, category)],
    )
    try:
        index = theory_topic_index()
    finally:
        theory_topic_index.cache_clear()
    assert index == {
        "kj-1": QuestionTopic(track="kafka", category="basics"),
        "ks-1": QuestionTopic(track="kafka", category="consumers"),
        "af-1": QuestionTopic(track="airflow", category="scheduling"),
    }


def test_real_banks_resolve_known_tracks() -> None:
    theory_topic_index.cache_clear()
    index = theory_topic_index()
    assert index
    assert {topic.track for topic in index.values()} >= {"kafka", "python"}
