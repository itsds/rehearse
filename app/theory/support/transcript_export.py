# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Render a blind theory transcript (questions and answers only) as Markdown."""

from __future__ import annotations

import re
from typing import Final

from app.theory.domain.entities import TheoryTask
from app.theory.schemas.review import TheoryReviewContext
from app.theory.schemas.theory import TheoryTaskRead

NO_ANSWER_TEXT: Final = "_(no answer — skipped or time expired)_"
_SHORT_ID_LENGTH: Final = 8


def transcript_filename(interview_id: str) -> str:
    """Return the download filename for a theory transcript.

    Args:
        interview_id: Session UUID.

    Returns:
        File name such as ``rehearsal-1a2b3c4d-theory.md``.
    """
    return f"rehearsal-{interview_id[:_SHORT_ID_LENGTH]}-theory.md"


def render_theory_transcript(context: TheoryReviewContext) -> str:
    """Build a Markdown transcript of the theory section for blind grading.

    Only questions, follow-ups and the candidate's answers are included.
    Scores, feedback, rubric points and section narratives are deliberately
    never read, so an external grader cannot be anchored by them.

    Args:
        context: Theory review context of a completed session.

    Returns:
        Markdown document text ending with a newline.
    """
    lines: list[str] = [f"# Rehearsal transcript — {context.interview_title}", ""]
    if context.completed_at is not None:
        date = context.completed_at.strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"- **Date:** {date}")
    if context.selection_lines:
        lines.append("- **Selection:**")
        lines.extend(f"  - {line}" for line in context.selection_lines)
    lines.append(f"- **Language:** {context.locale_label}")

    for task in context.answers:
        lines.extend(["", "---" if task.round == 0 else "", ""])
        lines.extend(_task_lines(task))

    # Collapse the blank-line runs produced by the separator logic above.
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return text.rstrip() + "\n"


def _task_lines(task: TheoryTaskRead) -> list[str]:
    """Render one question or follow-up round with its answer."""
    heading = f"## Q{task.order}" if task.round == 0 else f"### Follow-up {task.round}"
    lines = [heading, "", task.question_text.strip()]
    if task.question_code and task.question_code.strip():
        fence = _code_fence(task.question_code)
        lines.extend(["", fence, task.question_code.rstrip("\n"), fence])
    lines.extend(["", "**My answer:**", "", _answer_text(task.answer_text)])
    return lines


def _answer_text(answer_text: str | None) -> str:
    """Return the answer body, or a placeholder when nothing was answered."""
    text = (answer_text or "").strip()
    if not text or text == TheoryTask.TIME_EXPIRED_ANSWER_TEXT:
        return NO_ANSWER_TEXT
    return text


def _code_fence(code: str) -> str:
    """Return a backtick fence longer than any backtick run inside ``code``."""
    longest = max((len(run) for run in re.findall(r"`+", code)), default=0)
    return "`" * max(3, longest + 1)
