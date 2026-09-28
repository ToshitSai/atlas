"""Tests for Hugging Face reference parsing (sections 11 & 13) and intelligent
target detection (section 12)."""
import pytest

from backend import hf_datasets
from backend.hf_datasets import parse_hf_reference, _detect_target, score_candidate


# ---------------------------------------------------------------------------
# Section 11 / 13: URL handling — general page vs specific dataset vs none
# ---------------------------------------------------------------------------
def test_general_datasets_page_is_not_a_dataset():
    for url in [
        "https://huggingface.co/datasets",
        "https://huggingface.co/datasets/",
        "http://huggingface.co/datasets?sort=downloads",
    ]:
        res = parse_hf_reference(url)
        assert res["kind"] == "general", url
        assert res["repo_id"] is None


def test_specific_dataset_url():
    res = parse_hf_reference("https://huggingface.co/datasets/gusdelact/credit-card-fraud-curated")
    assert res["kind"] == "specific"
    assert res["repo_id"] == "gusdelact/credit-card-fraud-curated"


def test_specific_url_with_trailing_segments():
    res = parse_hf_reference("https://huggingface.co/datasets/owner/name/tree/main/data")
    assert res["kind"] == "specific"
    assert res["repo_id"] == "owner/name"

    res2 = parse_hf_reference("https://huggingface.co/datasets/owner/name/resolve/main/train.parquet")
    assert res2["repo_id"] == "owner/name"


def test_url_embedded_in_sentence():
    res = parse_hf_reference("Improve fraud detection using https://huggingface.co/datasets/gusdelact/credit-card-fraud-curated please")
    assert res["kind"] == "specific"
    assert res["repo_id"] == "gusdelact/credit-card-fraud-curated"


def test_bare_repo_id():
    assert parse_hf_reference("gusdelact/credit-card-fraud-curated")["kind"] == "specific"


def test_non_hf_text_is_none():
    for text in ["", "improve fraud detection", "https://example.com/data", None]:
        assert parse_hf_reference(text)["kind"] == "none"


# ---------------------------------------------------------------------------
# Section 12: intelligent target detection
# ---------------------------------------------------------------------------
def _df(cols):
    import pandas as pd
    return pd.DataFrame({c: [0, 1] for c in cols})


def test_detect_target_prefers_is_fraud():
    df = _df(["amount", "v1", "v2", "is_fraud"])
    assert _detect_target(df) == "is_fraud"


def test_detect_target_fraud_label():
    df = _df(["feature_a", "feature_b", "fraud"])
    assert _detect_target(df) == "fraud"


def test_detect_target_class_column():
    df = _df(["x1", "x2", "class"])
    assert _detect_target(df) == "class"


def test_detect_target_hint_wins_over_decoy():
    # A low-cardinality integer decoy must not beat an explicit label hint.
    df = _df(["some_flag", "row_id", "is_fraud"])
    assert _detect_target(df) == "is_fraud"


def test_detect_target_falls_back_when_no_hint():
    # DOCUMENTED current behaviour (section 12 gap): with no recognisable label
    # hint, the detector falls back to the last column rather than asking the
    # user. Asserted so any future change to this contract is deliberate.
    import pandas as pd
    df = pd.DataFrame({"alpha": ["a", "b"], "beta": ["c", "d"]})
    assert _detect_target(df) == "beta"


def test_enrich_candidates_adds_verified_metadata_and_dedupes_forks(monkeypatch):
    def fake_inspect(repo_id, **_kwargs):
        return {
            "rowCount": 1200,
            "targetColumn": "is_fraud",
            "featureCount": 30,
            "availableSplits": {"train": ["train.parquet"], "test": ["test.parquet"]},
            "previewFile": "train.parquet",
            "license": "mit",
            "format": "parquet",
            "sizeCategory": "1K<n<10K",
        }

    monkeypatch.setattr(hf_datasets, "inspect_dataset", fake_inspect)
    cards = hf_datasets.enrich_candidates([
        {"repoId": "team/fraud-dataset", "description": "Fraud classification"},
        {"repoId": "fork/fraud-dataset-splits", "description": "Copied fraud classification"},
    ])
    assert len(cards) == 1
    assert cards[0]["featureCount"] == 30
    assert cards[0]["targetColumn"] == "is_fraud"
    assert cards[0]["previewVerified"] is True


def test_large_candidate_is_penalized_and_has_an_executable_sampling_plan():
    score, reasons = score_candidate({"repoId": "team/fraud", "sizeCategory": "10M<n<100M",
                                      "samplingPlan": "Will train on a 200,000-row sample."}, "improve fraud detection")
    assert score < 0
    assert any("200,000-row sample" in reason for reason in reasons)
    assert hf_datasets.sandbox_sample_rows("10M<n<100M") == 200_000
