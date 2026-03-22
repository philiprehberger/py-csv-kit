from __future__ import annotations

from philiprehberger_csv_kit import read_csv, write_csv, infer_types


# --- Read / Write Roundtrip ---

def test_read_write_roundtrip(tmp_path):
    csv_file = tmp_path / "data.csv"
    rows = [
        {"name": "Alice", "age": "30", "score": "9.5"},
        {"name": "Bob", "age": "25", "score": "8.0"},
    ]

    write_csv(csv_file, rows)
    result = read_csv(csv_file, typed=False)

    assert len(result) == 2
    assert result[0]["name"] == "Alice"
    assert result[0]["age"] == "30"
    assert result[1]["name"] == "Bob"


def test_read_csv_with_type_inference(tmp_path):
    csv_file = tmp_path / "typed.csv"
    csv_file.write_text("name,age,score\nAlice,30,9.5\n", encoding="utf-8")

    result = read_csv(csv_file, typed=True)

    assert result[0]["name"] == "Alice"
    assert result[0]["age"] == 30
    assert isinstance(result[0]["age"], int)
    assert result[0]["score"] == 9.5
    assert isinstance(result[0]["score"], float)


# --- Type Inference ---

def test_infer_types_int():
    rows = [{"val": "42"}]
    result = infer_types(rows)
    assert result[0]["val"] == 42
    assert isinstance(result[0]["val"], int)


def test_infer_types_float():
    rows = [{"val": "3.14"}]
    result = infer_types(rows)
    assert result[0]["val"] == 3.14
    assert isinstance(result[0]["val"], float)


def test_infer_types_bool():
    rows = [{"a": "true", "b": "false", "c": "True", "d": "FALSE"}]
    result = infer_types(rows)
    assert result[0]["a"] is True
    assert result[0]["b"] is False
    assert result[0]["c"] is True
    assert result[0]["d"] is False


def test_infer_types_none():
    rows = [{"a": "", "b": "hello"}]
    result = infer_types(rows)
    assert result[0]["a"] is None
    assert result[0]["b"] == "hello"


def test_infer_types_string_preserved():
    rows = [{"val": "not-a-number"}]
    result = infer_types(rows)
    assert result[0]["val"] == "not-a-number"


# --- Column Filter ---

def test_write_with_column_filter(tmp_path):
    csv_file = tmp_path / "filtered.csv"
    rows = [
        {"name": "Alice", "age": "30", "secret": "hidden"},
    ]

    write_csv(csv_file, rows, columns=["name", "age"])
    result = read_csv(csv_file, typed=False)

    assert list(result[0].keys()) == ["name", "age"]
    assert "secret" not in result[0]


# --- Empty CSV ---

def test_empty_csv(tmp_path):
    csv_file = tmp_path / "empty.csv"

    write_csv(csv_file, [])
    content = csv_file.read_text(encoding="utf-8")
    assert content == ""


def test_read_empty_csv_with_headers(tmp_path):
    csv_file = tmp_path / "headers_only.csv"
    csv_file.write_text("name,age\n", encoding="utf-8")

    result = read_csv(csv_file, typed=True)
    assert result == []
