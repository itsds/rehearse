# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Progress page: first-answer score trends overall and per topic."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.interview.api.deps import ProgressTrendsDep
from app.templating import templates

router = APIRouter(tags=["progress"])


@router.get("/progress", response_class=HTMLResponse)
async def progress_page(
    request: Request,
    progress: ProgressTrendsDep,
) -> HTMLResponse:
    """Render overall and per-topic progress trends.

    Args:
        request: FastAPI request object.
        progress: Progress trend query for the request scope.

    Returns:
        HTML response with the progress template.
    """
    return templates.TemplateResponse(
        request,
        "progress.html",
        {"progress": progress.build_page()},
    )
