# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Typed errors for the recording feature."""


class RecordingError(Exception):
    """Base class for recording domain errors."""


class RecordingInterviewNotFoundError(RecordingError):
    """The interview does not exist."""


class RecordingRoundNotFoundError(RecordingError):
    """The question round does not exist in the interview's theory section."""


class UnsupportedRecordingTypeError(RecordingError):
    """The upload is not a supported video type (WebM or MP4)."""


class RecordingTooLargeError(RecordingError):
    """The upload exceeds the per-clip size limit."""


class RecordingsNotFoundError(RecordingError):
    """The interview has no recordings."""
