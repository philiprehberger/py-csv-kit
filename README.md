# philiprehberger-csv-kit

[![Tests](https://github.com/philiprehberger/py-csv-kit/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-csv-kit/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-csv-kit.svg)](https://pypi.org/project/philiprehberger-csv-kit/)
[![Last updated](https://img.shields.io/github/last-commit/philiprehberger/py-csv-kit)](https://github.com/philiprehberger/py-csv-kit/commits/main)

![philiprehberger-csv-kit](https://raw.githubusercontent.com/philiprehberger/py-csv-kit/main/package-card.webp)

Enhanced CSV reader and writer with automatic type inference.

## Installation

```bash
pip install philiprehberger-csv-kit
```

## Usage

```python
from philiprehberger_csv_kit import read_csv

rows = read_csv("data.csv")
# [{"name": "Alice", "age": 30, "score": 9.5}, ...]
```

Values are automatically cast to `int`, `float`, `bool`, or `None`. Disable with `typed=False`:

```python
rows = read_csv("data.csv", typed=False)
# [{"name": "Alice", "age": "30", "score": "9.5"}, ...]
```

### Writing CSV

```python
from philiprehberger_csv_kit import write_csv

rows = [
    {"name": "Alice", "age": 30, "score": 9.5},
    {"name": "Bob", "age": 25, "score": 8.0},
]

write_csv("output.csv", rows)
write_csv("output.csv", rows, columns=["name", "age"])  # select columns
```

### Streaming large files

```python
from philiprehberger_csv_kit import stream_csv, stream_csv_rows

# Chunked streaming (lists of rows)
for chunk in stream_csv("large.csv", chunk_size=500):
    for row in chunk:
        process(row)

# Row-by-row streaming (minimal memory usage)
for row in stream_csv_rows("large.csv"):
    process(row)
```

### Column type override

```python
from philiprehberger_csv_kit import read_csv, infer_types

# Force specific columns to a type instead of auto-inferring
rows = read_csv("data.csv", overrides={"id": str, "score": int})

# Also available on infer_types directly
raw = [{"id": "42", "score": "9.5"}]
typed = infer_types(raw, overrides={"id": str, "score": int})
# [{"id": "42", "score": 9}]
```

### Quick inspection

```python
from philiprehberger_csv_kit import head, sample

# First 5 rows (without loading the entire file)
rows = head("data.csv", n=5)

# Random sample of 10 rows (reproducible with seed)
rows = sample("data.csv", n=10, seed=42)
```

### Export helpers

```python
from philiprehberger_csv_kit import read_csv, to_json, to_dict_list

rows = read_csv("data.csv")

# Serialize to JSON string
json_str = to_json(rows, indent=2)

# Extract specific columns as a list of dicts
subset = to_dict_list(rows, columns=["name", "age"])
```

### Duplicate detection

```python
from philiprehberger_csv_kit import read_csv, find_duplicates, deduplicate

rows = read_csv("data.csv")

# Find duplicate rows
dupes = find_duplicates(rows)
dupes_by_name = find_duplicates(rows, columns=["name"])

# Remove duplicates (keeps first occurrence)
unique = deduplicate(rows)
unique_by_name = deduplicate(rows, columns=["name"])
```

### Column statistics

```python
from philiprehberger_csv_kit import column_stats

stats = column_stats("data.csv")
# {"age": {"min": 25, "max": 30, "unique": 2, "nulls": 0, "count": 2}, ...}

# Analyse specific columns only
stats = column_stats("data.csv", columns=["age", "score"])
```

### Dialect detection

```python
from philiprehberger_csv_kit import detect_dialect

# Detect from a file
result = detect_dialect("data.tsv")
print(result.delimiter)   # "\t"
print(result.quotechar)   # '"'

# Detect from a raw text sample
result = detect_dialect("name;age;score\nAlice;30;9.5\n")
print(result.delimiter)   # ";"
```

### Column data quality

```python
from philiprehberger_csv_kit import read_csv, column_quality

rows = read_csv("data.csv")
quality = column_quality(rows, "email")
print(quality.completeness)      # 87.5  (percentage of non-null values)
print(quality.cardinality_ratio)  # 0.95  (unique values / total rows)
print(quality.null_count)         # 2
```

### Transformation pipeline

```python
from philiprehberger_csv_kit import read_csv, CsvPipeline

rows = read_csv("employees.csv")

result = (
    CsvPipeline(rows)
    .filter(lambda r: r["age"] > 18)
    .map_column("name", str.upper)
    .deduplicate(columns=["name"])
    .sort_by("age")
    .to_list()
)

# Export pipeline results as JSON
json_str = CsvPipeline(rows).filter(lambda r: r["active"] is True).to_json()

# Random sample from pipeline
sampled = CsvPipeline(rows).sample(10, seed=42).to_list()

# Group by department
groups = (
    CsvPipeline(rows)
    .filter(lambda r: r["active"] is True)
    .group_by("department")
)
# {"Engineering": [...], "Sales": [...]}

# Aggregate per group — supply named aggregations as kwargs
summary = (
    CsvPipeline(rows)
    .aggregate(
        "department",
        count=len,
        avg_age=lambda rs: sum(r["age"] for r in rs) / len(rs),
        max_salary=lambda rs: max(r["salary"] for r in rs),
    )
)
# [
#   {"department": "Engineering", "count": 12, "avg_age": 31.4, "max_salary": 180000},
#   {"department": "Sales", "count": 8, "avg_age": 28.7, "max_salary": 140000},
# ]
```

### Distinct column values

```python
from philiprehberger_csv_kit import CsvPipeline

rows = [
    {"city": "NYC"},
    {"city": "LA"},
    {"city": "NYC"},
    {"city": "Chicago"},
]
CsvPipeline(rows).distinct("city")
# ["NYC", "LA", "Chicago"]
```

Preserves first-seen order and is a terminal operation (returns a list, not a pipeline).

### Type inference

```python
from philiprehberger_csv_kit import infer_types

raw = [{"val": "42"}, {"val": "3.14"}, {"val": "true"}, {"val": ""}]
typed = infer_types(raw)
# [{"val": 42}, {"val": 3.14}, {"val": True}, {"val": None}]
```

## API

| Function / Class | Description |
|---|---|
| `read_csv(path, typed=True, encoding="utf-8", overrides=None)` | Read CSV file, return list of dicts. Infers types when `typed=True`. Optional type overrides per column. |
| `write_csv(path, rows, columns=None, encoding="utf-8")` | Write list of dicts to CSV. Optional column filter. |
| `stream_csv(path, chunk_size=1000, encoding="utf-8")` | Generator yielding chunks of row dicts for memory-efficient reading. |
| `stream_csv_rows(path, typed=True, encoding="utf-8")` | Generator yielding individual row dicts for true row-by-row streaming. |
| `infer_types(rows, overrides=None)` | Cast string values to int, float, bool, or None. Optional per-column type overrides. |
| `head(path, n=5, typed=True, encoding="utf-8")` | Return the first *n* rows from a CSV file without loading the entire file. |
| `sample(path, n=5, typed=True, encoding="utf-8", seed=None)` | Return a random sample of *n* rows from a CSV file. |
| `to_json(rows, indent=2, ensure_ascii=False)` | Serialize a list of row dicts to a JSON string. |
| `to_dict_list(rows, columns=None)` | Return a filtered copy of rows as a list of plain dicts. |
| `find_duplicates(rows, columns=None)` | Find duplicate rows. Returns second and subsequent occurrences. |
| `deduplicate(rows, columns=None)` | Remove duplicate rows, keeping the first occurrence. |
| `column_stats(path, columns=None)` | Compute per-column stats: min, max, unique, nulls, count. |
| `detect_dialect(filepath_or_sample)` | Detect CSV delimiter, quotechar, and formatting from a file or text sample. Returns `DialectResult`. |
| `column_quality(rows, column)` | Score column data quality: completeness %, cardinality ratio, null count. Returns `QualityResult`. |
| `CsvPipeline(rows)` | Chainable pipeline with `.filter()`, `.exclude()`, `.map_column()`, `.add_column()`, `.rename_column()`, `.select_columns()`, `.sort_by()`, `.group_by()`, `.aggregate()`, `.head()`, `.tail()`, `.sample()`, `.deduplicate()`, `.distinct()`, `.to_list()`, `.to_json()`, `.to_dict_list()`, `.count()`, `.first()`. |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## Support

If you find this project useful:

⭐ [Star the repo](https://github.com/philiprehberger/py-csv-kit)

🐛 [Report issues](https://github.com/philiprehberger/py-csv-kit/issues?q=is%3Aissue+is%3Aopen+label%3Abug)

💡 [Suggest features](https://github.com/philiprehberger/py-csv-kit/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)

❤️ [Sponsor development](https://github.com/sponsors/philiprehberger)

🌐 [All Open Source Projects](https://philiprehberger.com/open-source-packages)

💻 [GitHub Profile](https://github.com/philiprehberger)

🔗 [LinkedIn Profile](https://www.linkedin.com/in/philiprehberger)

## License

[MIT](LICENSE)
