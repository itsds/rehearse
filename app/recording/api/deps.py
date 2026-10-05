# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""FastAPI dependencies for the recording feature."""

from typing import Annotated

from fastapi import Depends

from app.recording.repositories.metadata import RecordingMetadataRepository
from app.shared.infrastructure.gateways.recording_storage import RecordingStorage
from app.shared.paths import RECORDINGS_DIR


def get_recording_metadata() -> RecordingMetadataRepository:
    """Build the metadata repository over ``data/recordings/``.

    Tests override this dependency to point at a temporary directory.
    """
    return RecordingMetadataRepository(RecordingStorage(RECORDINGS_DIR))


RecordingMetadataDep = Annotated[
    RecordingMetadataRepository, Depends(get_recording_metadata)
]
