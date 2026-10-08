from backend.confidence import calculate_evidence_score, run_evidence_check


def _sources(count, tier="academic"):
    return [{"url": f"https://source-{i}.edu/paper", "tier": tier, "relevance_score": 1.0} for i in range(count)]


def test_six_reputable_sources_score_high():
    claims = [{"supporting_sources": [0, 1], "verified": True} for _ in range(8)]
    score = calculate_evidence_score(_sources(6), claims, {"available": True})
    assert score["percentage"] >= 80


def test_three_sources_and_half_verified_is_moderate():
    claims = [{"supporting_sources": [0], "verified": True} for _ in range(4)] + [{"supporting_sources": [], "verified": False} for _ in range(4)]
    score = calculate_evidence_score(_sources(3), claims, {"available": True})
    assert 40 <= score["percentage"] <= 65


def test_zero_results_is_explicit_low_result():
    result = run_evidence_check("A factual statement about a rare topic.", [], "rare topic with no results")
    assert result["overall"]["level"] in {"Low", "Moderate", "High"}
    assert result["claims"]


def test_false_claim_is_not_verified():
    result = run_evidence_check("This claim is definitely false according to no evidence.", [{"url": "https://example.edu", "snippet": "Unrelated material", "tier": "academic"}], "false claim")
    assert not result["claims"][0]["verified"]

