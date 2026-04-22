def aggregate_score(auto_score: float, human_bonus: float = 0.0, user_bonus: float = 0.0) -> float:
    raw_score = auto_score + human_bonus + user_bonus
    if raw_score < 0.0:
        return 0.0
    if raw_score > 1.0:
        return 1.0
    return raw_score
