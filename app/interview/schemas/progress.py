# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Read models for the progress trend chart and the per-topic progress page."""

from pydantic import BaseModel, ConfigDict


class TrendPointRead(BaseModel):
    """One plotted session on a trend chart.

    Attributes:
        interview_id: Session UUID.
        url: Results page of the session.
        title: Session display title.
        date_label: Short date for the x axis (``04 Oct``).
        datetime_display: Full local date and time for the tooltip.
        average_display: Average first-answer score, one decimal (``3.8``).
        question_count: Questions included in the average.
        timed_out_count: Included questions whose first answer timed out.
        follow_up_count: Follow-ups asked on the included questions.
        overall_percent: Whole-session score percent (overall chart only).
        x: SVG x coordinate.
        y: SVG y coordinate.
    """

    model_config = ConfigDict(frozen=True)

    interview_id: str
    url: str
    title: str
    date_label: str
    datetime_display: str
    average_display: str
    question_count: int
    timed_out_count: int
    follow_up_count: int
    overall_percent: int | None
    x: float
    y: float


class ChartTickRead(BaseModel):
    """Axis tick: a horizontal gridline (y) or a date label (x).

    Attributes:
        position: SVG coordinate along the tick's axis.
        label: Tick text.
    """

    model_config = ConfigDict(frozen=True)

    position: float
    label: str


class TrendChartRead(BaseModel):
    """Inline-SVG geometry and summary for one trend chart.

    Attributes:
        chart_id: Unique DOM id prefix for the chart.
        width: SVG viewBox width.
        height: SVG viewBox height.
        plot_left: Left edge of the plot area.
        plot_right: Right edge of the plot area.
        plot_top: Top edge of the plot area.
        plot_bottom: Bottom edge (score 0 baseline) of the plot area.
        path: SVG path ``d`` for the line, empty for a single point.
        points: Plotted sessions, oldest first.
        y_ticks: Gridlines at each score step.
        x_ticks: Date labels under the plot.
        latest_display: Latest average (``3.8``).
        delta_display: Change from first to latest (``+0.6``), or None.
        aria_label: Text summary for screen readers.
    """

    model_config = ConfigDict(frozen=True)

    chart_id: str
    width: int
    height: int
    plot_left: float
    plot_right: float
    plot_top: float
    plot_bottom: float
    path: str
    points: list[TrendPointRead]
    y_ticks: list[ChartTickRead]
    x_ticks: list[ChartTickRead]
    latest_display: str
    delta_display: str | None
    aria_label: str


class CategoryStatRead(BaseModel):
    """Per-category row under a topic chart.

    Attributes:
        label: Category display name.
        question_count: First answers scored in the category.
        average_display: Average first-answer score (``3.4``).
        latest_display: Average in the most recent session (``4.0``).
    """

    model_config = ConfigDict(frozen=True)

    label: str
    question_count: int
    average_display: str
    latest_display: str


class TopicProgressRead(BaseModel):
    """Progress of one track (all levels merged).

    Attributes:
        track: Track slug.
        label: Track display name.
        session_count: Sessions that included this track.
        chart: Trend chart for the track.
        categories: Category rows, weakest first.
    """

    model_config = ConfigDict(frozen=True)

    track: str
    label: str
    session_count: int
    chart: TrendChartRead
    categories: list[CategoryStatRead]


class ProgressPageRead(BaseModel):
    """Context for the ``/progress`` page.

    Attributes:
        overall: Trend across every question, or None without sessions.
        topics: One entry per practised track, most recent first.
    """

    model_config = ConfigDict(frozen=True)

    overall: TrendChartRead | None
    topics: list[TopicProgressRead]
