"""Difficulty ramp configuration and progression logic (G02_F04_SF06)."""

BASE_TIME_LIMIT: float = 10.0   # Starting time limit per question (seconds)
TIME_BONUS_PER_LEVEL: float = 1.0  # Extra seconds granted per level increment

def get_difficulty_params_for_count(correct_count: int) -> dict:
    """Return the current difficulty parameters based on the correct answer count.

    Difficulty scaling:
    - Base time_limit = 10s at level 1
    - Every 3 correct answers: level += 1, time_limit += TIME_BONUS_PER_LEVEL
    - Higher levels have harder questions (more operators, larger numbers), so
      players receive progressively more time to compensate.

    Args:
        correct_count: Total correct answers so far in the session.

    Returns:
        A dictionary with:
        - "level": Current ramp level (starts at 1).
        - "time_limit": Time limit in seconds for the current level.
    """
    increments = correct_count // 3
    level = increments + 1
    time_limit = BASE_TIME_LIMIT + increments * TIME_BONUS_PER_LEVEL

    return {
        "level": level,
        "time_limit": time_limit,
    }