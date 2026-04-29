from __future__ import annotations

import json

from philiprehberger_csv_kit import (
    CsvPipeline,
    DialectResult,
    QualityResult,
    column_quality,
    column_stats,
    deduplicate,
    detect_dialect,
    find_duplicates,
    head,
    infer_types,
    read_csv,
    sample,
    stream_csv,
    stream_csv_rows,
    to_dict_list,
    to_json,
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


# --- Streaming rows ---

def test_stream_csv_rows_typed(tmp_path):
    csv_file = tmp_path / "stream_rows.csv"
    csv_file.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")

    rows = list(stream_csv_rows(csv_file, typed=True))
    assert len(rows) == 2
    assert rows[0]["name"] == "Alice"
    assert rows[0]["age"] == 30
    assert isinstance(rows[0]["age"], int)


def test_stream_csv_rows_untyped(tmp_path):
    csv_file = tmp_path / "stream_rows.csv"
    csv_file.write_text("name,age\nAlice,30\n", encoding="utf-8")

    rows = list(stream_csv_rows(csv_file, typed=False))
    assert rows[0]["age"] == "30"


def test_stream_csv_rows_empty(tmp_path):
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("name,age\n", encoding="utf-8")

    rows = list(stream_csv_rows(csv_file))
    assert rows == []


def test_stream_csv_rows_is_lazy(tmp_path):
    csv_file = tmp_path / "lazy.csv"
    csv_file.write_text("x\n1\n2\n3\n4\n5\n", encoding="utf-8")

    gen = stream_csv_rows(csv_file)
    first = next(gen)
    assert first["x"] == 1


# --- Export helpers: to_json / to_dict_list ---

def test_to_json_basic():
    rows = [{"name": "Alice", "age": 30}]
    result = to_json(rows)
    parsed = json.loads(result)
    assert parsed == rows


def test_to_json_compact():
    rows = [{"a": 1}]
    result = to_json(rows, indent=None)
    assert "\n" not in result


def test_to_json_empty():
    assert to_json([]) == "[]"


def test_to_dict_list_all_columns():
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    result = to_dict_list(rows)
    assert result == rows
    # Verify it returns copies, not references
    result[0]["a"] = 999
    assert rows[0]["a"] == 1


def test_to_dict_list_select_columns():
    rows = [{"a": 1, "b": 2, "c": 3}]
    result = to_dict_list(rows, columns=["a", "c"])
    assert result == [{"a": 1, "c": 3}]


def test_to_dict_list_missing_column():
    rows = [{"a": 1}]
    result = to_dict_list(rows, columns=["a", "z"])
    assert result == [{"a": 1, "z": None}]


# --- Column type override ---

def test_infer_types_with_overrides():
    rows = [{"id": "42", "score": "9.5", "active": "true"}]
    result = infer_types(rows, overrides={"id": str, "score": int})
    assert result[0]["id"] == "42"
    assert isinstance(result[0]["id"], str)
    assert result[0]["score"] == 9
    assert isinstance(result[0]["score"], int)
    # active should still be inferred normally
    assert result[0]["active"] is True


def test_infer_types_override_to_bool():
    rows = [{"flag": "1"}, {"flag": "0"}, {"flag": "yes"}]
    result = infer_types(rows, overrides={"flag": bool})
    assert result[0]["flag"] is True
    assert result[1]["flag"] is False
    assert result[2]["flag"] is True


def test_infer_types_override_empty_value():
    rows = [{"val": ""}]
    result = infer_types(rows, overrides={"val": int})
    assert result[0]["val"] is None


def test_read_csv_with_overrides(tmp_path):
    csv_file = tmp_path / "override.csv"
    csv_file.write_text("id,score\n42,9.5\n", encoding="utf-8")

    result = read_csv(csv_file, overrides={"id": str})
    assert result[0]["id"] == "42"
    assert isinstance(result[0]["id"], str)
    assert result[0]["score"] == 9.5


def test_infer_types_override_to_float():
    rows = [{"val": "42"}]
    result = infer_types(rows, overrides={"val": float})
    assert result[0]["val"] == 42.0
    assert isinstance(result[0]["val"], float)


# --- Head ---

def test_head_basic(tmp_path):
    csv_file = tmp_path / "head.csv"
    csv_file.write_text("x\n1\n2\n3\n4\n5\n", encoding="utf-8")

    result = head(csv_file, n=3)
    assert len(result) == 3
    assert result[0]["x"] == 1
    assert result[2]["x"] == 3


def test_head_default_n(tmp_path):
    csv_file = tmp_path / "head.csv"
    lines = "x\n" + "\n".join(str(i) for i in range(10)) + "\n"
    csv_file.write_text(lines, encoding="utf-8")

    result = head(csv_file)
    assert len(result) == 5


def test_head_fewer_rows(tmp_path):
    csv_file = tmp_path / "head.csv"
    csv_file.write_text("x\n1\n2\n", encoding="utf-8")

    result = head(csv_file, n=10)
    assert len(result) == 2


def test_head_typed(tmp_path):
    csv_file = tmp_path / "head.csv"
    csv_file.write_text("x\n42\n", encoding="utf-8")

    typed = head(csv_file, typed=True)
    assert typed[0]["x"] == 42
    assert isinstance(typed[0]["x"], int)

    untyped = head(csv_file, typed=False)
    assert untyped[0]["x"] == "42"


# --- Sample ---

def test_sample_basic(tmp_path):
    csv_file = tmp_path / "sample.csv"
    lines = "x\n" + "\n".join(str(i) for i in range(20)) + "\n"
    csv_file.write_text(lines, encoding="utf-8")

    result = sample(csv_file, n=5, seed=42)
    assert len(result) == 5


def test_sample_reproducible(tmp_path):
    csv_file = tmp_path / "sample.csv"
    lines = "x\n" + "\n".join(str(i) for i in range(20)) + "\n"
    csv_file.write_text(lines, encoding="utf-8")

    r1 = sample(csv_file, n=5, seed=42)
    r2 = sample(csv_file, n=5, seed=42)
    assert r1 == r2


def test_sample_more_than_available(tmp_path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("x\n1\n2\n", encoding="utf-8")

    result = sample(csv_file, n=10)
    assert len(result) == 2


def test_sample_empty(tmp_path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("x\n", encoding="utf-8")

    result = sample(csv_file, n=5)
    assert result == []


# --- Duplicate detection ---

def test_find_duplicates_all_columns():
    rows = [
        {"a": 1, "b": 2},
        {"a": 3, "b": 4},
        {"a": 1, "b": 2},
        {"a": 5, "b": 6},
        {"a": 1, "b": 2},
    ]
    dups = find_duplicates(rows)
    assert len(dups) == 2
    assert all(d == {"a": 1, "b": 2} for d in dups)


def test_find_duplicates_by_column():
    rows = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Alice", "age": 35},
    ]
    dups = find_duplicates(rows, columns=["name"])
    assert len(dups) == 1
    assert dups[0]["name"] == "Alice"
    assert dups[0]["age"] == 35


def test_find_duplicates_no_duplicates():
    rows = [{"a": 1}, {"a": 2}, {"a": 3}]
    assert find_duplicates(rows) == []


def test_find_duplicates_empty():
    assert find_duplicates([]) == []


def test_deduplicate_all_columns():
    rows = [
        {"a": 1, "b": 2},
        {"a": 3, "b": 4},
        {"a": 1, "b": 2},
    ]
    result = deduplicate(rows)
    assert len(result) == 2
    assert result[0] == {"a": 1, "b": 2}
    assert result[1] == {"a": 3, "b": 4}


def test_deduplicate_by_column():
    rows = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Alice", "age": 35},
    ]
    result = deduplicate(rows, columns=["name"])
    assert len(result) == 2
    assert result[0]["age"] == 30  # keeps first occurrence


def test_deduplicate_empty():
    assert deduplicate([]) == []


def test_deduplicate_no_duplicates():
    rows = [{"a": 1}, {"a": 2}]
    result = deduplicate(rows)
    assert len(result) == 2


# --- CsvPipeline new methods ---

def test_pipeline_to_json():
    rows = [{"name": "Alice", "age": 30}]
    result = CsvPipeline(rows).to_json()
    parsed = json.loads(result)
    assert parsed == rows


def test_pipeline_to_json_compact():
    rows = [{"a": 1}]
    result = CsvPipeline(rows).to_json(indent=None)
    assert "\n" not in result


def test_pipeline_to_dict_list():
    rows = [{"a": 1, "b": 2, "c": 3}]
    result = CsvPipeline(rows).to_dict_list(columns=["a", "c"])
    assert result == [{"a": 1, "c": 3}]


def test_pipeline_to_dict_list_all():
    rows = [{"a": 1, "b": 2}]
    result = CsvPipeline(rows).to_dict_list()
    assert result == rows


def test_pipeline_sample():
    rows = [{"i": i} for i in range(20)]
    result = CsvPipeline(rows).sample(5, seed=42).to_list()
    assert len(result) == 5


def test_pipeline_sample_reproducible():
    rows = [{"i": i} for i in range(20)]
    r1 = CsvPipeline(rows).sample(5, seed=42).to_list()
    r2 = CsvPipeline(rows).sample(5, seed=42).to_list()
    assert r1 == r2


def test_pipeline_deduplicate():
    rows = [{"a": 1}, {"a": 2}, {"a": 1}]
    result = CsvPipeline(rows).deduplicate().to_list()
    assert len(result) == 2


def test_pipeline_deduplicate_by_column():
    rows = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Alice", "age": 35},
    ]
    result = CsvPipeline(rows).deduplicate(columns=["name"]).to_list()
    assert len(result) == 2
    assert result[0]["age"] == 30


# ---------------------------------------------------------------------------
# CsvPipeline.aggregate
# ---------------------------------------------------------------------------


def test_aggregate_count():
    rows = [
        {"city": "NYC", "age": 30},
        {"city": "NYC", "age": 25},
        {"city": "LA", "age": 40},
    ]
    result = CsvPipeline(rows).aggregate("city", count=len)
    by_city = {r["city"]: r for r in result}
    assert by_city["NYC"]["count"] == 2
    assert by_city["LA"]["count"] == 1


def test_aggregate_multiple_functions():
    rows = [
        {"city": "NYC", "age": 30},
        {"city": "NYC", "age": 25},
        {"city": "LA", "age": 40},
    ]
    result = CsvPipeline(rows).aggregate(
        "city",
        count=len,
        avg_age=lambda rs: sum(r["age"] for r in rs) / len(rs),
        max_age=lambda rs: max(r["age"] for r in rs),
    )
    by_city = {r["city"]: r for r in result}
    assert by_city["NYC"]["count"] == 2
    assert by_city["NYC"]["avg_age"] == 27.5
    assert by_city["NYC"]["max_age"] == 30
    assert by_city["LA"]["avg_age"] == 40


def test_aggregate_empty_pipeline_returns_empty():
    assert CsvPipeline([]).aggregate("city", count=len) == []


def test_aggregate_preserves_group_key_in_result():
    rows = [{"k": "a", "v": 1}, {"k": "b", "v": 2}]
    result = CsvPipeline(rows).aggregate("k", total=lambda rs: sum(r["v"] for r in rs))
    keys = {r["k"] for r in result}
    assert keys == {"a", "b"}

