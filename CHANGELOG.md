# Changelog

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
