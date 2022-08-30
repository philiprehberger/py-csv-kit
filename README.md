# philiprehberger-csv-kit

[![Tests](https://github.com/philiprehberger/py-csv-kit/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-csv-kit/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-csv-kit.svg)](https://pypi.org/project/philiprehberger-csv-kit/)
[![GitHub release](https://img.shields.io/github/v/release/philiprehberger/py-csv-kit)](https://github.com/philiprehberger/py-csv-kit/releases)
[![Last updated](https://img.shields.io/github/last-commit/philiprehberger/py-csv-kit)](https://github.com/philiprehberger/py-csv-kit/commits/main)
[![License](https://img.shields.io/github/license/philiprehberger/py-csv-kit)](LICENSE)
[![Bug Reports](https://img.shields.io/github/issues/philiprehberger/py-csv-kit/bug)](https://github.com/philiprehberger/py-csv-kit/issues?q=is%3Aissue+is%3Aopen+label%3Abug)
[![Feature Requests](https://img.shields.io/github/issues/philiprehberger/py-csv-kit/enhancement)](https://github.com/philiprehberger/py-csv-kit/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub%20Sponsors-ec6cb9)](https://github.com/sponsors/philiprehberger)

Enhanced CSV reader and writer with automatic type inference.

## Installation

```bash
pip install philiprehberger-csv-kit
```

## Usage

### Reading CSV

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
from philiprehberger_csv_kit import stream_csv

for chunk in stream_csv("large.csv", chunk_size=500):
    for row in chunk:
        process(row)
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
    .sort_by("age")
    .to_list()
)

# Group by department
groups = (
    CsvPipeline(rows)
    .filter(lambda r: r["active"] is True)
    .group_by("department")
)
# {"Engineering": [...], "Sales": [...]}
```

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
| `read_csv(path, typed=True, encoding="utf-8")` | Read CSV file, return list of dicts. Infers types when `typed=True`. |
| `write_csv(path, rows, columns=None, encoding="utf-8")` | Write list of dicts to CSV. Optional column filter. |
| `stream_csv(path, chunk_size=1000, encoding="utf-8")` | Generator yielding chunks of row dicts for memory-efficient reading. |
| `column_stats(path, columns=None)` | Compute per-column stats: min, max, unique, nulls, count. |
| `infer_types(rows)` | Cast string values to int, float, bool, or None where possible. |
| `detect_dialect(filepath_or_sample)` | Detect CSV delimiter, quotechar, and formatting from a file or text sample. Returns `DialectResult`. |
| `column_quality(rows, column)` | Score column data quality: completeness %, cardinality ratio, null count. Returns `QualityResult`. |
| `CsvPipeline(rows)` | Chainable pipeline with `.filter()`, `.map_column()`, `.add_column()`, `.rename_column()`, `.select_columns()`, `.sort_by()`, `.group_by()`, `.head()`, `.tail()`, `.to_list()`, `.count()`, `.first()`. |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## Support

If you find this package useful, consider starring the repository.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Philip%20Rehberger-blue?logo=linkedin)](https://www.linkedin.com/in/philiprehberger/)
[![More Packages](https://img.shields.io/badge/More%20Packages-philiprehberger-orange)](https://github.com/philiprehberger?tab=repositories)

## License

[MIT](LICENSE)
