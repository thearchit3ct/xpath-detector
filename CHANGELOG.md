# Changelog

All notable changes to xpath-detector are documented here.

## [1.1.0] - 2026-05-12

### Fixed
- Overlay hover/click target mismatch on nested elements (I-1): click handler now uses `document.elementFromPoint` for consistency with hover highlight
- Shell coverage from 26% to 48% with new unit tests for capture pipeline and export dispatch (I-4)

### Added
- `help` command in interactive shell lists all available commands and shortcuts (I-3)
- `by_label_neighbor` strategy in analyzer (score 50) for inputs identified by their nearby label text (I-5a)
- Overlay JS detects the nearest label via `label[for=]`, ancestor `<label>`, or preceding sibling `<span>`/`<label>` within 3 ancestor levels
- `scripts/migrate_v1.py` script to convert v1.0 session JSON to v1.1 format (I-5b)
- Console logging handler (WARNING+) on stderr in addition to file handler (M-9)
- Edge-case tests for `escape_xpath_literal`: empty string, lone apostrophe, wrapped, consecutive (M-11)

### Changed
- Naming helpers (`sanitize`, `to_pascal`, `to_constant`, `to_var_name`) extracted from java/python/robot exporters to `exporters/_naming.py` (M-4 DRY)

## [1.0.0] - 2026-05-12

Initial release. Complete rewrite of xpath_detector with Playwright sync, plugin-based exporters (JSON/HTML/Robot/Java/Python), interactive shell with rich UI, JS overlay for Ctrl+click capture.
