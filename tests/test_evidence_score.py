from backend.confidence import calculate_evidence_score

def _sources(n=6, tier='academic'):
    return [{'url': f'https://s{i}.example.org/paper', 'tier': tier, 'relevance_score': .9} for i in range(n)]

def _claims(n=2, supported=2, verified=True):
    return [{'supporting_sources': list(range(supported)), 'verified': verified} for _ in range(n)]

def test_one_source_is_capped():
    result = calculate_evidence_score(_sources(1), _claims(), {'available': True})
    assert result['percentage'] <= 50
    assert any(c['reason'] == 'fewer_than_3_independent_sources' for c in result['caps'])

def test_six_strong_sources_can_reach_high():
    result = calculate_evidence_score(_sources(), _claims(2, 2), {'available': True})
    assert result['percentage'] == 100
    assert result['caps'] == []

def test_conflicting_sources_reduce_agreement():
    result = calculate_evidence_score(_sources(), _claims(2, 1), {'available': True})
    assert result['components']['agreement'] == 0
    assert result['percentage'] < 100

def test_failed_verification_caps_score():
    result = calculate_evidence_score(_sources(), _claims(), {'available': True, 'failed': True})
    assert result['percentage'] <= 60

def test_dataset_claim_without_experiment_caps_score():
    result = calculate_evidence_score(_sources(), _claims(), {'available': True}, dataset_specific=True, experiment_run=False)
    assert result['percentage'] <= 70
