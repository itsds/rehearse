# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Dashboard endpoint module.

This module provides the home page with interview history.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.interview.api.deps import InterviewDashboardDep, ProgressTrendsDep
from app.templating import templates

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    dashboard: InterviewDashboardDep,
    progress: ProgressTrendsDep,
) -> HTMLResponse:
    """Render the dashboard with recent interview history.

    Args:
        request: FastAPI request object.
        dashboard: Dashboard row builder for the request scope.
        progress: Progress trend query for the request scope.

    Returns:
        HTML response with the dashboard template.
    """
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "interview_history": dashboard.list_rows(limit=20),
            "progress_trend": progress.overall_chart(),
        },
    )
