# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for completed session results HTTP routes."""

from tests.helpers.completed_session_seed import seed_completed_theory_interview
from tests.helpers.interview_seed import seed_two_question_interview


def test_completed_interview_page_redirects_to_results(client, isolated_db) -> None:
    """Completed sessions no longer render the active interview page."""
    interview_id = seed_completed_theory_interview("results-redirect-1")
    response = client.get(f"/interview/{interview_id}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/interview/{interview_id}/results"


def test_results_page_renders_for_completed_session(client, isolated_db) -> None:
    """Results hub renders overall feedback and section cards."""
    interview_id = seed_completed_theory_interview("results-page-1")
    response = client.get(f"/interview/{interview_id}/results")
    assert response.status_code == 200
    assert "Overall Evaluation" in response.text
    assert "View details" in response.text
    assert "Good theory performance." in response.text


def test_theory_transcript_export_downloads_markdown(client, isolated_db) -> None:
    """Completed sessions export the theory Q&A as a blind Markdown attachment."""
    interview_id = seed_completed_theory_interview("results-export-1")
    response = client.get(f"/interview/{interview_id}/theory/export.md")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="rehearsal-results--theory.md"'
    )
    assert "## Q1" in response.text
    assert "What is Python?" in response.text
    assert "A programming language" in response.text
    assert "Clear and concise." not in response.text
    assert "Good theory performance." not in response.text


def test_theory_transcript_export_unknown_interview_returns_404(
    client, isolated_db
) -> None:
    """Exporting a missing session returns 404."""
    response = client.get(
        "/interview/does-not-exist/theory/export.md", follow_redirects=False
    )
    assert response.status_code == 404


def test_theory_transcript_export_redirects_when_not_completed(
    client, isolated_db
) -> None:
    """Active sessions cannot be exported and redirect to the results hub."""
    interview_id = seed_two_question_interview("results-export-active")
    response = client.get(
        f"/interview/{interview_id}/theory/export.md", follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"/interview/{interview_id}/results"


def test_theory_review_page_has_export_button(client, isolated_db) -> None:
    """The theory review page links to the transcript export."""
    interview_id = seed_completed_theory_interview("results-export-btn")
    response = client.get(f"/interview/{interview_id}/theory")
    assert response.status_code == 200
    assert "Export transcript" in response.text
    assert f"/interview/{interview_id}/theory/export.md" in response.text
