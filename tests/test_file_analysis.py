import pytest
from backend.file_analysis import parse_file_bytes


def test_csv_parser_reports_actual_schema_and_rows():
    parsed = parse_file_bytes("customers.csv", b"name,churn\nAda,0\nBen,1\n")
    assert parsed["metadata"] == {"columns": ["name", "churn"], "rowCount": 2}


def test_invalid_json_and_unsupported_file_are_rejected():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_file_bytes("bad.json", b"{")
    with pytest.raises(ValueError, match="Supported file types"):
        parse_file_bytes("malware.exe", b"x")


def test_path_traversal_filename_is_rejected():
    with pytest.raises(ValueError):
        parse_file_bytes("../secret.txt", b"no")
