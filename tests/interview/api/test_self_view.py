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
    assert "nothing is recorded" in response.text


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


def test_self_view_script_is_served(client) -> None:
    """The self-view script is available as a static asset."""
    response = client.get("/static/js/self_view.js")
    assert response.status_code == 200
    assert "getUserMedia" in response.text
    assert "audio: false" in response.text
