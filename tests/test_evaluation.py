from eval.run import percentile


def test_percentile_uses_nearest_rank_in_a_sorted_copy() -> None:
    values = [100.0, 10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 0.5) == 30.0
    assert percentile(values, 0.95) == 100.0
    assert values == [100.0, 10.0, 20.0, 30.0, 40.0]
