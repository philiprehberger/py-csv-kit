"""Enhanced CSV reader and writer with automatic type inference."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

__all__ = ["read_csv", "write_csv", "infer_types", "stream_csv", "column_stats"]


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
