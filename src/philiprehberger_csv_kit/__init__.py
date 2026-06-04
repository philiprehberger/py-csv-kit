"""Enhanced CSV reader and writer with automatic type inference."""

from __future__ import annotations

import csv
import json
import random
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "read_csv",
    "write_csv",
    "infer_types",
    "stream_csv",
    "stream_csv_rows",
    "column_stats",
    "detect_dialect",
    "column_quality",
    "to_json",
    "to_dict_list",
    "head",
    "sample",
    "deduplicate",
    "find_duplicates",
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


def _apply_type_override(value: str, target_type: type) -> Any:
    """Cast a string value to a specific target type."""
    if value == "" or value is None:
        return None
    if target_type is int:
        return int(float(value))
    if target_type is float:
        return float(value)
    if target_type is bool:
        return value.lower() in ("true", "1", "yes")
    if target_type is str:
        return value
    return target_type(value)


def infer_types(
    rows: list[dict[str, str]],
    overrides: dict[str, type] | None = None,
) -> list[dict[str, int | float | bool | None | str]]:
    """Take a list of string-value dicts and return with values cast to
    int, float, bool, or None where possible.

    Inference order: int -> float -> bool -> None -> str.

    Args:
        rows: List of row dicts with string values.
        overrides: Optional mapping of column names to types. When a
            column appears in *overrides*, its value is cast to the
            given type instead of using automatic inference.

    Returns:
        List of row dicts with inferred (or overridden) types.
    """
    overrides = overrides or {}
    result: list[dict[str, int | float | bool | None | str]] = []
    for row in rows:
        new_row: dict[str, int | float | bool | None | str] = {}
        for key, val in row.items():
            if key in overrides:
                new_row[key] = _apply_type_override(val, overrides[key])
            else:
                new_row[key] = _infer_value(val)
        result.append(new_row)
    return result


# ---------------------------------------------------------------------------
# Read / Write / Stream
# ---------------------------------------------------------------------------


def read_csv(
    path: str | Path,
    typed: bool = True,
    encoding: str = "utf-8",
    overrides: dict[str, type] | None = None,
) -> list[dict[str, str]] | list[dict[str, int | float | bool | None | str]]:
    """Read a CSV file and return a list of dicts.

    Args:
        path: Path to the CSV file.
        typed: If True, automatically infer value types.
        encoding: File encoding.
        overrides: Optional mapping of column names to types. Forces
            specific columns to the given type instead of inferring.

    Returns:
        List of row dicts keyed by column headers.
    """
    with open(path, newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, str]] = list(reader)

    if typed:
        return infer_types(rows, overrides=overrides)
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


def stream_csv_rows(
    path: str | Path,
    typed: bool = True,
    encoding: str = "utf-8",
) -> Iterator[dict[str, Any]]:
    """Yield individual rows from a CSV file without loading the entire file.

    This is a true streaming mode that yields one row at a time, making it
    suitable for processing very large files with minimal memory usage.

    Args:
        path: Path to the CSV file.
        typed: If True, automatically infer value types per row.
        encoding: File encoding.

    Yields:
        Individual row dicts keyed by column headers.
    """
    with open(path, newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if typed:
                yield {key: _infer_value(val) for key, val in row.items()}
            else:
                yield row


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------


def to_json(
    rows: list[dict[str, Any]],
    *,
    indent: int | None = 2,
    ensure_ascii: bool = False,
) -> str:
    """Serialize a list of row dicts to a JSON string.

    Args:
        rows: List of row dicts.
        indent: JSON indentation level. ``None`` for compact output.
        ensure_ascii: If ``False``, allow non-ASCII characters.

    Returns:
        A JSON-encoded string.
    """
    return json.dumps(rows, indent=indent, ensure_ascii=ensure_ascii, default=str)


def to_dict_list(
    rows: list[dict[str, Any]],
    columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return a filtered copy of rows as a list of plain dicts.

    This is useful for selecting specific columns or obtaining a
    clean copy of the data for further processing.

    Args:
        rows: List of row dicts.
        columns: Column names to include. If ``None``, all columns
            are returned.

    Returns:
        A new list of dicts containing only the requested columns.
    """
    if columns is None:
        return [dict(row) for row in rows]
    return [{col: row.get(col) for col in columns} for row in rows]


# ---------------------------------------------------------------------------
# Quick inspection helpers
# ---------------------------------------------------------------------------


def head(
    path: str | Path,
    n: int = 5,
    typed: bool = True,
    encoding: str = "utf-8",
) -> list[dict[str, Any]]:
    """Return the first *n* rows from a CSV file.

    Reads only the needed rows without loading the entire file.

    Args:
        path: Path to the CSV file.
        n: Number of rows to return.
        typed: If True, automatically infer value types.
        encoding: File encoding.

    Returns:
        List of up to *n* row dicts.
    """
    result: list[dict[str, Any]] = []
    with open(path, newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= n:
                break
            if typed:
                result.append({key: _infer_value(val) for key, val in row.items()})
            else:
                result.append(dict(row))
    return result


def sample(
    path: str | Path,
    n: int = 5,
    typed: bool = True,
    encoding: str = "utf-8",
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Return a random sample of *n* rows from a CSV file.

    Loads the full file to perform the sampling. For very large files,
    consider using :func:`stream_csv_rows` with custom logic instead.

    Args:
        path: Path to the CSV file.
        n: Number of rows to sample.
        typed: If True, automatically infer value types.
        encoding: File encoding.
        seed: Optional random seed for reproducible results.

    Returns:
        List of up to *n* randomly selected row dicts.
    """
    rows = read_csv(path, typed=typed, encoding=encoding)
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()
    k = min(n, len(rows))
    return rng.sample(rows, k)


# ---------------------------------------------------------------------------
# Duplicate detection and removal
# ---------------------------------------------------------------------------


def _row_key(
    row: dict[str, Any],
    columns: list[str] | None = None,
) -> tuple[Any, ...]:
    """Create a hashable key from a row dict for duplicate detection."""
    if columns is not None:
        return tuple(row.get(col) for col in columns)
    return tuple(sorted(row.items()))


def find_duplicates(
    rows: list[dict[str, Any]],
    columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Find duplicate rows in a list of dicts.

    Two rows are considered duplicates if they share the same values for
    the specified *columns*. If *columns* is ``None``, all columns are
    compared.

    Args:
        rows: List of row dicts.
        columns: Column names to compare. If ``None``, all columns
            are compared.

    Returns:
        List of rows that are duplicates (second and subsequent
        occurrences).
    """
    seen: set[tuple[Any, ...]] = set()
    duplicates: list[dict[str, Any]] = []
    for row in rows:
        key = _row_key(row, columns)
        if key in seen:
            duplicates.append(row)
        else:
            seen.add(key)
    return duplicates


def deduplicate(
    rows: list[dict[str, Any]],
    columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Remove duplicate rows, keeping the first occurrence.

    Two rows are considered duplicates if they share the same values for
    the specified *columns*. If *columns* is ``None``, all columns are
    compared.

    Args:
        rows: List of row dicts.
        columns: Column names to compare. If ``None``, all columns
            are compared.

    Returns:
        List of unique rows (first occurrence kept).
    """
    seen: set[tuple[Any, ...]] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        key = _row_key(row, columns)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


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

    # -- Aggregation --------------------------------------------------------

    def aggregate(
        self,
        group_key: str,
        **agg_fns: Callable[[list[Row]], Any],
    ) -> list[Row]:
        """Group rows by *group_key* and compute aggregate values per group.

        Each keyword argument is an aggregation: the parameter name becomes
        the result column, and the callable receives the list of rows in that
        group and returns a scalar.

        This is a terminal operation that returns a list of dicts, one per
        distinct group value. The group key is included in each result row.

        Args:
            group_key: Column name to group by.
            **agg_fns: Mapping of result-column name to a function that
                takes a ``list[Row]`` and returns the aggregate value.

        Returns:
            A list of result dicts, one per group.

        Example::

            CsvPipeline(rows).aggregate(
                "city",
                count=len,
                avg_age=lambda rs: sum(r["age"] for r in rs) / len(rs),
            )
            # [{"city": "NYC", "count": 4, "avg_age": 32.5}, ...]
        """
        groups = self.group_by(group_key)
        results: list[Row] = []
        for value, rows in groups.items():
            result_row: Row = {group_key: value}
            for col, fn in agg_fns.items():
                result_row[col] = fn(rows)
            results.append(result_row)
        return results

    # -- Limiting -----------------------------------------------------------

    def head(self, n: int) -> CsvPipeline:
        """Keep only the first *n* rows."""
        return CsvPipeline(self._rows[:n])

    def tail(self, n: int) -> CsvPipeline:
        """Keep only the last *n* rows."""
        return CsvPipeline(self._rows[-n:] if n > 0 else [])

    # -- Sampling -----------------------------------------------------------

    def sample(self, n: int, *, seed: int | None = None) -> CsvPipeline:
        """Return a random sample of *n* rows.

        Args:
            n: Number of rows to sample.
            seed: Optional random seed for reproducible results.
        """
        rng = random.Random(seed) if seed is not None else random.Random()
        k = min(n, len(self._rows))
        return CsvPipeline(rng.sample(self._rows, k))

    # -- Deduplication ------------------------------------------------------

    def deduplicate(self, columns: list[str] | None = None) -> CsvPipeline:
        """Remove duplicate rows, keeping the first occurrence.

        Args:
            columns: Column names to compare. If ``None``, all columns
                are compared.
        """
        return CsvPipeline(deduplicate(self._rows, columns=columns))

    # -- Distinct values ----------------------------------------------------

    def distinct(self, column: str) -> list[Any]:
        """Return unique values in *column*, preserving first-seen order.

        Terminal operation. ``None`` is included if it appears. Useful for
        quickly enumerating the categories present in a column without
        sprinkling ``set()`` and re-sorting throughout calling code.

        Args:
            column: The column name to extract.

        Returns:
            A list of unique values in the order they were first seen.
        """
        seen: set[Any] = set()
        result: list[Any] = []
        for row in self._rows:
            value = row.get(column)
            try:
                if value in seen:
                    continue
                seen.add(value)
            except TypeError:
                # Unhashable value: keep it but fall back to a linear scan.
                if value in result:
                    continue
            result.append(value)
        return result

    # -- Terminal operations ------------------------------------------------

    def to_list(self) -> list[Row]:
        """Return the current rows as a plain list of dicts."""
        return list(self._rows)

    def to_json(self, *, indent: int | None = 2, ensure_ascii: bool = False) -> str:
        """Serialize the current rows to a JSON string.

        Args:
            indent: JSON indentation level. ``None`` for compact output.
            ensure_ascii: If ``False``, allow non-ASCII characters.

        Returns:
            A JSON-encoded string.
        """
        return to_json(self._rows, indent=indent, ensure_ascii=ensure_ascii)

    def to_dict_list(self, columns: list[str] | None = None) -> list[Row]:
        """Return the current rows as a list of plain dicts.

        Args:
            columns: Column names to include. If ``None``, all columns
                are returned.

        Returns:
            A new list of dicts.
        """
        return to_dict_list(self._rows, columns=columns)

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
