"""The experiment's shared ranking and tie-breaking rules."""

RANK_COLUMNS = [
    "mean_question_f1",
    "exact_match_rate",
    "mean_question_precision",
    "average_selected_chunks",
]
# RANK_ASCENDING = [False, False, False, True]


def rank_key(row):
    """Prefer F1, exact match and precision, then fewer selected chunks."""
    return tuple(
        -row[key] if key == "average_selected_chunks" else row[key] for key in RANK_COLUMNS
    )


def group_winners(rows):
    """Choose the best row for each representation/selector pair."""
    winners = {}
    for row in rows:
        key = (row["representation"], row["method"])
        if key not in winners or rank_key(row) > rank_key(winners[key]):
            winners[key] = row
            
    # Keep the first encountered setting when all ranking metrics tie.
    return sorted(winners.values(), key=rank_key, reverse=True)
