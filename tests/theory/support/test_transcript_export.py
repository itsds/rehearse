# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the blind theory transcript Markdown renderer."""

from datetime import datetime

from app.theory.schemas.review import TheoryReviewContext
from app.theory.schemas.theory import TheoryTaskRead
from app.theory.support.transcript_export import (
    NO_ANSWER_TEXT,
    render_theory_transcript,
    transcript_filename,
)

SECRET_FEEDBACK = "ZZ-feedback-should-never-leak"
SECTION_SECRET = "ZZ-section-narrative-should-never-leak"


def _task(
    order: int,
    round_num: int,
    question: str,
    answer: str | None,
    *,
    code: str | None = None,
) -> TheoryTaskRead:
    return TheoryTaskRead(
        id=order * 10 + round_num,
        question_id=f"q{order}",
        order=order,
        round=round_num,
        question_text=question,
        question_code=code,
        answer_text=answer,
        score=3,
        feedback=f"{SECRET_FEEDBACK} {order}:{round_num}",
        started_at=None,
    )


def _context(answers: list[TheoryTaskRead]) -> TheoryReviewContext:
    return TheoryReviewContext(
        interview_id="abcdef12-3456-7890",
        interview_title="Kafka · Senior",
        selection_lines=["Kafka / Senior: Consumers"],
        locale_label="English",
        section_score=37,
        section_max_score=91,
        section_feedback={
            "summary": SECTION_SECRET,
            "strengths": [SECTION_SECRET],
            "topics_to_review": [SECTION_SECRET],
        },
        answers=answers,
        results_url="/interview/abcdef12-3456-7890/results",
        completed_at=datetime(2026, 10, 4, 18, 42),
    )


def test_header_contains_title_date_selection_and_locale() -> None:
    text = render_theory_transcript(_context([_task(1, 0, "Q?", "A.")]))
    assert text.startswith("# Rehearsal transcript — Kafka · Senior\n")
    assert "- **Date:** 2026-10-04 18:42 UTC" in text
    assert "  - Kafka / Senior: Consumers" in text
    assert "- **Language:** English" in text


def test_questions_in_order_with_follow_ups_nested() -> None:
    text = render_theory_transcript(
        _context(
            [
                _task(1, 0, "First question?", "First answer."),
                _task(1, 1, "First follow-up?", "Follow-up answer one."),
                _task(1, 2, "Second follow-up?", "Follow-up answer two."),
                _task(2, 0, "Second question?", "Second answer."),
            ]
        )
    )
    markers = [
        "## Q1",
        "First question?",
        "First answer.",
        "### Follow-up 1",
        "First follow-up?",
        "Follow-up answer one.",
        "### Follow-up 2",
        "Second follow-up?",
        "Follow-up answer two.",
        "## Q2",
        "Second question?",
        "Second answer.",
    ]
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions)
    assert text.count("**My answer:**") == 4
    # Follow-ups are not separated from their parent question by a rule.
    q1_block = text[text.index("## Q1") : text.index("Follow-up answer two.")]
    assert "---" not in q1_block


def test_question_code_rendered_in_fenced_block() -> None:
    code = "def f():\n    return 1\n"
    text = render_theory_transcript(
        _context([_task(1, 0, "Explain:", "Ok", code=code)])
    )
    assert "```\ndef f():\n    return 1\n```" in text


def test_code_fence_longer_than_backticks_inside_code() -> None:
    code = "s = '```'"
    text = render_theory_transcript(_context([_task(1, 0, "Q?", "A", code=code)]))
    assert "````\ns = '```'\n````" in text


def test_empty_or_expired_answers_get_placeholder() -> None:
    text = render_theory_transcript(
        _context(
            [
                _task(1, 0, "Q1?", ""),
                _task(2, 0, "Q2?", "   "),
                _task(3, 0, "Q3?", "[Time expired]"),
                _task(4, 0, "Q4?", None),
            ]
        )
    )
    assert text.count(NO_ANSWER_TEXT) == 4
    assert "[Time expired]" not in text


def test_no_scores_or_feedback_in_output() -> None:
    text = render_theory_transcript(
        _context([_task(1, 0, "Q?", "A."), _task(1, 1, "Follow?", "B.")])
    )
    assert SECRET_FEEDBACK not in text
    assert SECTION_SECRET not in text
    assert "37" not in text
    assert "91" not in text
    lowered = text.lower()
    for word in ("score", "feedback", "strength", "expected"):
        assert word not in lowered


def test_transcript_filename_uses_short_id() -> None:
    assert (
        transcript_filename("abcdef12-3456-7890-abcd-ef1234567890")
        == "rehearsal-abcdef12-theory.md"
    )
