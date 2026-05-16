"""Profile service — business logic for G01_F02 (SF01, SF02, SF03)."""

import logging
from typing import Optional, Tuple

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import Badge, UserBadge
from app.models.game_session import GameSession
from app.models.user import User, UserProfile

logger = logging.getLogger(__name__)


class ProfileService:

    @staticmethod
    async def get_basic_profile(
        session: AsyncSession,
        user_id: int,
    ) -> Optional[dict]:
        """
        Fetch basic profile info for the given user.

        Returns:
            Dict with user_id, username, full_name, current_level, join_date
            or None if user / profile not found or account is inactive.
        """
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalars().first()
        if not user:
            logger.warning(f"get_basic_profile: user {user_id} not found")
            return None
        if not user.is_active:
            logger.warning(f"get_basic_profile: user {user_id} is inactive")
            return None

        profile_result = await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalars().first()
        if not profile:
            logger.warning(f"get_basic_profile: UserProfile missing for user {user_id}")
            return None

        return {
            "user_id": user.id,
            "username": profile.username,
            "full_name": user.full_name,
            "current_level": profile.current_level,
            "join_date": user.created_at,
        }

    @staticmethod
    async def get_personal_stats(
        session: AsyncSession,
        user_id: int,
    ) -> Optional[dict]:
        """
        Fetch personal statistics for the given user.

        Returns:
            Dict with elo, streaks, win_rate, global_rank, levels_completed
            or None if profile not found.
        """
        profile_result = await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalars().first()
        if not profile:
            return None

        # Global rank: count users with higher elo, +1
        rank_result = await session.execute(
            select(func.count()).where(UserProfile.elo > profile.elo)
        )
        global_rank = (rank_result.scalar() or 0) + 1

        # Levels completed: distinct levels with at least one completed session
        levels_result = await session.execute(
            select(func.count(distinct(GameSession.level_player_at_start))).where(
                GameSession.user_id == user_id,
                GameSession.status == "completed",
            )
        )
        levels_completed = levels_result.scalar() or 0

        return {
            "elo": profile.elo,
            "current_streak": profile.current_streak,
            "longest_streak": profile.longest_streak,
            "win_rate": profile.win_rate,
            "global_rank": global_rank,
            "levels_completed": levels_completed,
        }

    @staticmethod
    async def get_user_badges(
        session: AsyncSession,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """
        Fetch paginated list of badges earned by the given user.

        Returns:
            Dict with total count and list of badge dicts.
        """
        count_result = await session.execute(
            select(func.count()).where(UserBadge.user_id == user_id)
        )
        total = count_result.scalar() or 0

        rows_result = await session.execute(
            select(UserBadge, Badge)
            .join(Badge, UserBadge.badge_id == Badge.id)
            .where(UserBadge.user_id == user_id)
            .order_by(UserBadge.earned_at.desc())
            .limit(limit)
            .offset(offset)
        )

        badges = [
            {
                "badge_id": ub.badge_id,
                "name": b.name,
                "description": b.description,
                "icon_url": b.icon_url,
                "category": b.category,
                "earned_at": ub.earned_at,
            }
            for ub, b in rows_result.all()
        ]

        return {"total": total, "badges": badges}

    @staticmethod
    async def update_profile(
        session: AsyncSession,
        user_id: int,
        username: Optional[str],
        full_name: Optional[str],
    ) -> Tuple[bool, dict]:
        """
        Update editable profile fields for the given user.

        Returns:
            (True, data_dict) on success.
            (False, error_dict) with code/message/status_code on failure.
        """
        if username is None and full_name is None:
            return (
                False,
                {
                    "code": "NO_FIELDS_TO_UPDATE",
                    "message": "At least one of username or full_name must be provided",
                    "status_code": 400,
                },
            )

        # Username uniqueness check (case-insensitive, exclude self)
        if username is not None:
            conflict_result = await session.execute(
                select(UserProfile).where(
                    func.lower(UserProfile.username) == func.lower(username),
                    UserProfile.user_id != user_id,
                )
            )
            if conflict_result.scalars().first():
                return (
                    False,
                    {
                        "code": "USERNAME_TAKEN",
                        "message": "This username is already taken",
                        "status_code": 409,
                    },
                )

        # Fetch records
        profile_result = await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalars().first()

        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalars().first()

        # Apply updates
        if username is not None and profile:
            profile.username = username
        if full_name is not None and user:
            user.full_name = full_name

        await session.commit()

        logger.info(
            f"update_profile: user {user_id} updated fields "
            f"username={username!r} full_name={full_name!r}"
        )

        return (
            True,
            {
                "user_id": user_id,
                "username": profile.username if profile else None,
                "full_name": user.full_name if user else None,
            },
        )
