from __future__ import annotations

from philiprehberger_csv_kit import (
    CsvPipeline,
    DialectResult,
    QualityResult,
    column_quality,
    column_stats,
    detect_dialect,
    infer_types,
    read_csv,
    stream_csv,
    write_csv,
)

import pytest


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


# --- Streaming ---

def test_stream_csv_chunks(tmp_path):
    csv_file = tmp_path / "stream.csv"
    csv_file.write_text(
        "name,age\nAlice,30\nBob,25\nCarol,35\n", encoding="utf-8"
    )

    chunks = list(stream_csv(csv_file, chunk_size=2))
    assert len(chunks) == 2
    assert len(chunks[0]) == 2
    assert len(chunks[1]) == 1


# --- Column Stats ---

def test_column_stats(tmp_path):
    csv_file = tmp_path / "stats.csv"
    csv_file.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")

    stats = column_stats(csv_file)
    assert stats["age"]["min"] == 25
    assert stats["age"]["max"] == 30
    assert stats["age"]["count"] == 2


# --- Dialect Detection ---

def test_detect_dialect_from_file(tmp_path):
    tsv = tmp_path / "data.tsv"
    tsv.write_text("name\tage\tscore\nAlice\t30\t9.5\nBob\t25\t8.0\n", encoding="utf-8")

    result = detect_dialect(tsv)
    assert isinstance(result, DialectResult)
    assert result.delimiter == "\t"


def test_detect_dialect_from_sample():
    sample = "name;age;score\nAlice;30;9.5\nBob;25;8.0\n"
    result = detect_dialect(sample)
    assert result.delimiter == ";"


def test_detect_dialect_comma_file(tmp_path):
    csv_file = tmp_path / "comma.csv"
    csv_file.write_text("name,age,score\nAlice,30,9.5\nBob,25,8.0\n", encoding="utf-8")

    result = detect_dialect(csv_file)
    assert result.delimiter == ","


def test_detect_dialect_to_dict(tmp_path):
    csv_file = tmp_path / "dict.csv"
    csv_file.write_text("a,b,c\n1,2,3\n4,5,6\n", encoding="utf-8")

    result = detect_dialect(csv_file)
    d = result.to_dict()
    assert "delimiter" in d
    assert "quotechar" in d
    assert "doublequote" in d
    assert "skipinitialspace" in d
    assert "lineterminator" in d


def test_detect_dialect_quoted_fields():
    sample = '"name","age","city"\n"Alice","30","New York"\n"Bob","25","London"\n'
    result = detect_dialect(sample)
    assert result.delimiter == ","
    assert result.quotechar == '"'


# --- Column Quality ---

def test_column_quality_full():
    rows = [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob", "email": "bob@example.com"},
        {"name": "Carol", "email": "carol@example.com"},
    ]
    q = column_quality(rows, "email")
    assert isinstance(q, QualityResult)
    assert q.completeness == 100.0
    assert q.null_count == 0
    assert q.total_count == 3
    assert q.cardinality_ratio == 1.0


def test_column_quality_with_nulls():
    rows = [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob", "email": None},
        {"name": "Carol", "email": ""},
        {"name": "Dave", "email": "dave@example.com"},
    ]
    q = column_quality(rows, "email")
    assert q.null_count == 2
    assert q.completeness == 50.0
    assert q.total_count == 4
    assert q.cardinality_ratio == 0.5


def test_column_quality_cardinality():
    rows = [
        {"status": "active"},
        {"status": "active"},
        {"status": "inactive"},
        {"status": "active"},
    ]
    q = column_quality(rows, "status")
    assert q.cardinality_ratio == 0.5
    assert q.completeness == 100.0


def test_column_quality_empty_rows():
    q = column_quality([], "any")
    assert q.completeness == 0.0
    assert q.null_count == 0
    assert q.total_count == 0


def test_column_quality_missing_column():
    rows = [{"name": "Alice"}]
    with pytest.raises(KeyError, match="email"):
        column_quality(rows, "email")


def test_column_quality_to_dict():
    rows = [{"x": 1}, {"x": 2}]
    q = column_quality(rows, "x")
    d = q.to_dict()
    assert "completeness" in d
    assert "cardinality_ratio" in d
    assert "null_count" in d
    assert "total_count" in d


# --- CsvPipeline ---

def test_pipeline_filter():
    rows = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 17}]
    result = CsvPipeline(rows).filter(lambda r: r["age"] > 18).to_list()
    assert len(result) == 1
    assert result[0]["name"] == "Alice"


def test_pipeline_exclude():
    rows = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 17}]
    result = CsvPipeline(rows).exclude(lambda r: r["age"] > 18).to_list()
    assert len(result) == 1
    assert result[0]["name"] == "Bob"


def test_pipeline_map_column():
    rows = [{"name": "alice"}, {"name": "bob"}]
    result = CsvPipeline(rows).map_column("name", str.upper).to_list()
    assert result[0]["name"] == "ALICE"
    assert result[1]["name"] == "BOB"


def test_pipeline_map_column_missing_key():
    rows = [{"name": "alice"}, {"age": 30}]
    result = CsvPipeline(rows).map_column("name", str.upper).to_list()
    assert result[0]["name"] == "ALICE"
    assert "name" not in result[1]


def test_pipeline_add_column():
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    result = CsvPipeline(rows).add_column("c", lambda r: r["a"] + r["b"]).to_list()
    assert result[0]["c"] == 3
    assert result[1]["c"] == 7


def test_pipeline_rename_column():
    rows = [{"old_name": "Alice"}]
    result = CsvPipeline(rows).rename_column("old_name", "new_name").to_list()
    assert "new_name" in result[0]
    assert "old_name" not in result[0]
    assert result[0]["new_name"] == "Alice"


def test_pipeline_select_columns():
    rows = [{"a": 1, "b": 2, "c": 3}]
    result = CsvPipeline(rows).select_columns(["a", "c"]).to_list()
    assert list(result[0].keys()) == ["a", "c"]


def test_pipeline_sort_by():
    rows = [{"name": "Carol", "age": 35}, {"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]
    result = CsvPipeline(rows).sort_by("age").to_list()
    assert result[0]["name"] == "Alice"
    assert result[2]["name"] == "Carol"


def test_pipeline_sort_by_reverse():
    rows = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]
    result = CsvPipeline(rows).sort_by("age", reverse=True).to_list()
    assert result[0]["name"] == "Bob"


def test_pipeline_group_by():
    rows = [
        {"dept": "eng", "name": "Alice"},
        {"dept": "sales", "name": "Bob"},
        {"dept": "eng", "name": "Carol"},
    ]
    groups = CsvPipeline(rows).group_by("dept")
    assert len(groups["eng"]) == 2
    assert len(groups["sales"]) == 1


def test_pipeline_head():
    rows = [{"i": i} for i in range(10)]
    result = CsvPipeline(rows).head(3).to_list()
    assert len(result) == 3
    assert result[0]["i"] == 0


def test_pipeline_tail():
    rows = [{"i": i} for i in range(10)]
    result = CsvPipeline(rows).tail(2).to_list()
    assert len(result) == 2
    assert result[0]["i"] == 8


def test_pipeline_count():
    rows = [{"a": 1}, {"a": 2}, {"a": 3}]
    assert CsvPipeline(rows).count() == 3


def test_pipeline_first():
    rows = [{"a": 1}, {"a": 2}]
    assert CsvPipeline(rows).first() == {"a": 1}


def test_pipeline_first_empty():
    assert CsvPipeline([]).first() is None


def test_pipeline_len():
    rows = [{"a": 1}, {"a": 2}]
    assert len(CsvPipeline(rows)) == 2


def test_pipeline_iter():
    rows = [{"a": 1}, {"a": 2}]
    collected = list(CsvPipeline(rows))
    assert collected == rows


def test_pipeline_chaining():
    rows = [
        {"name": "Alice", "age": 30, "dept": "eng"},
        {"name": "Bob", "age": 17, "dept": "eng"},
        {"name": "Carol", "age": 25, "dept": "sales"},
    ]
    result = (
        CsvPipeline(rows)
        .filter(lambda r: r["age"] >= 18)
        .map_column("name", str.upper)
        .sort_by("age")
        .to_list()
    )
    assert len(result) == 2
    assert result[0]["name"] == "CAROL"
    assert result[1]["name"] == "ALICE"


def test_pipeline_does_not_mutate_input():
    rows = [{"name": "alice"}]
    CsvPipeline(rows).map_column("name", str.upper).to_list()
    assert rows[0]["name"] == "alice"
