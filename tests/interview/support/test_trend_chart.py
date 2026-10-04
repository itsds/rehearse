# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for trend chart SVG layout."""

from datetime import UTC, datetime

import pytest

from app.interview.domain.rules.progress_trend import TrendPoint
from app.interview.support.trend_chart import build_trend_chart


def _point(day: int, average: float) -> TrendPoint:
    return TrendPoint(
        interview_id=f"id-{day}",
        completed_at=datetime(2026, 10, day, 12, tzinfo=UTC),
        title="Kafka Interview",
        average=average,
        question_count=3,
        timed_out_count=0,
        follow_up_count=1,
        overall_percent=70,
    )


def test_points_span_plot_and_map_scores_to_y() -> None:
    chart = build_trend_chart(
        [_point(1, 0.0), _point(2, 5.0), _point(3, 2.5)],
        chart_id="c",
        subject="Overall",
        width=640,
        height=220,
    )
    xs = [p.x for p in chart.points]
    assert xs[0] == chart.plot_left
    assert xs[-1] == chart.plot_right
    assert chart.points[0].y == chart.plot_bottom
    assert chart.points[1].y == chart.plot_top
    assert chart.points[2].y == pytest.approx((chart.plot_top + chart.plot_bottom) / 2)
    assert chart.path.startswith(f"M{xs[0]},")
    assert chart.path.count(" L") == 2
    assert [t.label for t in chart.y_ticks] == ["0", "1", "2", "3", "4", "5"]
    assert chart.points[0].url == "/interview/id-1/results"


def test_summary_and_delta() -> None:
    chart = build_trend_chart(
        [_point(1, 3.2), _point(2, 3.8)], chart_id="c", subject="Kafka"
    )
    assert chart.latest_display == "3.8"
    assert chart.delta_display == "+0.6"
    assert "Kafka: 2 rehearsals" in chart.aria_label


def test_single_point_is_centered_without_line_or_delta() -> None:
    chart = build_trend_chart([_point(1, 4.0)], chart_id="c", subject="Kafka")
    assert chart.path == ""
    assert chart.delta_display is None
    assert chart.points[0].x == pytest.approx((chart.plot_left + chart.plot_right) / 2)


def test_x_ticks_capped_and_include_first_and_last() -> None:
    points = [_point(day, 3.0) for day in range(1, 21)]
    chart = build_trend_chart(points, chart_id="c", subject="Overall")
    assert len(chart.x_ticks) == 5
    assert chart.x_ticks[0].position == chart.points[0].x
    assert chart.x_ticks[-1].position == chart.points[-1].x


def test_empty_points_rejected() -> None:
    with pytest.raises(ValueError):
        build_trend_chart([], chart_id="c", subject="Overall")
