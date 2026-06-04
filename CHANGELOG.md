# Changelog

## 0.6.0 (2026-06-04)

- Add `CsvPipeline.distinct(column)` terminal op returning unique column values in first-seen order — handy for quickly enumerating categories without `set()` gymnastics
- Add `package-card.webp` to README

## 0.5.0 (2026-04-28)

- Add `CsvPipeline.aggregate(group_key, **agg_fns)` for grouped aggregations — each keyword arg is a result column whose value is computed from the list of rows in the group

## 0.4.0 (2026-04-01)

- Add `stream_csv_rows()` for true row-by-row streaming without loading the entire file
- Add `to_json()` and `to_dict_list()` convenience export methods
- Add column type override via `overrides` parameter on `infer_types()` and `read_csv()`
- Add `head(path, n)` and `sample(path, n)` functions for quick data inspection
- Add `find_duplicates()` and `deduplicate()` for duplicate row detection and removal
- Add `CsvPipeline.to_json()`, `.to_dict_list()`, `.sample()`, and `.deduplicate()` methods

## 0.3.1 (2026-03-31)

- Standardize README to 3-badge format with emoji Support section
- Update CI checkout action to v5 for Node.js 24 compatibility

## 0.3.0 (2026-03-28)

- Add `detect_dialect()` for automatic delimiter and dialect detection via `csv.Sniffer`
- Add `column_quality()` for data quality scoring (completeness %, cardinality ratio, null count)
- Add `CsvPipeline` chainable transformation pipeline with `filter`, `map_column`, `group_by`, `sort_by`, and more
- Add `DialectResult` and `QualityResult` dataclasses for structured return values

## 0.2.0 (2026-03-27)

- Add `stream_csv()` generator for memory-efficient chunked reading of large files
- Add `column_stats()` for per-column statistics (min, max, unique, nulls, count)
- Add `.github/` issue templates, PR template, and Dependabot config
- Update README with full badge set and all standard sections

## 0.1.1 (2026-03-22)

- Rename Install section to Installation in README
- Add Changelog URL to project URLs
- Add `#readme` anchor to Homepage URL
- Add pytest and mypy configuration

## 0.1.0 (2026-03-21)

- Initial release
- `read_csv` with automatic type inference
- `write_csv` with optional column filtering
- `infer_types` for standalone type casting (int, float, bool, None)
