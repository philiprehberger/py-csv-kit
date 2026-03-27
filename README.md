# philiprehberger-csv-kit

[![Tests](https://github.com/philiprehberger/py-csv-kit/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-csv-kit/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-csv-kit.svg)](https://pypi.org/project/philiprehberger-csv-kit/)
[![License](https://img.shields.io/github/license/philiprehberger/py-csv-kit)](LICENSE)
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

### Type Inference

```python
from philiprehberger_csv_kit import infer_types

raw = [{"val": "42"}, {"val": "3.14"}, {"val": "true"}, {"val": ""}]
typed = infer_types(raw)
# [{"val": 42}, {"val": 3.14}, {"val": True}, {"val": None}]
```

## API

| Function | Description |
|---|---|
| `read_csv(path, typed=True, encoding="utf-8")` | Read CSV file, return list of dicts. Infers types when `typed=True`. |
| `write_csv(path, rows, columns=None, encoding="utf-8")` | Write list of dicts to CSV. Optional column filter. |
| `infer_types(rows)` | Cast string values to int, float, bool, or None where possible. |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## License

MIT
