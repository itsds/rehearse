# Copyright 2026 GrillKit Contributors
# SPDX-License-Identifier: Apache-2.0
"""Test helpers for seeding completed sessions with scored theory rounds."""

from datetime import datetime

from app.interview.domain.serialization import session_to_spec
from app.interview.domain.value_objects import SessionSelection, TrackSelection
from app.interview.repositories.uow import InterviewUnitOfWork
from app.shared.infrastructure.models import Answer, Interview
from tests.helpers.interview_seed import persist_interview_with_answers

# (question_id, round, score, answer_text)
Round = tuple[str, int, int | None, str | None]


def seed_scored_session(
    interview_id: str,
    rounds: list[Round],
    *,
    completed_at: datetime,
    tracks: tuple[str, ...] = ("kafka",),
) -> str:
    """Persist a completed theory session with the given scored rounds.

    Args:
        interview_id: Interview primary key.
        rounds: Theory rounds as ``(question_id, round, score, answer_text)``.
        completed_at: Session end time (controls trend order).
        tracks: Theory tracks recorded in the selection spec.

    Returns:
        Interview UUID.
    """
    spec = session_to_spec(
        SessionSelection.theory_only(
            sources=tuple(
                TrackSelection(track=track, level="senior", categories=("basics",))
                for track in tracks
            ),
            question_count=len({qid for qid, *_ in rounds}),
        )
    )
    orders: dict[str, int] = {}
    answers = [
        Answer(
            question_id=qid,
            order=orders.setdefault(qid, len(orders) + 1),
            round=round_num,
            question_text=f"Question {qid} round {round_num}?",
            answer_text=answer_text,
            score=score,
            feedback="SECRET-FEEDBACK",
        )
        for qid, round_num, score, answer_text in rounds
    ]
    persist_interview_with_answers(
        Interview(id=interview_id, locale="en", selection_spec=spec, status="active"),
        answers,
    )
    with InterviewUnitOfWork(auto_commit=True) as uow:
        aggregate = uow.interviews.get_aggregate(interview_id)
        assert aggregate is not None
        uow.interviews.save_aggregate(
            aggregate.with_session_completed(
                {"overall_feedback": "ok"}, completed_at=completed_at
            )
        )
    return interview_id
