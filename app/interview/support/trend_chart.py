# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Lay out trend points as inline-SVG geometry for the Jinja chart macro."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Final

from app.interview.domain.rules.progress_trend import TrendPoint
from app.interview.schemas.progress import (
    ChartTickRead,
    TrendChartRead,
    TrendPointRead,
)
from app.theory.domain.entities import TheorySection

MAX_SCORE: Final = TheorySection.MAX_SCORE_PER_ROUND
_PAD_LEFT: Final = 36.0
_PAD_RIGHT: Final = 16.0
_PAD_TOP: Final = 12.0
_PAD_BOTTOM: Final = 28.0
_MAX_X_TICKS: Final = 5


def build_trend_chart(
    points: Sequence[TrendPoint],
    *,
    chart_id: str,
    subject: str,
    width: int = 640,
    height: int = 220,
) -> TrendChartRead:
    """Compute SVG coordinates, ticks and summary text for a trend chart.

    Sessions are spaced evenly by index rather than by date, so a burst of
    practice on one day stays readable; the x labels carry the dates.

    Args:
        points: Non-empty trend points, oldest first.
        chart_id: Unique DOM id prefix for this chart.
        subject: What the chart measures, for the screen-reader summary.
        width: SVG viewBox width.
        height: SVG viewBox height.

    Returns:
        Chart read model ready for ``_trend_chart.html``.

    Raises:
        ValueError: If ``points`` is empty.
    """
    if not points:
        msg = "build_trend_chart needs at least one point"
        raise ValueError(msg)

    left, right = _PAD_LEFT, width - _PAD_RIGHT
    top, bottom = _PAD_TOP, height - _PAD_BOTTOM

    def x_at(index: int) -> float:
        if len(points) == 1:
            return round((left + right) / 2, 1)
        return round(left + index * (right - left) / (len(points) - 1), 1)

    def y_at(score: float) -> float:
        return round(bottom - score / MAX_SCORE * (bottom - top), 1)

    plotted = [
        TrendPointRead(
            interview_id=point.interview_id,
            url=f"/interview/{point.interview_id}/results",
            title=point.title,
            date_label=_local(point.completed_at).strftime("%d %b"),
            datetime_display=_local(point.completed_at).strftime("%d %b %Y, %H:%M"),
            average_display=f"{point.average:.1f}",
            question_count=point.question_count,
            timed_out_count=point.timed_out_count,
            follow_up_count=point.follow_up_count,
            overall_percent=point.overall_percent,
            x=x_at(index),
            y=y_at(point.average),
        )
        for index, point in enumerate(points)
    ]
    path = "M" + " L".join(f"{p.x},{p.y}" for p in plotted) if len(plotted) > 1 else ""

    latest = points[-1].average
    delta = latest - points[0].average if len(points) > 1 else None
    delta_display = f"{delta:+.1f}" if delta is not None else None
    aria = (
        f"{subject}: {len(points)} rehearsals, latest average first-answer "
        f"score {latest:.1f} out of {MAX_SCORE}"
    )
    if delta_display is not None:
        aria += f", {delta_display} since the first"

    return TrendChartRead(
        chart_id=chart_id,
        width=width,
        height=height,
        plot_left=left,
        plot_right=right,
        plot_top=top,
        plot_bottom=bottom,
        path=path,
        points=plotted,
        y_ticks=[
            ChartTickRead(position=y_at(score), label=str(score))
            for score in range(MAX_SCORE + 1)
        ],
        x_ticks=[
            ChartTickRead(position=plotted[i].x, label=plotted[i].date_label)
            for i in _x_tick_indices(len(plotted))
        ],
        latest_display=f"{latest:.1f}",
        delta_display=delta_display,
        aria_label=aria,
    )


def _x_tick_indices(count: int) -> list[int]:
    """Pick up to ``_MAX_X_TICKS`` evenly spread indices, always first and last."""
    if count <= _MAX_X_TICKS:
        return list(range(count))
    step = (count - 1) / (_MAX_X_TICKS - 1)
    return sorted({round(i * step) for i in range(_MAX_X_TICKS)})


def _local(dt: datetime) -> datetime:
    """Convert a naive-UTC or aware datetime to the server's local timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone()
