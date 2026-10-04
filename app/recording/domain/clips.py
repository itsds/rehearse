# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure naming and format rules for recording files."""

from __future__ import annotations

import re
from typing import Final

# 300 MB per clip: ~40 min at the ~1 Mbit/s the browser records with.
MAX_CLIP_BYTES: Final = 300 * 1024 * 1024
CALIBRATION_STEM: Final = "calibration"
MANIFEST_FILE: Final = "manifest.json"
META_SUFFIX: Final = ".meta.json"

_EXTENSIONS: Final[dict[str, str]] = {"video/webm": "webm", "video/mp4": "mp4"}
_MEDIA_TYPES: Final[dict[str, str]] = {ext: mime for mime, ext in _EXTENSIONS.items()}
_VIDEO_FILE_RE: Final = re.compile(
    rf"^(?:q\d{{2,3}}-r\d|{CALIBRATION_STEM})\.(?:webm|mp4)$"
)


def clip_stem(order: int, round_num: int) -> str:
    """Return the file stem for a question round, e.g. ``q03-r1``.

    The question order (not the bank ID) is used so names stay short and
    filesystem-safe; the manifest maps each file back to its question ID.

    Args:
        order: Question display order within the section (1-based).
        round_num: Follow-up round (0 = main question).

    Returns:
        File stem without extension.
    """
    return f"q{order:02d}-r{round_num}"


def extension_for(content_type: str | None) -> str | None:
    """Map an upload content type (codecs parameters allowed) to an extension.

    Args:
        content_type: e.g. ``video/webm;codecs=vp9,opus``.

    Returns:
        ``webm`` or ``mp4``, or None when the type is not a supported video.
    """
    if not content_type:
        return None
    base = content_type.split(";", 1)[0].strip().lower()
    return _EXTENSIONS.get(base)


def media_type_for(filename: str) -> str:
    """Return the HTTP media type for a stored video file name."""
    return _MEDIA_TYPES[filename.rsplit(".", 1)[-1]]


def is_video_filename(filename: str) -> bool:
    """Return whether ``filename`` is a servable recording (no paths, no meta)."""
    return bool(_VIDEO_FILE_RE.fullmatch(filename))
