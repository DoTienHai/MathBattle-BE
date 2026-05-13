"""Tests for Quick Calculate game (G02_F04, SF01–SF07)."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.question import Question
from app.models.session_operation import SessionOperation
from app.utils.security import TokenGenerator

BASE = "/api/v1/games/quick-calculate"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def auth_headers(verified_user) -> dict:
    """Authorization headers for the verified user."""
    token = TokenGenerator.create_access_token(
        user_id=verified_user.id, email=verified_user.email
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def seeded_questions(test_db):
    """Seed the question bank with math questions at difficulty levels 1–5."""
    questions_data = [
        # level 1 — three questions so anti-repeat logic has room to pick
        {"content": "3 + 4 = ?", "correct_answer": 7, "difficulty_level": 1},
        {"content": "8 - 2 = ?", "correct_answer": 6, "difficulty_level": 1},
        {"content": "5 + 9 = ?", "correct_answer": 14, "difficulty_level": 1},
        # level 2
        {"content": "12 + 7 = ?", "correct_answer": 19, "difficulty_level": 2},
        {"content": "20 - 8 = ?", "correct_answer": 12, "difficulty_level": 2},
        # level 3
        {"content": "4 × 5 = ?", "correct_answer": 20, "difficulty_level": 3},
        {"content": "6 × 3 = ?", "correct_answer": 18, "difficulty_level": 3},
        # level 4
        {"content": "35 + 15 = ?", "correct_answer": 50, "difficulty_level": 4},
        # level 5
        {"content": "48 ÷ 6 = ?", "correct_answer": 8, "difficulty_level": 5},
    ]
    async with test_db() as db:
        for data in questions_data:
            q = Question(
                type="math",
                content=data["content"],
                correct_answer=data["correct_answer"],
                difficulty_level=data["difficulty_level"],
            )
            db.add(q)
        await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _start(client, headers) -> str:
    """Start a session and return its session_id."""
    r = await client.post(f"{BASE}/sessions", headers=headers)
    assert r.status_code == 201
    return r.json()["data"]["session_id"]


async def _next_op(client, headers, session_id: str) -> dict:
    """Request the next operation and return its data dict."""
    r = await client.post(f"{BASE}/sessions/{session_id}/next", headers=headers)
    assert r.status_code == 200
    return r.json()["data"]


async def _correct_answer_for(op_id: str, test_db) -> int:
    """Query the DB to get the correct answer for an operation via its linked Question."""
    async with test_db() as db:
        op_result = await db.execute(
            select(SessionOperation).where(SessionOperation.id == uuid.UUID(op_id))
        )
        op = op_result.scalar_one()
        q_result = await db.execute(
            select(Question).where(Question.id == op.question_id)
        )
        return q_result.scalar_one().correct_answer


# ── SF01: Start Session ───────────────────────────────────────────────────────

class TestStartSession:
    async def test_session_id_in_response(self, async_client, verified_user, auth_headers):
        r = await async_client.post(f"{BASE}/sessions", headers=auth_headers)
        assert r.status_code == 201
        assert "session_id" in r.json()["data"]

    async def test_initial_ramp_level_is_1(self, async_client, verified_user, auth_headers):
        r = await async_client.post(f"{BASE}/sessions", headers=auth_headers)
        cfg = r.json()["data"]["initial_ramp_config"]
        assert cfg["ramp_level"] == 1
        assert cfg["time_limit_per_question"] == 15.0
        assert cfg["max_questions"] is None
        assert cfg["max_errors_allowed"] == 1

    async def test_duplicate_session_returns_409(self, async_client, verified_user, auth_headers):
        await async_client.post(f"{BASE}/sessions", headers=auth_headers)
        r = await async_client.post(f"{BASE}/sessions", headers=auth_headers)
        assert r.status_code == 409
        assert r.json()["detail"]["code"] == "SESSION_ALREADY_ACTIVE"

    async def test_unauthenticated_returns_401(self, async_client):
        r = await async_client.post(f"{BASE}/sessions")
        assert r.status_code == 401


# ── SF02: Generate Next Operation ─────────────────────────────────────────────

class TestNextOperation:
    @pytest_asyncio.fixture(autouse=True)
    async def _seed(self, seeded_questions):
        pass

    async def test_returns_operation_fields(self, async_client, verified_user, auth_headers):
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        for field in ("operation_id", "question_id", "question_index", "content", "time_limit", "generated_at"):
            assert field in op
        assert isinstance(op["content"], str)

    async def test_correct_answer_not_in_response(self, async_client, verified_user, auth_headers):
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        assert "correct_answer" not in op

    async def test_question_index_starts_at_zero(self, async_client, verified_user, auth_headers):
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        assert op["question_index"] == 0

    async def test_time_limit_matches_ramp_level_1(self, async_client, verified_user, auth_headers):
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        assert op["time_limit"] == 15.0

    async def test_invalid_session_returns_404(self, async_client, verified_user, auth_headers):
        r = await async_client.post(
            f"{BASE}/sessions/00000000-0000-0000-0000-000000000000/next",
            headers=auth_headers,
        )
        assert r.status_code == 404


# ── SF03: Timeout ─────────────────────────────────────────────────────────────

class TestTimeout:
    @pytest_asyncio.fixture(autouse=True)
    async def _seed(self, seeded_questions):
        pass

    async def test_timeout_reveals_correct_answer(self, async_client, verified_user, auth_headers):
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        r = await async_client.post(
            f"{BASE}/sessions/{sid}/timeout",
            headers=auth_headers,
            json={"operation_id": op["operation_id"]},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["timed_out"] is True
        assert "correct_answer" in data

    async def test_timeout_increments_wrong_count(self, async_client, verified_user, auth_headers):
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        r = await async_client.post(
            f"{BASE}/sessions/{sid}/timeout",
            headers=auth_headers,
            json={"operation_id": op["operation_id"]},
        )
        stats = r.json()["data"]["session_stats"]
        assert stats["wrong_count"] == 1
        assert stats["current_streak"] == 0

    async def test_timeout_ends_session(self, async_client, verified_user, auth_headers):
        """Timeout counts as a wrong answer — session ends immediately (max_errors_allowed=1)."""
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        r = await async_client.post(
            f"{BASE}/sessions/{sid}/timeout",
            headers=auth_headers,
            json={"operation_id": op["operation_id"]},
        )
        data = r.json()["data"]
        assert data["session_ended"] is True
        assert data["end_reason"] == "max_errors"

    async def test_cannot_get_next_op_after_timeout(self, async_client, verified_user, auth_headers):
        """After a timeout the session is closed — SF02 must refuse further questions."""
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        await async_client.post(
            f"{BASE}/sessions/{sid}/timeout",
            headers=auth_headers,
            json={"operation_id": op["operation_id"]},
        )
        r = await async_client.post(f"{BASE}/sessions/{sid}/next", headers=auth_headers)
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "SESSION_NOT_ACTIVE"


# ── SF04 + SF05: Submit Answer ────────────────────────────────────────────────

class TestSubmitAnswer:
    @pytest_asyncio.fixture(autouse=True)
    async def _seed(self, seeded_questions):
        pass

    async def test_correct_answer_increments_correct_count(
        self, async_client, verified_user, auth_headers, test_db
    ):
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        correct = await _correct_answer_for(op["operation_id"], test_db)

        r = await async_client.post(
            f"{BASE}/sessions/{sid}/answer",
            headers=auth_headers,
            json={"operation_id": op["operation_id"], "answer": str(correct)},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["is_correct"] is True
        assert data["correct_answer"] == correct
        assert data["session_stats"]["correct_count"] == 1
        assert data["session_stats"]["current_streak"] == 1

    async def test_wrong_answer_ends_session(
        self, async_client, verified_user, auth_headers, test_db
    ):
        """Wrong answer increments wrong_count and auto-ends the session (max_errors=1)."""
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        correct = await _correct_answer_for(op["operation_id"], test_db)

        r = await async_client.post(
            f"{BASE}/sessions/{sid}/answer",
            headers=auth_headers,
            json={"operation_id": op["operation_id"], "answer": str(correct + 9999)},
        )
        data = r.json()["data"]
        assert data["is_correct"] is False
        assert data["session_stats"]["wrong_count"] == 1
        assert data["session_stats"]["current_streak"] == 0
        assert data["session_ended"] is True
        assert data["end_reason"] == "max_errors"

    async def test_streak_resets_on_wrong(
        self, async_client, verified_user, auth_headers, test_db
    ):
        sid = await _start(async_client, auth_headers)

        # Two correct answers to build streak
        for _ in range(2):
            op = await _next_op(async_client, auth_headers, sid)
            correct = await _correct_answer_for(op["operation_id"], test_db)
            await async_client.post(
                f"{BASE}/sessions/{sid}/answer",
                headers=auth_headers,
                json={"operation_id": op["operation_id"], "answer": str(correct)},
            )

        # Wrong answer — streak must reset to 0
        op = await _next_op(async_client, auth_headers, sid)
        correct = await _correct_answer_for(op["operation_id"], test_db)
        r = await async_client.post(
            f"{BASE}/sessions/{sid}/answer",
            headers=auth_headers,
            json={"operation_id": op["operation_id"], "answer": str(correct + 9999)},
        )
        assert r.json()["data"]["session_stats"]["current_streak"] == 0

    async def test_invalid_format_returns_400(self, async_client, verified_user, auth_headers):
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        r = await async_client.post(
            f"{BASE}/sessions/{sid}/answer",
            headers=auth_headers,
            json={"operation_id": op["operation_id"], "answer": "abc"},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "INVALID_ANSWER_FORMAT"

    async def test_duplicate_answer_returns_400(
        self, async_client, verified_user, auth_headers, test_db
    ):
        """Submitting a correct answer twice for the same operation returns OPERATION_ALREADY_ANSWERED."""
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        correct = await _correct_answer_for(op["operation_id"], test_db)
        payload = {"operation_id": op["operation_id"], "answer": str(correct)}
        await async_client.post(f"{BASE}/sessions/{sid}/answer", headers=auth_headers, json=payload)
        r = await async_client.post(f"{BASE}/sessions/{sid}/answer", headers=auth_headers, json=payload)
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "OPERATION_ALREADY_ANSWERED"

    async def test_negative_answer_accepted(
        self, async_client, verified_user, auth_headers, test_db
    ):
        """Negative integer answers must be accepted (subtraction can yield negative)."""
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        r = await async_client.post(
            f"{BASE}/sessions/{sid}/answer",
            headers=auth_headers,
            json={"operation_id": op["operation_id"], "answer": "-5"},
        )
        assert r.status_code == 200  # accepted (may be right or wrong, both are valid)

    async def test_cannot_answer_after_wrong(
        self, async_client, verified_user, auth_headers, test_db
    ):
        """After a wrong answer ends the session, further requests are rejected."""
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        correct = await _correct_answer_for(op["operation_id"], test_db)
        await async_client.post(
            f"{BASE}/sessions/{sid}/answer",
            headers=auth_headers,
            json={"operation_id": op["operation_id"], "answer": str(correct + 9999)},
        )
        r = await async_client.post(f"{BASE}/sessions/{sid}/next", headers=auth_headers)
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "SESSION_NOT_ACTIVE"


# ── SF07: End Session ─────────────────────────────────────────────────────────

class TestEndSession:
    @pytest_asyncio.fixture(autouse=True)
    async def _seed(self, seeded_questions):
        pass

    async def test_end_session_returns_stats(self, async_client, verified_user, auth_headers):
        sid = await _start(async_client, auth_headers)
        r = await async_client.post(
            f"{BASE}/sessions/{sid}/end",
            headers=auth_headers,
            json={"end_reason": "manual"},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["end_reason"] == "manual"
        assert "final_score" in data
        assert "stats" in data
        assert "accuracy_percent" in data["stats"]
        assert "duration_seconds" in data["stats"]

    async def test_score_equals_correct_count(
        self, async_client, verified_user, auth_headers, test_db
    ):
        sid = await _start(async_client, auth_headers)
        op = await _next_op(async_client, auth_headers, sid)
        correct = await _correct_answer_for(op["operation_id"], test_db)
        await async_client.post(
            f"{BASE}/sessions/{sid}/answer",
            headers=auth_headers,
            json={"operation_id": op["operation_id"], "answer": str(correct)},
        )
        r = await async_client.post(
            f"{BASE}/sessions/{sid}/end",
            headers=auth_headers,
            json={"end_reason": "manual"},
        )
        data = r.json()["data"]
        assert data["final_score"] == data["stats"]["correct_count"]

    async def test_double_end_returns_400(self, async_client, verified_user, auth_headers):
        sid = await _start(async_client, auth_headers)
        await async_client.post(
            f"{BASE}/sessions/{sid}/end", headers=auth_headers, json={"end_reason": "manual"}
        )
        r = await async_client.post(
            f"{BASE}/sessions/{sid}/end", headers=auth_headers, json={"end_reason": "manual"}
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "SESSION_ALREADY_ENDED"

    async def test_session_not_found_returns_404(self, async_client, verified_user, auth_headers):
        r = await async_client.post(
            f"{BASE}/sessions/00000000-0000-0000-0000-000000000000/end",
            headers=auth_headers,
            json={"end_reason": "manual"},
        )
        assert r.status_code == 404

    async def test_ended_session_cannot_generate_operation(
        self, async_client, verified_user, auth_headers
    ):
        """After session ends, SF02 must refuse to generate more questions."""
        sid = await _start(async_client, auth_headers)
        await async_client.post(
            f"{BASE}/sessions/{sid}/end", headers=auth_headers, json={"end_reason": "manual"}
        )
        r = await async_client.post(f"{BASE}/sessions/{sid}/next", headers=auth_headers)
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "SESSION_NOT_ACTIVE"


# ── SF06: Difficulty Ramp (unit tests) ───────────────────────────────────────

class TestDifficultyRamp:
    def test_level_1_player_starts_at_level_1(self):
        from app.utils.difficulty_ramp import get_difficulty_params_for_count

        params = get_difficulty_params_for_count(0, 1)
        assert params["level"] == 1
        assert params["time_limit"] == 15.0
        assert set(params.keys()) == {"level", "time_limit"}

    def test_correct_count_advances_level(self):
        from app.utils.difficulty_ramp import get_difficulty_params_for_count

        assert get_difficulty_params_for_count(5, 1)["level"] == 2
        assert get_difficulty_params_for_count(10, 1)["level"] == 3

    def test_player_level_sets_base_level(self):
        from app.utils.difficulty_ramp import get_difficulty_params_for_count

        # player_level=10 → base_level=max(10-5,1)=5
        assert get_difficulty_params_for_count(0, 10)["level"] == 5
        # player_level=3 → base_level=max(3-5,1)=1
        assert get_difficulty_params_for_count(0, 3)["level"] == 1

    def test_time_limit_decreases_with_correct_count(self):
        from app.utils.difficulty_ramp import get_difficulty_params_for_count

        t0 = get_difficulty_params_for_count(0, 1)["time_limit"]
        t5 = get_difficulty_params_for_count(5, 1)["time_limit"]
        assert t5 == t0 - 1.0

    def test_time_floor_never_below_3(self):
        from app.utils.difficulty_ramp import get_difficulty_params_for_count, MIN_TIME_LIMIT

        t = get_difficulty_params_for_count(1000, 1)["time_limit"]
        assert t >= MIN_TIME_LIMIT

