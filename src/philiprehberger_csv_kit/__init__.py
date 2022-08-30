"""Enhanced CSV reader and writer with automatic type inference."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "read_csv",
    "write_csv",
    "infer_types",
    "stream_csv",
    "column_stats",
    "detect_dialect",
    "column_quality",
    "CsvPipeline",
    "DialectResult",
    "QualityResult",
]

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Row = dict[str, Any]
Predicate = Callable[[Row], bool]
MapFn = Callable[[Any], Any]


# ---------------------------------------------------------------------------
# Value inference
# ---------------------------------------------------------------------------


def _infer_value(value: str) -> int | float | bool | None | str:
    """Try to cast a string value to int, float, bool, or None."""
    if value == "" or value is None:
        return None

    try:
        return int(value)
    except (ValueError, TypeError):
        pass

    try:
        return float(value)
    except (ValueError, TypeError):
        pass

    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False

    return value


def infer_types(rows: list[dict[str, str]]) -> list[dict[str, int | float | bool | None | str]]:
    """Take a list of string-value dicts and return with values cast to
    int, float, bool, or None where possible.

    Inference order: int -> float -> bool -> None -> str.
    """
    return [
        {key: _infer_value(val) for key, val in row.items()}
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Read / Write / Stream
# ---------------------------------------------------------------------------


def read_csv(
    path: str | Path,
    typed: bool = True,
    encoding: str = "utf-8",
) -> list[dict[str, str]] | list[dict[str, int | float | bool | None | str]]:
    """Read a CSV file and return a list of dicts.

    Args:
        path: Path to the CSV file.
        typed: If True, automatically infer value types.
        encoding: File encoding.

    Returns:
        List of row dicts keyed by column headers.
    """
    with open(path, newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, str]] = list(reader)

    if typed:
        return infer_types(rows)
    return rows


def write_csv(
    path: str | Path,
    rows: list[dict[str, object]],
    columns: list[str] | None = None,
    encoding: str = "utf-8",
) -> None:
    """Write a list of dicts to a CSV file.

    Args:
        path: Destination file path.
        rows: List of row dicts to write.
        columns: Column names to include (and their order).
            If None, uses all keys from the first row.
        encoding: File encoding.
    """
    if not rows:
        with open(path, "w", newline="", encoding=encoding) as f:
            f.write("")
        return

    fieldnames = columns if columns is not None else list(rows[0].keys())

    with open(path, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def stream_csv(
    path: str | Path,
    chunk_size: int = 1000,
    encoding: str = "utf-8",
) -> Iterator[list[dict[str, str]]]:
    """Read a CSV file in chunks, yielding lists of row dicts.

    This is a generator that reads the file lazily, making it suitable for
    large files that do not fit in memory.

    Args:
        path: Path to the CSV file.
        chunk_size: Number of rows per chunk.
        encoding: File encoding.

    Yields:
        Lists of row dicts, each list containing up to *chunk_size* rows.
    """
    with open(path, newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        chunk: list[dict[str, str]] = []
        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk


# ---------------------------------------------------------------------------
# Column statistics
# ---------------------------------------------------------------------------


def column_stats(
    path: str | Path,
    columns: list[str] | None = None,
) -> dict[str, dict[str, object]]:
    """Compute per-column statistics for a CSV file.

    For each column, returns ``min``, ``max``, ``unique`` count,
    ``nulls`` count, and total ``count``.  Uses type inference for
    min/max comparison so numeric columns compare numerically.

    Args:
        path: Path to the CSV file.
        columns: Column names to analyse.  If ``None``, all columns are
            included.

    Returns:
        Dict mapping column names to their statistics dicts.
    """
    rows = read_csv(path, typed=True)
    if not rows:
        return {}

    target_cols = columns if columns is not None else list(rows[0].keys())

    stats: dict[str, dict[str, object]] = {}
    for col in target_cols:
        values = [row.get(col) for row in rows]
        non_null = [v for v in values if v is not None]
        nulls = len(values) - len(non_null)
        unique = len(set(non_null))

        col_min: object = None
        col_max: object = None
        if non_null:
            try:
                col_min = min(non_null)  # type: ignore[type-var]
                col_max = max(non_null)  # type: ignore[type-var]
            except TypeError:
                str_vals = [str(v) for v in non_null]
                col_min = min(str_vals)
                col_max = max(str_vals)

        stats[col] = {
            "min": col_min,
            "max": col_max,
            "unique": unique,
            "nulls": nulls,
            "count": len(values),
        }

    return stats


# ---------------------------------------------------------------------------
# Dialect detection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DialectResult:
    """Result of CSV dialect detection."""

    delimiter: str
    quotechar: str | None
    doublequote: bool
    skipinitialspace: bool
    lineterminator: str

    def to_dict(self) -> dict[str, str | bool | None]:
        """Return the dialect as a plain dictionary."""
        return {
            "delimiter": self.delimiter,
            "quotechar": self.quotechar,
            "doublequote": self.doublequote,
            "skipinitialspace": self.skipinitialspace,
            "lineterminator": self.lineterminator,
        }


def detect_dialect(filepath_or_sample: str | Path) -> DialectResult:
    """Detect the CSV dialect from a file path or a raw text sample.

    Uses :func:`csv.Sniffer` to detect the delimiter, quotechar, and
    other formatting properties.

    Args:
        filepath_or_sample: Either a file path (``str`` or ``Path``)
            pointing to a CSV file, or a raw CSV text sample (``str``).

    Returns:
        A :class:`DialectResult` with the detected properties.

    Raises:
        csv.Error: If the sniffer cannot determine the dialect.
    """
    sample: str
    path = Path(filepath_or_sample) if not isinstance(filepath_or_sample, Path) else filepath_or_sample

    # Heuristic: if the string looks like a file path that exists, read it
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            sample = f.read(8192)
    else:
        if not isinstance(filepath_or_sample, str):
            raise FileNotFoundError(f"File not found: {filepath_or_sample}")
        sample = filepath_or_sample

    sniffer = csv.Sniffer()
    dialect = sniffer.sniff(sample)

    return DialectResult(
        delimiter=dialect.delimiter,
        quotechar=dialect.quotechar,
        doublequote=dialect.doublequote,
        skipinitialspace=dialect.skipinitialspace,
        lineterminator=dialect.lineterminator,
    )


# ---------------------------------------------------------------------------
# Column data quality scoring
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QualityResult:
    """Data quality metrics for a single column."""

    completeness: float
    """Percentage of non-null values (0.0 -- 100.0)."""

    cardinality_ratio: float
    """Ratio of unique non-null values to total rows (0.0 -- 1.0)."""

    null_count: int
    """Number of null / empty values."""

    total_count: int
    """Total number of rows examined."""

    def to_dict(self) -> dict[str, float | int]:
        """Return the quality metrics as a plain dictionary."""
        return {
            "completeness": self.completeness,
            "cardinality_ratio": self.cardinality_ratio,
            "null_count": self.null_count,
            "total_count": self.total_count,
        }


def column_quality(
    rows: list[dict[str, Any]],
    column: str,
) -> QualityResult:
    """Score the data quality of a single column.

    Args:
        rows: List of row dicts (may be raw strings or type-inferred).
        column: The column name to evaluate.

    Returns:
        A :class:`QualityResult` with completeness percentage,
        cardinality ratio, null count, and total count.

    Raises:
        KeyError: If *column* is not present in any row.
    """
    if not rows:
        return QualityResult(
            completeness=0.0,
            cardinality_ratio=0.0,
            null_count=0,
            total_count=0,
        )

    # Validate column exists in at least one row
    if not any(column in row for row in rows):
        raise KeyError(f"Column '{column}' not found in any row")

    total = len(rows)
    values = [row.get(column) for row in rows]

    null_count = sum(
        1 for v in values if v is None or (isinstance(v, str) and v.strip() == "")
    )
    non_null_count = total - null_count
    non_null_values = [
        v for v in values if v is not None and not (isinstance(v, str) and v.strip() == "")
    ]

    completeness = (non_null_count / total) * 100.0 if total > 0 else 0.0
    cardinality_ratio = len(set(non_null_values)) / total if total > 0 else 0.0

    return QualityResult(
        completeness=round(completeness, 2),
        cardinality_ratio=round(cardinality_ratio, 4),
        null_count=null_count,
        total_count=total,
    )


# ---------------------------------------------------------------------------
# Chainable transformation pipeline
# ---------------------------------------------------------------------------


class CsvPipeline:
    """Chainable transformation pipeline for CSV row data.

    Provides a fluent API for filtering, mapping, sorting, and
    grouping rows in an ETL-like workflow.

    Example::

        result = (
            CsvPipeline(rows)
            .filter(lambda r: r["age"] > 18)
            .map_column("name", str.upper)
            .sort_by("age")
            .to_list()
        )
    """

    __slots__ = ("_rows",)

    def __init__(self, rows: list[Row]) -> None:
        self._rows: list[Row] = list(rows)

    # -- Filtering ----------------------------------------------------------

    def filter(self, predicate: Predicate) -> CsvPipeline:
        """Keep only rows for which *predicate* returns ``True``."""
        return CsvPipeline([row for row in self._rows if predicate(row)])

    def exclude(self, predicate: Predicate) -> CsvPipeline:
        """Remove rows for which *predicate* returns ``True``."""
        return CsvPipeline([row for row in self._rows if not predicate(row)])

    # -- Mapping ------------------------------------------------------------

    def map_column(self, name: str, fn: MapFn) -> CsvPipeline:
        """Apply *fn* to the value of *name* in every row.

        Rows that do not contain *name* are passed through unchanged.
        """
        new_rows: list[Row] = []
        for row in self._rows:
            new_row = dict(row)
            if name in new_row:
                new_row[name] = fn(new_row[name])
            new_rows.append(new_row)
        return CsvPipeline(new_rows)

    def add_column(self, name: str, fn: Callable[[Row], Any]) -> CsvPipeline:
        """Add a computed column *name* whose value is ``fn(row)``."""
        new_rows: list[Row] = []
        for row in self._rows:
            new_row = dict(row)
            new_row[name] = fn(row)
            new_rows.append(new_row)
        return CsvPipeline(new_rows)

    def rename_column(self, old: str, new: str) -> CsvPipeline:
        """Rename column *old* to *new* in every row."""
        new_rows: list[Row] = []
        for row in self._rows:
            new_row = {(new if k == old else k): v for k, v in row.items()}
            new_rows.append(new_row)
        return CsvPipeline(new_rows)

    def select_columns(self, columns: list[str]) -> CsvPipeline:
        """Keep only the specified columns, in order."""
        return CsvPipeline([
            {k: row.get(k) for k in columns} for row in self._rows
        ])

    # -- Sorting ------------------------------------------------------------

    def sort_by(self, key: str, *, reverse: bool = False) -> CsvPipeline:
        """Sort rows by column *key*."""
        return CsvPipeline(
            sorted(self._rows, key=lambda r: r.get(key, ""), reverse=reverse)  # type: ignore[return-value]
        )

    # -- Grouping -----------------------------------------------------------

    def group_by(self, key: str) -> dict[Any, list[Row]]:
        """Group rows by the value of *key* and return a dict.

        This is a terminal operation that returns a plain dict
        mapping each distinct value to the list of rows sharing it.
        """
        groups: dict[Any, list[Row]] = {}
        for row in self._rows:
            k = row.get(key)
            groups.setdefault(k, []).append(row)
        return groups

    # -- Limiting -----------------------------------------------------------

    def head(self, n: int) -> CsvPipeline:
        """Keep only the first *n* rows."""
        return CsvPipeline(self._rows[:n])

    def tail(self, n: int) -> CsvPipeline:
        """Keep only the last *n* rows."""
        return CsvPipeline(self._rows[-n:] if n > 0 else [])

    # -- Terminal operations ------------------------------------------------

    def to_list(self) -> list[Row]:
        """Return the current rows as a plain list of dicts."""
        return list(self._rows)

    def count(self) -> int:
        """Return the number of rows."""
        return len(self._rows)

    def first(self) -> Row | None:
        """Return the first row, or ``None`` if empty."""
        return self._rows[0] if self._rows else None

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self) -> Iterator[Row]:
        return iter(self._rows)
