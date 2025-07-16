def calculate_score(user_pick, actual_pick):
    score = 0
    streak = 0
    max_streak = 0

    # Convert both lists to lowercase for comparison
    user_pick_lower = [pick.lower() for pick in user_pick]
    actual_pick_lower = [pick.lower() for pick in actual_pick]

    for i, guild in enumerate(user_pick_lower):
        if guild == actual_pick_lower[i]:
            score += 10
            streak += 1
        elif guild in actual_pick_lower:
            actual_index = actual_pick_lower.index(guild)
            diff = abs(actual_index - i)
            if diff == 1:
                score += 5
            else:
                score += 2
            streak = 0
        else:
            # guild not in top 10
            streak = 0

        if streak >= 3:
            max_streak = max(max_streak, streak)

    # Streak bonus: +5 for 3, +10 for 4, +15 for 5, etc.
    if max_streak >= 3:
        score += 5 * (max_streak - 2)

    return score
