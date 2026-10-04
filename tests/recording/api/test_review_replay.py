# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for replaying recorded answers on the theory review page."""

from tests.helpers.completed_session_seed import seed_completed_theory_interview


def _upload(client, interview_id: str) -> None:
    response = client.post(
        f"/interview/{interview_id}/recordings/clips",
        data={"question_id": "q1", "round": "0"},
        files={"file": ("clip.webm", b"video", "video/webm")},
    )
    assert response.status_code == 201


def test_review_page_shows_player_and_delete_button(client, isolated_db) -> None:
    interview_id = seed_completed_theory_interview("replay-1")
    _upload(client, interview_id)
    page = client.get(f"/interview/{interview_id}/theory")
    assert page.status_code == 200
    assert f'src="/interview/{interview_id}/recordings/q01-r0.webm"' in page.text
    assert "answer-recording" in page.text
    assert "Delete recordings" in page.text


def test_review_page_without_recordings_has_no_player(client, isolated_db) -> None:
    interview_id = seed_completed_theory_interview("replay-2")
    page = client.get(f"/interview/{interview_id}/theory")
    assert page.status_code == 200
    assert "<video" not in page.text
    assert "Delete recordings" not in page.text
