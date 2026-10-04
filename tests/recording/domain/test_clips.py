# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for recording file naming and format rules."""

import pytest

from app.recording.domain.clips import (
    clip_stem,
    extension_for,
    is_video_filename,
    media_type_for,
)


def test_clip_stem_uses_order_and_round() -> None:
    assert clip_stem(3, 0) == "q03-r0"
    assert clip_stem(12, 2) == "q12-r2"


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("video/webm", "webm"),
        ("video/webm;codecs=vp9,opus", "webm"),
        ("VIDEO/MP4; codecs=avc1", "mp4"),
        ("audio/wav", None),
        ("", None),
        (None, None),
    ],
)
def test_extension_for(content_type, expected) -> None:
    assert extension_for(content_type) == expected


def test_media_type_for() -> None:
    assert media_type_for("q01-r0.webm") == "video/webm"
    assert media_type_for("calibration.mp4") == "video/mp4"


@pytest.mark.parametrize(
    ("name", "ok"),
    [
        ("q01-r0.webm", True),
        ("q123-r2.mp4", True),
        ("calibration.webm", True),
        ("manifest.json", False),
        ("q01-r0.meta.json", False),
        ("../q01-r0.webm", False),
        ("q01-r0.webm/../x", False),
        ("q1-r0.webm", False),
        ("q01-r0.mov", False),
    ],
)
def test_is_video_filename(name, ok) -> None:
    assert is_video_filename(name) is ok
