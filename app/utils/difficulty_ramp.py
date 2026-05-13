"""Difficulty ramp configuration and progression logic (G02_F04_SF06)."""

MIN_TIME_LIMIT: float = 3.0  # Floor: never drop below 3 seconds

def get_difficulty_params_for_count(correct_count: int, player_level: int) -> dict:
    """
    Return the current difficulty parameters based on the correct answer count.

    This is a helper function that combines the logic of determining the current
    ramp level and fetching the corresponding question generation parameters.
    Difficulty scaling:
    - Base time_limit = 15s
    - Base level = player_level - 5
    - Every 5 correct answers:
        - time_limit -= 1
        - level += 1

    Args:
        correct_count: Total correct answers so far in the session.
        player_level: The player's current level.
        
    Returns:
        A dictionary containing the current difficulty parameters, including:
        - "level": The current ramp level.  
        - "time_limit": The time limit for answering questions at the current level.
    """
    base_time_limit = 15.0
    base_level = max(player_level - 5, 1)  # Ensure base level is at least 1

    # Calculate increments based on correct_count
    increments = correct_count // 5
    time_limit = max(base_time_limit - increments, MIN_TIME_LIMIT)
    level = base_level + increments

    return {
        "level": level,
        "time_limit": time_limit,
    }