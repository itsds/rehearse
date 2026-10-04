# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the camera self-view panel on interview pages."""

from tests.helpers.coding_seed import seed_active_coding_interview
from tests.helpers.interview_seed import seed_two_question_interview


def test_theory_interview_page_has_self_view(client, isolated_db) -> None:
    """Active theory interviews render the self-view panel and its script."""
    interview_id = seed_two_question_interview("self-view-theory")
    response = client.get(f"/interview/{interview_id}")
    assert response.status_code == 200
    assert "data-self-view" in response.text
    assert "data-self-view-toggle" in response.text
    assert "/static/js/self_view.js" in response.text
    assert "Nothing is recorded unless you tick" in response.text


def test_theory_page_offers_opt_in_recording(client, isolated_db) -> None:
    """The theory page has the unticked recording option and its script."""
    interview_id = seed_two_question_interview("self-view-recording")
    response = client.get(f"/interview/{interview_id}")
    assert "data-recording-toggle" in response.text
    assert f'data-interview-id="{interview_id}"' in response.text
    assert "/static/js/recording.js" in response.text
    assert "data-recording-toggle checked" not in response.text


def test_self_view_is_off_until_switched_on(client, isolated_db) -> None:
    """The preview frame starts hidden; the camera starts only from JS."""
    interview_id = seed_two_question_interview("self-view-default-off")
    response = client.get(f"/interview/{interview_id}")
    assert 'aria-pressed="false"' in response.text
    assert "data-self-view-frame hidden" in response.text


def test_coding_interview_page_has_self_view(client, isolated_db) -> None:
    """Active coding tasks render the self-view panel under the brief."""
    interview_id, _task_id = seed_active_coding_interview("self-view-coding")
    response = client.get(f"/interview/{interview_id}")
    assert response.status_code == 200
    assert "coding-session__self-view" in response.text
    assert "/static/js/self_view.js" in response.text
    assert "data-recording-toggle" not in response.text
    assert "nothing is recorded" in response.text


def test_self_view_script_never_auto_starts_camera(client) -> None:
    """The camera is opened only from a click; the on/off state is not stored."""
    response = client.get("/static/js/self_view.js")
    assert response.status_code == 200
    assert "getUserMedia" in response.text
    assert "enabled" not in response.text
