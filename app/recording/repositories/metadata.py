# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Read and write recording sidecar metadata and the manifest file."""

from __future__ import annotations

import logging

from pydantic import ValidationError

from app.recording.domain.clips import (
    CALIBRATION_STEM,
    MANIFEST_FILE,
    META_SUFFIX,
)
from app.recording.domain.models import CalibrationMeta, ClipMeta, RecordingManifest
from app.shared.infrastructure.gateways.recording_storage import RecordingStorage

logger = logging.getLogger(__name__)


class RecordingMetadataRepository:
    """Typed access to ``*.meta.json`` sidecars and ``manifest.json``."""

    def __init__(self, storage: RecordingStorage) -> None:
        """Wrap the recording file storage."""
        self.storage = storage

    def save_clip_meta(self, interview_id: str, stem: str, meta: ClipMeta) -> None:
        """Write the sidecar for one answer clip."""
        self.storage.write_text(
            interview_id, stem + META_SUFFIX, meta.model_dump_json(indent=2)
        )

    def save_calibration_meta(self, interview_id: str, meta: CalibrationMeta) -> None:
        """Write the calibration sidecar."""
        self.storage.write_text(
            interview_id, CALIBRATION_STEM + META_SUFFIX, meta.model_dump_json(indent=2)
        )

    def clip_metas(self, interview_id: str) -> list[ClipMeta]:
        """Load every readable answer-clip sidecar whose video still exists."""
        names = set(self.storage.list_names(interview_id))
        metas: list[ClipMeta] = []
        for name in sorted(names):
            if not name.endswith(META_SUFFIX) or name.startswith(CALIBRATION_STEM):
                continue
            meta = self._load(interview_id, name, ClipMeta)
            if meta is not None and meta.file in names:
                metas.append(meta)
        return metas

    def calibration_meta(self, interview_id: str) -> CalibrationMeta | None:
        """Load the calibration sidecar if the clip exists."""
        meta = self._load(interview_id, CALIBRATION_STEM + META_SUFFIX, CalibrationMeta)
        if meta is None or self.storage.path_for(interview_id, meta.file) is None:
            return None
        return meta

    def save_manifest(self, interview_id: str, manifest: RecordingManifest) -> None:
        """Write ``manifest.json``."""
        self.storage.write_text(
            interview_id, MANIFEST_FILE, manifest.model_dump_json(indent=2)
        )

    def _load[M: (ClipMeta, CalibrationMeta)](
        self, interview_id: str, name: str, model: type[M]
    ) -> M | None:
        """Parse a sidecar, skipping (and logging) unreadable files.

        ``[M: (...)]`` is Python 3.12 generic syntax: ``M`` is one of the two
        models, and the return type follows whichever ``model`` is passed.
        """
        raw = self.storage.read_text(interview_id, name)
        if raw is None:
            return None
        try:
            return model.model_validate_json(raw)
        except ValidationError:
            logger.warning(
                "Ignoring unreadable recording metadata %s/%s", interview_id, name
            )
            return None
