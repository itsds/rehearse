# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Completed session results and section review pages."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)

from app.interview.api.deps import (
    CodingReviewServiceDep,
    CompletedSessionResultsDep,
    TheoryReviewServiceDep,
)
from app.recording.api.deps import RecordingMetadataDep
from app.recording.queries.review_clips import review_recordings
from app.templating import templates
from app.theory.support.transcript_export import (
    render_theory_transcript,
    transcript_filename,
)

router = APIRouter(prefix="/interview", tags=["interview-results"])


@router.get("/{interview_id}/results", response_class=HTMLResponse)
async def session_results_page(
    request: Request,
    interview_id: str,
    service: CompletedSessionResultsDep,
) -> Response:
    """Render the completed session results hub.

    Args:
        request: FastAPI request object.
        interview_id: Session UUID.
        service: Session results page service for the request scope.

    Returns:
        HTML response with session results, or redirect when unavailable.
    """
    page = service.prepare_page(interview_id)
    if page.redirect_url is not None:
        return RedirectResponse(url=page.redirect_url, status_code=303)
    return templates.TemplateResponse(
        request,
        "session_results.html",
        page.template_context or {},
    )


@router.get("/{interview_id}/theory", response_class=HTMLResponse)
async def theory_review_page(
    request: Request,
    interview_id: str,
    service: TheoryReviewServiceDep,
    recordings: RecordingMetadataDep,
) -> Response:
    """Render the completed theory section review with chat history.

    Args:
        request: FastAPI request object.
        interview_id: Session UUID.
        service: Theory review service for the request scope.
        recordings: Recording metadata, for replaying recorded answers.

    Returns:
        HTML response with theory review, or redirect when unavailable.
    """
    context = service.build_context_for(interview_id)
    if context is None:
        return RedirectResponse(
            url=f"/interview/{interview_id}/results", status_code=303
        )
    return templates.TemplateResponse(
        request,
        "theory_review.html",
        {
            **context.model_dump(),
            "recordings": review_recordings(recordings, interview_id),
        },
    )


@router.get("/{interview_id}/theory/export.md", response_class=PlainTextResponse)
async def theory_transcript_export(
    interview_id: str,
    service: TheoryReviewServiceDep,
) -> Response:
    """Download the theory Q&A as Markdown, without scores or feedback.

    Args:
        interview_id: Session UUID.
        service: Theory review service for the request scope.

    Returns:
        Markdown attachment, or redirect when the session is not completed.

    Raises:
        HTTPException: 404 when the session does not exist.
    """
    context = service.build_context_for(interview_id)
    if context is None:
        if not service.interview_exists(interview_id):
            raise HTTPException(status_code=404, detail="Interview not found")
        return RedirectResponse(
            url=f"/interview/{interview_id}/results", status_code=303
        )
    filename = transcript_filename(interview_id)
    return Response(
        content=render_theory_transcript(context),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{interview_id}/coding", response_class=HTMLResponse)
async def coding_review_page(
    request: Request,
    interview_id: str,
    service: CodingReviewServiceDep,
) -> Response:
    """Render the completed coding section review with per-task feedback.

    Args:
        request: FastAPI request object.
        interview_id: Session UUID.
        service: Coding review service for the request scope.

    Returns:
        HTML response with coding review, or redirect when unavailable.
    """
    context = service.build_context_for(interview_id)
    if context is None:
        return RedirectResponse(
            url=f"/interview/{interview_id}/results", status_code=303
        )
    return templates.TemplateResponse(
        request,
        "coding_review.html",
        context.model_dump(),
    )
