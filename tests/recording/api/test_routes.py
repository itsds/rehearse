# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for recording upload, manifest, serving and delete endpoints."""

import json

from app.shared.infrastructure.models import Answer, Interview
from tests.helpers.interview_seed import persist_interview_with_answers
from tests.helpers.selection import minimal_selection_spec

WEBM = "video/webm;codecs=vp9,opus"


def _seed(interview_id: str = "rec-1") -> str:
    return persist_interview_with_answers(
        Interview(
            id=interview_id,
            locale="en",
            selection_spec=minimal_selection_spec(categories=["basics"]),
            status="active",
        ),
        [
            Answer(
                question_id="q1",
                order=1,
                round=0,
                question_text="What is Python?",
                answer_text="A language",
                score=5,
                feedback="SECRET-FEEDBACK",
            ),
            Answer(question_id="q2", order=2, round=0, question_text="Next?"),
        ],
    )


def _upload(
    client, interview_id, *, qid="q1", round_num=0, data=b"webm-bytes", ctype=WEBM
):
    return client.post(
        f"/interview/{interview_id}/recordings/clips",
        data={
            "question_id": qid,
            "round": str(round_num),
            "started_at": "2026-10-04T10:00:00Z",
            "duration_ms": "4200",
        },
        files={"file": ("clip.webm", data, ctype)},
    )


def test_upload_clip_stores_file_meta_and_manifest(
    client, isolated_db, isolated_recordings_dir
) -> None:
    interview_id = _seed()
    response = _upload(client, interview_id)
    assert response.status_code == 201
    assert response.json() == {"file": "q01-r0.webm", "size_bytes": 10}

    folder = isolated_recordings_dir / interview_id
    assert (folder / "q01-r0.webm").read_bytes() == b"webm-bytes"
    assert (folder / "q01-r0.meta.json").exists()
    manifest = json.loads((folder / "manifest.json").read_text())
    assert manifest["version"] == 1
    assert manifest["clips"][0]["question_text"] == "What is Python?"
    assert manifest["clips"][0]["answer_text"] == "A language"
    assert manifest["clips"][0]["duration_s"] == 4.2
    raw = (folder / "manifest.json").read_text()
    assert "SECRET-FEEDBACK" not in raw
    assert '"score"' not in raw


def test_upload_rejects_unknown_interview_and_round(client, isolated_db) -> None:
    assert _upload(client, "missing").status_code == 404
    interview_id = _seed()
    assert _upload(client, interview_id, qid="q9").status_code == 404
    assert _upload(client, interview_id, round_num=1).status_code == 404


def test_upload_rejects_non_video(client, isolated_db) -> None:
    interview_id = _seed()
    assert _upload(client, interview_id, ctype="audio/wav").status_code == 415


def test_upload_rejects_too_large(client, isolated_db, monkeypatch) -> None:
    monkeypatch.setattr("app.recording.domain.clips.MAX_CLIP_BYTES", 4)
    interview_id = _seed()
    assert _upload(client, interview_id).status_code == 413


def test_reupload_replaces_clip_across_formats(
    client, isolated_db, isolated_recordings_dir
) -> None:
    interview_id = _seed()
    _upload(client, interview_id)
    response = _upload(client, interview_id, data=b"mp4", ctype="video/mp4")
    assert response.json()["file"] == "q01-r0.mp4"
    names = sorted(p.name for p in (isolated_recordings_dir / interview_id).iterdir())
    assert "q01-r0.webm" not in names
    assert "q01-r0.mp4" in names


def test_serves_clip_with_range_support(client, isolated_db) -> None:
    interview_id = _seed()
    _upload(client, interview_id)
    response = client.get(f"/interview/{interview_id}/recordings/q01-r0.webm")
    assert response.status_code == 200
    assert response.headers["content-type"] == "video/webm"
    assert response.content == b"webm-bytes"
    partial = client.get(
        f"/interview/{interview_id}/recordings/q01-r0.webm",
        headers={"Range": "bytes=0-3"},
    )
    assert partial.status_code == 206
    assert partial.content == b"webm"


def test_serve_rejects_non_video_names(client, isolated_db) -> None:
    interview_id = _seed()
    _upload(client, interview_id)
    for name in ("q01-r0.meta.json", "q02-r0.webm", "calibration.webm"):
        assert (
            client.get(f"/interview/{interview_id}/recordings/{name}").status_code
            == 404
        )


def test_calibration_upload_and_validation(
    client, isolated_db, isolated_recordings_dir
) -> None:
    interview_id = _seed()
    segments = [
        {"target": "camera", "start_s": 0, "end_s": 5},
        {"target": "screen", "start_s": 5, "end_s": 10},
    ]
    url = f"/interview/{interview_id}/recordings/calibration"
    ok = client.post(
        url,
        data={"segments": json.dumps(segments)},
        files={"file": ("clip.webm", b"cal", WEBM)},
    )
    assert ok.status_code == 201
    manifest = client.get(f"/interview/{interview_id}/recordings/manifest.json").json()
    assert manifest["calibration"]["file"] == "calibration.webm"
    assert [s["target"] for s in manifest["calibration"]["segments"]] == [
        "camera",
        "screen",
    ]
    bad = client.post(
        url,
        data={
            "segments": json.dumps([{"target": "ceiling", "start_s": 0, "end_s": 1}])
        },
        files={"file": ("clip.webm", b"cal", WEBM)},
    )
    assert bad.status_code == 422


def test_manifest_404_without_recordings(client, isolated_db) -> None:
    interview_id = _seed()
    assert (
        client.get(f"/interview/{interview_id}/recordings/manifest.json").status_code
        == 404
    )
    assert client.get("/interview/missing/recordings/manifest.json").status_code == 404


def test_delete_recordings(client, isolated_db, isolated_recordings_dir) -> None:
    interview_id = _seed()
    _upload(client, interview_id)
    assert client.delete(f"/interview/{interview_id}/recordings").status_code == 204
    assert not (isolated_recordings_dir / interview_id).exists()
    assert client.delete(f"/interview/{interview_id}/recordings").status_code == 404
