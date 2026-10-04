# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""HTTP endpoints for uploading, serving and deleting interview recordings.

Handlers are plain ``def`` (not ``async def``): FastAPI runs them in a worker
thread, so streaming a large video to disk never blocks the event loop.
"""

from __future__ import annotations

from datetime import datetime
import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import TypeAdapter, ValidationError

from app.recording.api.deps import RecordingMetadataDep
from app.recording.domain import clips as clip_rules
from app.recording.domain.exceptions import (
    RecordingError,
    RecordingInterviewNotFoundError,
    RecordingRoundNotFoundError,
    RecordingTooLargeError,
    UnsupportedRecordingTypeError,
)
from app.recording.domain.models import CalibrationSegment
from app.recording.use_cases.rebuild_manifest import RebuildRecordingManifest
from app.recording.use_cases.save_recording import SaveRecording
from app.shared.application.uow_deps import UoWDep

router = APIRouter(prefix="/interview", tags=["recording"])

_SEGMENTS = TypeAdapter(list[CalibrationSegment])


def _http_error(exc: RecordingError) -> HTTPException:
    """Map a recording domain error to an HTTP error."""
    if isinstance(exc, RecordingInterviewNotFoundError | RecordingRoundNotFoundError):
        return HTTPException(status_code=404, detail=str(exc) or "Not found")
    if isinstance(exc, UnsupportedRecordingTypeError):
        return HTTPException(
            status_code=415, detail="Only WebM or MP4 video is accepted"
        )
    if isinstance(exc, RecordingTooLargeError):
        return HTTPException(status_code=413, detail="Recording is too large")
    return HTTPException(status_code=400, detail=str(exc))


def _seconds(duration_ms: int | None) -> float | None:
    return round(duration_ms / 1000, 3) if duration_ms is not None else None


@router.post("/{interview_id}/recordings/clips", status_code=201)
def upload_clip(
    interview_id: str,
    uow: UoWDep,
    metadata: RecordingMetadataDep,
    question_id: Annotated[str, Form()],
    round: Annotated[int, Form(ge=0)],  # noqa: A002 - matches the wire field name
    file: Annotated[UploadFile, File()],
    started_at: Annotated[datetime | None, Form()] = None,
    duration_ms: Annotated[int | None, Form(ge=0)] = None,
) -> dict[str, object]:
    """Store the video clip for one question round.

    Returns:
        The stored file name and size.
    """
    try:
        meta = SaveRecording(uow, metadata).save_clip(
            interview_id=interview_id,
            question_id=question_id,
            round_num=round,
            content_type=file.content_type,
            source=file.file,
            started_at=started_at,
            duration_s=_seconds(duration_ms),
        )
    except RecordingError as exc:
        raise _http_error(exc) from exc
    return {"file": meta.file, "size_bytes": meta.size_bytes}


@router.post("/{interview_id}/recordings/calibration", status_code=201)
def upload_calibration(
    interview_id: str,
    uow: UoWDep,
    metadata: RecordingMetadataDep,
    segments: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    recorded_at: Annotated[datetime | None, Form()] = None,
) -> dict[str, object]:
    """Store the gaze-calibration clip with its look-at segments (JSON list)."""
    try:
        parsed = _SEGMENTS.validate_python(json.loads(segments))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail="Invalid segments") from exc
    try:
        meta = SaveRecording(uow, metadata).save_calibration(
            interview_id=interview_id,
            content_type=file.content_type,
            source=file.file,
            recorded_at=recorded_at,
            segments=parsed,
        )
    except RecordingError as exc:
        raise _http_error(exc) from exc
    return {"file": meta.file, "size_bytes": meta.size_bytes}


@router.get("/{interview_id}/recordings/manifest.json")
def recording_manifest(
    interview_id: str,
    uow: UoWDep,
    metadata: RecordingMetadataDep,
) -> JSONResponse:
    """Rebuild and return ``manifest.json`` (also refreshes the file on disk)."""
    try:
        manifest = RebuildRecordingManifest(uow, metadata).execute(interview_id)
    except RecordingError as exc:
        raise _http_error(exc) from exc
    if manifest is None:
        raise HTTPException(status_code=404, detail="No recordings")
    return JSONResponse(manifest.model_dump(mode="json"))


@router.get("/{interview_id}/recordings/{filename}")
def recording_file(
    interview_id: str,
    filename: str,
    metadata: RecordingMetadataDep,
) -> FileResponse:
    """Serve a recorded video (supports HTTP range requests for seeking)."""
    if not clip_rules.is_video_filename(filename):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        path = metadata.storage.path_for(interview_id, filename)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc
    if path is None:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path, media_type=clip_rules.media_type_for(filename))


@router.delete("/{interview_id}/recordings", status_code=204)
def delete_recordings(
    interview_id: str,
    metadata: RecordingMetadataDep,
) -> Response:
    """Delete every recording of a session (clips, calibration, manifest)."""
    try:
        deleted = metadata.storage.delete_all(interview_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="No recordings")
    return Response(status_code=204)
