"""Tests for User Profile endpoints — G01_F02 (SF01, SF02, SF03)."""

import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
PROFILE_URL = "/api/v1/profile"
STATS_URL = "/api/v1/profile/stats"
BADGES_URL = "/api/v1/profile/badges"

VALID_USER = {
    "email": "profileuser@example.com",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "full_name": "Profile User",
}


async def register_and_login(client: AsyncClient, payload: dict = VALID_USER) -> str:
    """Helper: register a user and return a valid access token."""
    await client.post(REGISTER_URL, json=payload)
    resp = await client.post(
        LOGIN_URL,
        json={"email": payload["email"], "password": payload["password"]},
    )
    return resp.json()["data"]["access_token"]


# ---------------------------------------------------------------------------
# SF01 — Basic Profile
# ---------------------------------------------------------------------------


class TestBasicProfile:

    async def test_get_profile_success(self, async_client: AsyncClient):
        token = await register_and_login(async_client)
        resp = await async_client.get(
            PROFILE_URL, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        profile = data["data"]
        assert profile["user_id"] is not None
        assert isinstance(profile["username"], str) and len(profile["username"]) > 0
        assert profile["full_name"] == "Profile User"
        assert profile["current_level"] == 1
        assert "join_date" in profile

    async def test_get_profile_null_full_name(self, async_client: AsyncClient):
        payload = {
            "email": "nofullname@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }
        token = await register_and_login(async_client, payload)
        resp = await async_client.get(
            PROFILE_URL, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["full_name"] is None

    async def test_get_profile_unauthenticated(self, async_client: AsyncClient):
        resp = await async_client.get(PROFILE_URL)
        assert resp.status_code == 401

    async def test_get_profile_invalid_token(self, async_client: AsyncClient):
        resp = await async_client.get(
            PROFILE_URL, headers={"Authorization": "Bearer invalidtoken"}
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# SF02 — Personal Statistics
# ---------------------------------------------------------------------------


class TestPersonalStats:

    async def test_get_stats_success(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "statsuser@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.get(
            STATS_URL, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        stats = data["data"]
        assert stats["elo"] == 1000
        assert stats["current_streak"] == 0
        assert stats["longest_streak"] == 0
        assert stats["win_rate"] == 0.0
        assert stats["global_rank"] >= 1
        assert stats["levels_completed"] == 0

    async def test_get_stats_unauthenticated(self, async_client: AsyncClient):
        resp = await async_client.get(STATS_URL)
        assert resp.status_code == 401

    async def test_get_stats_rank_is_positive(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "rankuser@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.get(
            STATS_URL, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["global_rank"] >= 1


# ---------------------------------------------------------------------------
# SF03 — Badges
# ---------------------------------------------------------------------------


class TestBadges:

    async def test_get_badges_empty(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "badgeuser@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.get(
            BADGES_URL, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0
        assert data["data"]["badges"] == []

    async def test_get_badges_unauthenticated(self, async_client: AsyncClient):
        resp = await async_client.get(BADGES_URL)
        assert resp.status_code == 401

    async def test_get_badges_invalid_limit(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "badgelimit@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.get(
            f"{BADGES_URL}?limit=200",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_get_badges_invalid_offset(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "badgeoffset@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.get(
            f"{BADGES_URL}?offset=-1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# SF04 — Update Profile
# ---------------------------------------------------------------------------

UPDATE_URL = "/api/v1/profile"


class TestUpdateProfile:

    async def test_update_username_success(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "upd_username@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "brand_new_name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["username"] == "brand_new_name"

    async def test_update_full_name_success(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "upd_fname@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "full_name": "Old Name",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"full_name": "New Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["full_name"] == "New Name"

    async def test_update_both_fields_success(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "upd_both@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "full_name": "Original",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "both_updated", "full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["username"] == "both_updated"
        assert data["full_name"] == "Updated Name"

    async def test_update_no_fields(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "upd_nofields@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "NO_FIELDS_TO_UPDATE"

    async def test_update_username_taken(self, async_client: AsyncClient):
        # User A claims a unique username
        token_a = await register_and_login(
            async_client,
            {
                "email": "taken_a@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp_a = await async_client.patch(
            UPDATE_URL,
            json={"username": "claimed_username"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_a.status_code == 200
        # User B tries to claim the same username
        token_b = await register_and_login(
            async_client,
            {
                "email": "taken_b@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "claimed_username"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "USERNAME_TAKEN"

    async def test_update_username_same_as_self(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "same_self@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        current = (
            await async_client.get(
                PROFILE_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
        ).json()["data"]["username"]
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": current},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_update_username_too_short(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "short_u@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "ab"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_update_username_too_long(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "long_u@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "a" * 31},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_update_username_with_space(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "space_u@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "has space"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_update_unauthenticated(self, async_client: AsyncClient):
        resp = await async_client.patch(UPDATE_URL, json={"username": "test_user"})
        assert resp.status_code == 401
