"""The experiment's shared ranking and tie-breaking rules."""
RANK_COLUMNS = ["mean_question_f1", "exact_match_rate", "mean_question_precision", "average_selected_chunks"]
RANK_ASCENDING = [False, False, False, True]


def rank_key(row):
    return tuple(-row[key] if key == "average_selected_chunks" else row[key] for key in RANK_COLUMNS)


def group_winners(rows):
    winners = {}
    for row in rows:
        key = (row["representation"], row["method"])
        if key not in winners or rank_key(row) > rank_key(winners[key]):
            winners[key] = row
    # Stable sorting retains input order on a complete tie; never combine columns from different rows.
    return sorted(winners.values(), key=rank_key, reverse=True)
