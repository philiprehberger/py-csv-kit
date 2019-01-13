"""Enhanced CSV reader and writer with automatic type inference."""

from __future__ import annotations

import csv
from pathlib import Path

__all__ = ["read_csv", "write_csv", "infer_types"]


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
