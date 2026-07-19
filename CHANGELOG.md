# Changelog

All notable changes to the Simplex specification will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-07-19

### Added
- Optional `SIMPLEX: 0.6` language-version declaration
- Document-wide stable item identifiers
- `COVERS` landmark for author-declared example-to-contract traceability
- Optional `value`, `error`, `outcome`, and `property` example kinds
- Deterministic language-version and traceability diagnostics and statistics
- Empty-landmark, duplicate-landmark, malformed-signature, and duplicate-function checks
- CHANGELOG.md following Keep a Changelog format
- Makefile for build automation

### Changed
- Updated the landmark count from 16 to 18
- Updated bundled examples to demonstrate complete declared traceability
- JSON and text lint results now report supported/declared specification versions and traceability statistics

### Fixed
- Empty landmarks no longer consume the following landmark during tolerant parsing
- Duplicate function-level landmarks are retained for diagnostics instead of silently overwriting earlier content
- `EVAL` thresholds now reject `pass^0` and `pass@0`; `k` must be positive
- Coverage gates no longer depend on an unavailable `bc` executable
- Text output no longer labels an identifier-only inventory as incomplete declared coverage

## [0.5.0] - 2026-01-28

### Added
- DETERMINISM landmark for output variance control (strict/structural/semantic levels)
- Linter support for DETERMINISM validation (E070)
- Variance control landmarks section in specification

### Changed
- Consolidated pillars from six to five: merged "Specification, not implementation" and "Implementation opacity" into "Implementation autonomy"
- Updated landmark count from 15 to 16
- Terminology: "tolerates" → "allows" for syntactic tolerance pillar

### Fixed
- Evolution checker threshold validation regex
