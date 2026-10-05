# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Progress trend read models: overall (dashboard) and per topic (``/progress``)."""

from __future__ import annotations

from typing import Final

from app.interview.domain.rules.bank_selection import track_label
from app.interview.domain.rules.progress_trend import (
    UNMAPPED_TRACK,
    SessionScores,
    TrendPoint,
    category_stats,
    score_first_answers,
    tracks_by_recent_practice,
    trend_points,
)
from app.interview.domain.serialization import parse_session_spec
from app.interview.queries.dashboard import InterviewDashboard
from app.interview.queries.projection import load_recent_completed_interview_reads
from app.interview.repositories.uow import InterviewUnitOfWork
from app.interview.schemas.interview import InterviewRead
from app.interview.schemas.progress import (
    CategoryStatRead,
    ProgressPageRead,
    TopicProgressRead,
    TrendChartRead,
)
from app.interview.support.bank_topics import theory_topic_index
from app.interview.support.trend_chart import build_trend_chart

DASHBOARD_SESSION_LIMIT: Final = 20
PROGRESS_PAGE_SESSION_LIMIT: Final = 50
# viewBox sizes roughly match the rendered width, so 11px axis text stays ~11px.
_OVERALL_SIZE: Final = (960, 260)
_TOPIC_SIZE: Final = (480, 200)


class ProgressTrends:
    """Build first-answer progress trends from completed sessions."""

    def __init__(self, uow: InterviewUnitOfWork) -> None:
        """Initialize with the active unit of work."""
        self._uow = uow

    def overall_chart(
        self,
        limit: int = DASHBOARD_SESSION_LIMIT,
    ) -> TrendChartRead | None:
        """Build the overall trend across every theory question.

        Args:
            limit: Most recent completed sessions to include.

        Returns:
            Chart, or None when no completed session has a scored answer.
        """
        points = trend_points(self._load_sessions(limit))
        if not points:
            return None
        return _overall_chart(points)

    def build_page(
        self,
        limit: int = PROGRESS_PAGE_SESSION_LIMIT,
    ) -> ProgressPageRead:
        """Build the overall chart plus one chart per practised track.

        A question counts once in the overall chart and once in its own track,
        so a mixed session adds a point to every track it touched.

        Args:
            limit: Most recent completed sessions to include.

        Returns:
            Progress page read model.
        """
        sessions = self._load_sessions(limit)
        overall_points = trend_points(sessions)
        overall = _overall_chart(overall_points) if overall_points else None
        topics: list[TopicProgressRead] = []
        for track in tracks_by_recent_practice(sessions):
            label = _track_display(track)
            points = trend_points(sessions, track=track)
            topics.append(
                TopicProgressRead(
                    track=track,
                    label=label,
                    session_count=len(points),
                    chart=build_trend_chart(
                        points,
                        chart_id=f"trend-{track}",
                        subject=label,
                        width=_TOPIC_SIZE[0],
                        height=_TOPIC_SIZE[1],
                    ),
                    categories=[
                        CategoryStatRead(
                            label=_category_display(stat.category),
                            question_count=stat.question_count,
                            average_display=f"{stat.average:.1f}",
                            latest_display=f"{stat.latest_average:.1f}",
                        )
                        for stat in category_stats(sessions, track)
                    ],
                )
            )
        return ProgressPageRead(overall=overall, topics=topics)

    def _load_sessions(self, limit: int) -> list[SessionScores]:
        """Load completed sessions and score their first answers."""
        topics = theory_topic_index()
        sessions: list[SessionScores] = []
        for interview in load_recent_completed_interview_reads(self._uow, limit=limit):
            if interview.completed_at is None:
                continue
            sessions.append(
                SessionScores(
                    interview_id=interview.id,
                    completed_at=interview.completed_at,
                    title=InterviewDashboard.interview_display_title(interview),
                    questions=score_first_answers(
                        interview.answers,
                        topics,
                        fallback_track=_single_theory_track(interview),
                    ),
                    overall_percent=_overall_percent(interview),
                )
            )
        return sessions


def _overall_chart(points: list[TrendPoint]) -> TrendChartRead:
    """Lay out the full-width overall trend chart."""
    return build_trend_chart(
        points,
        chart_id="trend-overall",
        subject="Overall progress",
        width=_OVERALL_SIZE[0],
        height=_OVERALL_SIZE[1],
    )


def _single_theory_track(interview: InterviewRead) -> str | None:
    """Return the session's only theory track, or None for mixed sessions."""
    session = parse_session_spec(interview.selection_spec)
    tracks = {source.track for source in session.theory_selection.sources}
    return tracks.pop() if len(tracks) == 1 else None


def _overall_percent(interview: InterviewRead) -> int | None:
    """Return the whole-session score as a percent, or None when unknown."""
    if interview.score is None:
        return None
    feedback = interview.overall_feedback
    breakdown = feedback.get("score_breakdown") if feedback else None
    max_score = InterviewDashboard.compute_max_score(interview, breakdown)
    if max_score <= 0:
        return None
    return round(interview.score * 100 / max_score)


def _track_display(track: str) -> str:
    """Return the display name for a track slug."""
    return "Unmapped questions" if track == UNMAPPED_TRACK else track_label(track)


def _category_display(category: str | None) -> str:
    """Return the display name for a category slug."""
    if category is None:
        return "Other"
    return category.replace("-", " ").replace("_", " ").title()
