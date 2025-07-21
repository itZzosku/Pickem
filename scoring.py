from typing import List, Union


def calculate_score(user_pick: List[str], actual_pick: List[str]) -> int:
    """Calculate the score based on user's guild predictions compared to actual rankings.

    Points system:
    - Exact match with streak multiplier:
        * First correct: 10 points
        * Second in streak: 15 points
        * Third in streak: 18 points
        * Fourth+ in streak: 20 points
    - Off by one position: 5 points
    - Wrong position but in top 10: 2 points
    - Not in top 10: 0 points

    Args:
        user_pick: List of guild names in user's predicted order
        actual_pick: List of guild names in actual current order

    Returns:
        int: Total calculated score

    Raises:
        ValueError: If input lists are empty or None
    """
    if not user_pick or not actual_pick:
        raise ValueError("Both user_pick and actual_pick must contain values")

    def get_streak_score(streak: int) -> int:
        """Determine score based on current streak length."""
        streak_scores = {
            1: 10,  # 1x multiplier
            2: 15,  # 1.5x multiplier
            3: 18,  # 1.75x multiplier
        }
        return streak_scores.get(streak, 20)  # 2x multiplier for streak >= 4

    def is_next_position_match(current_idx: int, user_guilds: List[str],
                               actual_guilds: List[str]) -> bool:
        """Check if next position could form part of a streak."""
        next_idx = current_idx + 1
        if next_idx >= len(user_guilds):
            return False

        next_guild = user_guilds[next_idx]
        return (next_guild in actual_guilds and
                actual_guilds.index(next_guild) == next_idx)

    # Normalize guild names by stripping whitespace
    user_guilds = [pick.strip() for pick in user_pick]
    actual_guilds = [pick.strip() for pick in actual_pick]

    position_scores = []
    current_streak = 0

    for idx, guild in enumerate(user_guilds):
        if idx >= len(actual_guilds):
            break

        if guild == actual_guilds[idx]:
            # Exact position match
            current_streak += 1
            position_scores.append(get_streak_score(current_streak))
        elif guild in actual_guilds:
            # Guild is in top 10 but wrong position
            actual_idx = actual_guilds.index(guild)
            position_diff = abs(actual_idx - idx)

            if (position_diff == 1 and
                    is_next_position_match(idx, user_guilds, actual_guilds)):
                position_scores.append(5)  # Off by one
                continue

            position_scores.append(2)  # Wrong position
            current_streak = 0
        else:
            # Guild not in top 10
            position_scores.append(0)
            current_streak = 0

    return sum(position_scores)
