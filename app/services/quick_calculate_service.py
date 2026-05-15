"""Business logic for Quick Calculate game (G02_F04, SF01–SF07)."""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_session import GameMode, GameSession
from app.models.question import Question
from app.models.session_operation import SessionOperation
from app.models.user import UserProfile
from app.utils.difficulty_ramp import get_difficulty_params_for_count
from app.utils.question_generator import GenerationError, generate_math_question

logger = logging.getLogger(__name__)

_ANSWER_TOLERANCE_SECONDS: float = 2.0
_MAX_ERRORS_ALLOWED: int = 1  # Quick Calculate: end on first wrong answer or timeout


# ── SF01 ─────────────────────────────────────────────────────────────────────

async def start_session(user_id: int, db: AsyncSession) -> dict:
    """
    SF01: Start or resume a Quick Calculate game session.

    If the user already has an active session (e.g. exited mid-game), that session
    is returned with its current ramp config instead of creating a new one.
    The `resumed` flag in the response tells the caller which case occurred.

    Precondition: user_id is authenticated (provided by FastAPI dependency).

    Args:
        user_id: Authenticated user's ID.
        db: Async database session.

    Returns:
        Dict with session_id, resumed, initial_ramp_config, started_at.
        When resumed=True, ramp_level and time_limit reflect the session's
        current correct_count rather than starting values.
    """
    existing_result = await db.execute(
        select(GameSession).where(
            GameSession.user_id == user_id,
            GameSession.status == "active",
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        correct_count = await _get_correct_count(existing.id, db)
        resumed_params = get_difficulty_params_for_count(correct_count)
        logger.info("Session %s resumed for user %d", existing.id, user_id)
        return {
            "session_id": str(existing.id),
            "resumed": True,
            "initial_ramp_config": {
                "ramp_level": resumed_params["level"],
                "time_limit_per_question": resumed_params["time_limit"],
                "max_questions": None,
                "max_errors_allowed": _MAX_ERRORS_ALLOWED,
            },
            "started_at": existing.created_at.isoformat() + "Z",
        }

    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    level_at_start = profile.current_level if profile else 1

    session = GameSession(
        user_id=user_id,
        game_mode=GameMode.QUICK_CALCULATE,
        level_player_at_start=level_at_start,
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info("Session %s started for user %d", session.id, user_id)

    initial_params = get_difficulty_params_for_count(0)
    return {
        "session_id": str(session.id),
        "resumed": False,
        "initial_ramp_config": {
            "ramp_level": initial_params["level"],
            "time_limit_per_question": initial_params["time_limit"],
            "max_questions": None,
            "max_errors_allowed": _MAX_ERRORS_ALLOWED,
        },
        "started_at": session.created_at.isoformat() + "Z",
    }


# ── SF02 ─────────────────────────────────────────────────────────────────────

async def generate_next_operation(session_id: str, user_id: int, db: AsyncSession) -> dict:
    """
    SF02: Generate the next math operation for the session.

    Supports two question sources:
    - "bank": fetches a pre-seeded Question from the questions table (current default)
    - "generated": creates a question algorithmically and stores content+answer inline

    Difficulty is derived from the session's current correct answer count (SF06 ramp).

    Args:
        session_id: UUID string of the session.
        user_id: Authenticated user's ID.
        db: Async database session.

    Returns:
        Dict with operation_id, question_id (null if generated), question_source,
        question_index, content, time_limit, generated_at.
        correct_answer is never sent to the client.
    """
    session = await _get_active_session(session_id, user_id, db)

    correct_count = await _get_correct_count(session.id, db)
    total_count = await _get_total_count(session.id, db)
    ramp = get_difficulty_params_for_count(correct_count)

    question_source = "generated"

    if question_source == "bank":
        last_question_id = await _get_last_question_id(session.id, db)
        question = await _fetch_question_for_level(ramp["level"], last_question_id, db)
        operation = SessionOperation(
            session_id=session.id,
            user_id=user_id,
            question_source="bank",
            question_id=question.id,
            question_index=total_count,
            time_limit=ramp["time_limit"],
        )
        content = question.content
        question_id_str = str(question.id)
    else:

        try:
            gen = generate_math_question(ramp["level"])
        except GenerationError as exc:
            logger.error("Question generation invariant violated at level %d: %s", ramp["level"], exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "NO_QUESTION_AVAILABLE", "message": "Question generation failed"},
            )
        operation = SessionOperation(
            session_id=session.id,
            user_id=user_id,
            question_source="generated",
            question_id=None,
            question_content=gen["content"],
            question_correct_answer=gen["correct_answer"],
            question_index=total_count,
            time_limit=ramp["time_limit"],
        )
        content = gen["content"]
        question_id_str = None

    db.add(operation)
    await db.commit()
    await db.refresh(operation)

    return {
        "operation_id": str(operation.id),
        "question_id": question_id_str,
        "question_source": operation.question_source,
        "question_index": total_count,
        "content": content,
        "time_limit": operation.time_limit,
        "generated_at": operation.created_at.isoformat() + "Z",
    }


# ── SF03 ─────────────────────────────────────────────────────────────────────

async def record_timeout(
    session_id: str, operation_id: str, user_id: int, db: AsyncSession
) -> dict:
    """
    SF03: Record a timeout for the current operation.

    Marks the operation as timed_out and auto-ends the session (max_errors_allowed=1).

    Args:
        session_id: UUID string of the session.
        operation_id: UUID string of the operation.
        user_id: Authenticated user's ID.
        db: Async database session.

    Returns:
        Dict with operation_id, timed_out, correct_answer, session_stats, session_ended.

    Raises:
        HTTPException 400: If the operation was already answered or timed out.
    """
    session = await _get_active_session(session_id, user_id, db)
    operation = await _get_operation(operation_id, session.id, db)

    if operation.timed_out or operation.user_answer is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OPERATION_ALREADY_ANSWERED", "message": "Operation already answered or timed out"},
        )

    now = datetime.utcnow()
    operation.timed_out = True
    operation.is_correct = False
    operation.evaluated_at = now

    await db.commit()

    correct_answer = await _resolve_correct_answer(operation, db)
    wrong_count = await _get_wrong_count(session.id, db)
    correct_count = await _get_correct_count(session.id, db)
    current_streak = await _get_current_streak(session.id, db)

    end_reason = _check_end_conditions(wrong_count)
    if end_reason:
        await _finalize_session(session, end_reason, db)

    return {
        "operation_id": str(operation.id),
        "timed_out": True,
        "correct_answer": correct_answer,
        "session_stats": {
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "questions_answered": correct_count + wrong_count,
            "current_streak": current_streak,
        },
        "session_ended": end_reason is not None,
        "end_reason": end_reason,
    }


# ── SF04 + SF05 ───────────────────────────────────────────────────────────────

async def submit_answer(
    session_id: str,
    operation_id: str,
    answer: str,
    user_id: int,
    client_submitted_at: Optional[datetime],
    db: AsyncSession,
) -> dict:
    """
    SF04 + SF05: Submit an answer and evaluate its correctness in one request.

    SF04: validates format, checks time window, records user_answer.
    SF05: compares against correct_answer from the questions table, updates stats.
    SF06: ramp level is derived from the session's correct_count.

    Args:
        session_id: UUID string of the session.
        operation_id: UUID string of the operation.
        answer: Player's answer as a string (must parse to integer).
        user_id: Authenticated user's ID.
        client_submitted_at: Client-reported timestamp stored for analytics (optional).
        db: Async database session.

    Returns:
        Dict with evaluation result, updated session stats, and optional session_ended flag.

    Raises:
        HTTPException 400: Invalid format, already answered, or answer too late.
    """
    try:
        answer_int = int(answer.strip())
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_ANSWER_FORMAT", "message": "Answer must be a valid integer"},
        )

    session = await _get_active_session(session_id, user_id, db)
    operation = await _get_operation(operation_id, session.id, db)

    if operation.user_answer is not None or operation.timed_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OPERATION_ALREADY_ANSWERED", "message": "Operation already answered"},
        )

    now = datetime.utcnow()
    deadline = operation.created_at + timedelta(
        seconds=operation.time_limit + _ANSWER_TOLERANCE_SECONDS
    )
    if now > deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ANSWER_TOO_LATE", "message": "Answer submitted after the allowed time window"},
        )

    correct_answer = await _resolve_correct_answer(operation, db)

    # SF04: record submission
    operation.user_answer = answer_int
    operation.submitted_at = now
    if client_submitted_at:
        operation.client_submitted_at = client_submitted_at.replace(tzinfo=None)

    # SF05: evaluate correctness
    is_correct = (answer_int == correct_answer)
    operation.is_correct = is_correct
    operation.evaluated_at = now

    await db.commit()

    correct_count = await _get_correct_count(session.id, db)
    wrong_count = await _get_wrong_count(session.id, db)
    current_streak = await _get_current_streak(session.id, db)

    if is_correct:
        level = get_difficulty_params_for_count(correct_count)["level"]
        logger.info(
            "Session %s: correct answer — correct_count=%d level=%d",
            session.id, correct_count, level,
        )

    end_reason = _check_end_conditions(wrong_count)
    if end_reason:
        await _finalize_session(session, end_reason, db)

    return {
        "operation_id": str(operation.id),
        "received": True,
        "server_received_at": now.isoformat() + "Z",
        "is_correct": is_correct,
        "correct_answer": correct_answer,
        "user_answer": answer_int,
        "consecutive_correct": current_streak,
        "session_stats": {
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "questions_answered": correct_count + wrong_count,
            "current_streak": current_streak,
        },
        "session_ended": end_reason is not None,
        "end_reason": end_reason,
    }


# ── SF07 ─────────────────────────────────────────────────────────────────────

async def end_session(session_id: str, user_id: int, end_reason: str, db: AsyncSession) -> dict:
    """
    SF07: End the game session and compute the final score.

    Idempotency: already-completed sessions return HTTP 400.

    Args:
        session_id: UUID string of the session.
        user_id: Authenticated user's ID.
        end_reason: One of 'max_errors', 'manual'.
        db: Async database session.

    Returns:
        Dict with session_id, end_reason, final_score, stats, ended_at.

    Raises:
        HTTPException 404: Session not found.
        HTTPException 400: Session already completed.
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    result = await db.execute(
        select(GameSession).where(
            GameSession.id == sid,
            GameSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SESSION_ALREADY_ENDED", "message": "Session already completed"},
        )

    return await _finalize_session(session, end_reason, db)


# ── Private helpers ───────────────────────────────────────────────────────────

def _check_end_conditions(wrong_count: int) -> Optional[str]:
    """Return end_reason if the session should auto-terminate, else None."""
    if wrong_count >= _MAX_ERRORS_ALLOWED:
        return "max_errors"
    return None


async def _finalize_session(session: GameSession, end_reason: str, db: AsyncSession) -> dict:
    """Mark session as completed, compute final score and stats from session_operations."""
    now = datetime.utcnow()

    correct_count = await _get_correct_count(session.id, db)
    wrong_count = await _get_wrong_count(session.id, db)
    max_streak = await _get_max_streak(session.id, db)
    total = correct_count + wrong_count
    accuracy = round(correct_count / total * 100, 1) if total > 0 else 0.0
    duration = round((now - session.created_at).total_seconds(), 1)
    max_ramp_level = get_difficulty_params_for_count(correct_count)["level"]

    session.status = "completed"
    session.score = correct_count
    session.ended_at = now

    await db.commit()
    await db.refresh(session)

    logger.info("Session %s ended — reason=%s score=%d", session.id, end_reason, session.score)

    return {
        "session_id": str(session.id),
        "end_reason": end_reason,
        "final_score": session.score,
        "stats": {
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "questions_answered": total,
            "accuracy_percent": accuracy,
            "max_streak": max_streak,
            "max_ramp_level": max_ramp_level,
            "duration_seconds": duration,
        },
        "ended_at": now.isoformat() + "Z",
    }


async def _get_active_session(session_id: str, user_id: int, db: AsyncSession) -> GameSession:
    """Load and validate a session: must exist, belong to user, and be active."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    result = await db.execute(
        select(GameSession).where(
            GameSession.id == sid,
            GameSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SESSION_NOT_ACTIVE", "message": "Session is not active"},
        )

    return session


async def _get_operation(
    operation_id: str, session_id: uuid.UUID, db: AsyncSession
) -> SessionOperation:
    """Load an operation and verify it belongs to the given session."""
    try:
        oid = uuid.UUID(operation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "OPERATION_NOT_FOUND", "message": "Operation not found"},
        )

    result = await db.execute(
        select(SessionOperation).where(
            SessionOperation.id == oid,
            SessionOperation.session_id == session_id,
        )
    )
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "OPERATION_NOT_FOUND", "message": "Operation not found"},
        )

    return operation


async def _get_question(question_id: uuid.UUID, db: AsyncSession) -> Question:
    """Load a question by ID from the questions table."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "QUESTION_NOT_FOUND", "message": "Question record missing"},
        )
    return question


async def _resolve_correct_answer(operation: SessionOperation, db: AsyncSession) -> int:
    """Return the correct answer for an operation regardless of its question source.

    - source="bank":      fetches correct_answer from the linked questions row
    - source="generated": reads question_correct_answer stored inline on the operation
    """
    if operation.question_source == "bank":
        question = await _get_question(operation.question_id, db)
        return question.correct_answer
    return operation.question_correct_answer


async def _get_correct_count(session_id: uuid.UUID, db: AsyncSession) -> int:
    """Count correct answers in the session."""
    result = await db.execute(
        select(func.count()).where(
            SessionOperation.session_id == session_id,
            SessionOperation.is_correct == True,  # noqa: E712
        )
    )
    return result.scalar_one()


async def _get_wrong_count(session_id: uuid.UUID, db: AsyncSession) -> int:
    """Count wrong/timed-out answers in the session."""
    result = await db.execute(
        select(func.count()).where(
            SessionOperation.session_id == session_id,
            SessionOperation.is_correct == False,  # noqa: E712
        )
    )
    return result.scalar_one()


async def _get_total_count(session_id: uuid.UUID, db: AsyncSession) -> int:
    """Count all operations (answered or not) in the session."""
    result = await db.execute(
        select(func.count()).where(SessionOperation.session_id == session_id)
    )
    return result.scalar_one()


async def _get_current_streak(session_id: uuid.UUID, db: AsyncSession) -> int:
    """Count consecutive correct answers from the most recent evaluated operation."""
    result = await db.execute(
        select(SessionOperation)
        .where(
            SessionOperation.session_id == session_id,
            SessionOperation.is_correct.isnot(None),
        )
        .order_by(SessionOperation.question_index.desc())
    )
    ops = result.scalars().all()
    streak = 0
    for op in ops:
        if op.is_correct is True:
            streak += 1
        else:
            break
    return streak


async def _get_max_streak(session_id: uuid.UUID, db: AsyncSession) -> int:
    """Find the longest consecutive correct answer run in the session."""
    result = await db.execute(
        select(SessionOperation)
        .where(
            SessionOperation.session_id == session_id,
            SessionOperation.is_correct.isnot(None),
        )
        .order_by(SessionOperation.question_index.asc())
    )
    ops = result.scalars().all()
    max_s, current = 0, 0
    for op in ops:
        if op.is_correct is True:
            current += 1
            max_s = max(max_s, current)
        else:
            current = 0
    return max_s


async def _get_last_question_id(
    session_id: uuid.UUID, db: AsyncSession
) -> Optional[uuid.UUID]:
    """Return the question_id of the most recent operation (anti-repeat guard)."""
    result = await db.execute(
        select(SessionOperation.question_id)
        .where(SessionOperation.session_id == session_id)
        .order_by(SessionOperation.question_index.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _fetch_question_for_level(
    level: int,
    exclude_id: Optional[uuid.UUID],
    db: AsyncSession,
) -> Question:
    """Fetch a random question at the given difficulty level, excluding the last seen.

    Falls back to the highest available level when the requested level has no questions,
    then retries without the exclude guard if only one question exists at that level.
    """
    async def _query(target_level: int, excluded: Optional[uuid.UUID]) -> Optional[Question]:
        stmt = select(Question).where(
            Question.type == "math",
            Question.difficulty_level == target_level,
        )
        if excluded is not None:
            stmt = stmt.where(Question.id != excluded)
        result = await db.execute(stmt.order_by(func.random()).limit(1))
        return result.scalar_one_or_none()

    question = await _query(level, exclude_id)
    if question:
        return question

    # Requested level not available — find the highest level that exists
    fallback_result = await db.execute(
        select(Question.difficulty_level)
        .where(Question.type == "math", Question.difficulty_level <= level)
        .order_by(Question.difficulty_level.desc())
        .limit(1)
    )
    fallback_level = fallback_result.scalar_one_or_none()

    if fallback_level is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "NO_QUESTION_AVAILABLE", "message": "No questions in the database"},
        )

    if fallback_level != level:
        logger.warning("No questions at level %d — falling back to level %d", level, fallback_level)

    question = await _query(fallback_level, exclude_id)
    if question:
        return question

    # Only one question at this level and it's excluded — drop the exclude guard
    question = await _query(fallback_level, excluded=None)
    if question:
        return question

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "NO_QUESTION_AVAILABLE", "message": "No questions available"},
    )
