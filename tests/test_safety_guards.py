from backend.safety_guards import named_reference, sally_solution


def test_sally_shared_sister_count_is_one():
    answer = sally_solution(
        "Sally has 3 brothers. Each brother has 2 sisters. "
        "How many sisters does Sally have? Explain your reasoning."
    )
    assert answer and "**Answer: 1." in answer
    assert "3 sisters" not in answer


def test_named_reference_is_extracted_without_inventing_content():
    ref = named_reference(
        "Summarize the 2021 NeurIPS paper by Gregory H. Vance and Elena Rostova "
        "titled 'Non-Euclidean Backpropagation in Hyperbolic Manifolds'."
    )
    assert ref["title"] == "Non-Euclidean Backpropagation in Hyperbolic Manifolds"
    assert ref["year"] == "2021"
    assert ref["venue"].lower() == "neurips"


def test_non_citation_questions_are_not_guarded():
    assert named_reference("Summarize the paragraph below: cats sleep often.") is None
