# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure rules for the progress trend: first-answer scores per session and topic."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Protocol

from app.theory.domain.entities import TheoryTask

UNMAPPED_TRACK: Final = "unmapped"


class AnswerRound(Protocol):
    """Read-only view of one theory round, as needed by the trend rules.

    A ``Protocol`` is structural typing (like a Java interface that classes
    satisfy implicitly), so ``TheoryTaskRead`` fits without importing it here.
    """

    @property
    def question_id(self) -> str: ...

    @property
    def round(self) -> int: ...

    @property
    def score(self) -> int | None: ...

    @property
    def answer_text(self) -> str | None: ...


@dataclass(frozen=True, slots=True)
class QuestionTopic:
    """Bank location of a theory question, with levels merged.

    Attributes:
        track: Track slug (``kafka``), or ``UNMAPPED_TRACK``.
        category: Category slug, or None when it cannot be resolved.
    """

    track: str
    category: str | None


@dataclass(frozen=True, slots=True)
class ScoredQuestion:
    """First-answer result for one question in a session.

    Attributes:
        question_id: Bank question ID.
        topic: Resolved track and category.
        score: Round-0 score (0 when the timer expired).
        timed_out: Whether the first answer timed out.
        follow_up_count: Follow-up rounds asked for this question.
    """

    question_id: str
    topic: QuestionTopic
    score: int
    timed_out: bool
    follow_up_count: int


@dataclass(frozen=True, slots=True)
class SessionScores:
    """Scored first answers of one completed session.

    Attributes:
        interview_id: Session UUID.
        completed_at: When the session ended.
        title: Display title of the session.
        questions: Scored first answers in question order.
        overall_percent: Whole-session score percent, or None when unknown.
    """

    interview_id: str
    completed_at: datetime
    title: str
    questions: tuple[ScoredQuestion, ...]
    overall_percent: int | None


@dataclass(frozen=True, slots=True)
class TrendPoint:
    """One plotted session: average first-answer score over selected questions.

    Attributes:
        interview_id: Session UUID.
        completed_at: When the session ended.
        title: Display title of the session.
        average: Mean round-0 score on the 0–5 scale.
        question_count: Questions included in the average.
        timed_out_count: Included questions whose first answer timed out.
        follow_up_count: Follow-ups asked on the included questions.
        overall_percent: Whole-session percent (overall trend only).
    """

    interview_id: str
    completed_at: datetime
    title: str
    average: float
    question_count: int
    timed_out_count: int
    follow_up_count: int
    overall_percent: int | None


@dataclass(frozen=True, slots=True)
class CategoryStat:
    """First-answer summary of one category within a track.

    Attributes:
        category: Category slug, or None for unresolved questions.
        question_count: First answers scored in this category.
        average: Mean round-0 score across all sessions.
        latest_average: Mean round-0 score in the most recent session.
    """

    category: str | None
    question_count: int
    average: float
    latest_average: float


def score_first_answers(
    answers: Iterable[AnswerRound],
    topics: Mapping[str, QuestionTopic],
    *,
    fallback_track: str | None,
) -> tuple[ScoredQuestion, ...]:
    """Collect round-0 scores per question; follow-ups are only counted.

    Rounds without a score (never answered or never evaluated) are skipped.
    A timed-out first answer keeps its score of 0 so skipping is not rewarded.

    Args:
        answers: Theory rounds of one session in display order.
        topics: Question ID to topic index built from the banks.
        fallback_track: Track to use for IDs missing from the banks, when the
            session had a single track; None files them under ``unmapped``.

    Returns:
        Scored first answers in question order.
    """
    rounds = list(answers)
    follow_ups: dict[str, int] = {}
    for item in rounds:
        if item.round > 0:
            follow_ups[item.question_id] = follow_ups.get(item.question_id, 0) + 1

    fallback = QuestionTopic(track=fallback_track or UNMAPPED_TRACK, category=None)
    scored: list[ScoredQuestion] = []
    for item in rounds:
        if item.round != 0 or item.score is None:
            continue
        scored.append(
            ScoredQuestion(
                question_id=item.question_id,
                topic=topics.get(item.question_id, fallback),
                score=item.score,
                timed_out=(item.answer_text or "").strip()
                == TheoryTask.TIME_EXPIRED_ANSWER_TEXT,
                follow_up_count=follow_ups.get(item.question_id, 0),
            )
        )
    return tuple(scored)


def trend_points(
    sessions: Sequence[SessionScores],
    *,
    track: str | None = None,
) -> list[TrendPoint]:
    """Build one point per session, oldest first.

    Args:
        sessions: Scored sessions in any order.
        track: Limit to questions of this track; None uses every question.

    Returns:
        Points for sessions with at least one matching question.
    """
    points: list[TrendPoint] = []
    for session in sorted(sessions, key=lambda s: s.completed_at):
        selected = _questions_for(session, track)
        if not selected:
            continue
        points.append(
            TrendPoint(
                interview_id=session.interview_id,
                completed_at=session.completed_at,
                title=session.title,
                average=_mean(q.score for q in selected),
                question_count=len(selected),
                timed_out_count=sum(1 for q in selected if q.timed_out),
                follow_up_count=sum(q.follow_up_count for q in selected),
                overall_percent=session.overall_percent if track is None else None,
            )
        )
    return points


def tracks_by_recent_practice(sessions: Sequence[SessionScores]) -> list[str]:
    """Return every practised track, most recently practised first.

    Args:
        sessions: Scored sessions in any order.

    Returns:
        Track slugs; ties keep alphabetical order.
    """
    last_seen: dict[str, datetime] = {}
    for session in sessions:
        for question in session.questions:
            track = question.topic.track
            if track not in last_seen or session.completed_at > last_seen[track]:
                last_seen[track] = session.completed_at
    return sorted(last_seen, key=lambda t: (-last_seen[t].timestamp(), t))


def category_stats(
    sessions: Sequence[SessionScores],
    track: str,
) -> list[CategoryStat]:
    """Summarize first answers per category of one track, weakest first.

    Args:
        sessions: Scored sessions in any order.
        track: Track slug to summarize.

    Returns:
        One row per category, sorted by average score then name.
    """
    scores: dict[str | None, list[int]] = {}
    latest: dict[str | None, tuple[datetime, list[int]]] = {}
    for session in sessions:
        for question in _questions_for(session, track):
            category = question.topic.category
            scores.setdefault(category, []).append(question.score)
            seen = latest.get(category)
            if seen is None or session.completed_at > seen[0]:
                latest[category] = (session.completed_at, [question.score])
            elif session.completed_at == seen[0]:
                seen[1].append(question.score)

    stats = [
        CategoryStat(
            category=category,
            question_count=len(values),
            average=_mean(values),
            latest_average=_mean(latest[category][1]),
        )
        for category, values in scores.items()
    ]
    return sorted(stats, key=lambda s: (s.average, s.category or "~"))


def _questions_for(
    session: SessionScores,
    track: str | None,
) -> list[ScoredQuestion]:
    """Return the session's questions, optionally limited to one track."""
    if track is None:
        return list(session.questions)
    return [q for q in session.questions if q.topic.track == track]


def _mean(values: Iterable[int]) -> float:
    """Return the arithmetic mean of a non-empty iterable of scores."""
    items = list(values)
    return sum(items) / len(items)
