# Changelog

All notable changes to the Simplex specification will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [Unreleased]

### Added
- CHANGELOG.md following Keep a Changelog format
- Makefile for build automation
