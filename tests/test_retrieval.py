from app.repositories import query_terms


def test_query_expansion_maps_customer_language_to_policy_terms() -> None:
    assert {"charged", "billing", "payment", "refund"} <= query_terms(
        "Why was I charged twice?"
    )
    assert {"cancel", "subscription", "cancellation"} <= query_terms(
        "Please cancel at renewal"
    )


def test_stop_words_are_removed() -> None:
    assert query_terms("How do I do it?") == set()
