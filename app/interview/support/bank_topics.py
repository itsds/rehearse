# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Resolve theory question IDs to their bank track and category."""

from __future__ import annotations

from functools import lru_cache

from app.interview.domain.rules.progress_trend import QuestionTopic
from app.shared import questions as theory_bank


@lru_cache(maxsize=1)
def theory_topic_index() -> dict[str, QuestionTopic]:
    """Build an ``id -> (track, category)`` map across the whole theory bank.

    Levels are deliberately merged: a Kafka junior and a Kafka senior question
    both belong to the ``kafka`` track. Cached for the process lifetime like
    ``bank_text`` — banks only change on restart.

    Returns:
        Mapping of theory question IDs to their topic (first occurrence wins).
    """
    index: dict[str, QuestionTopic] = {}
    for track in theory_bank.list_tracks():
        for level in theory_bank.list_levels(track):
            for category in theory_bank.list_categories(track, level):
                for question in theory_bank.load_category(track, level, category):
                    index.setdefault(
                        question.id,
                        QuestionTopic(track=track, category=category),
                    )
    return index
