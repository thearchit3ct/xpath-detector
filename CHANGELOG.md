# Changelog

All notable changes to xpath-detector are documented here.

## [1.2.2] - 2026-05-12

### Fixed
- **Critical**: Java/Python/Robot exporters generated duplicate constant names when
  multiple captured elements shared the same description. The generated Java code
  was uncompilable (duplicate `public static final By X` declarations). Exporters
  now append `_2`, `_3`, ... to make names unique within a screen.
- Auto-description picked wrong label for buttons/links. `findNearbyLabel` JS walks
  up DOM ancestors and may return the first preceding span, which for a button at
  the bottom of a form is not its real label. Auto-description now prefers the
  element's own `text` for buttons/links/etc., reserving `nearby_label` priority for
  form inputs (input/select/textarea) where the visible label is the field name.

### Added
- `dedup_name(name, seen)` helper in `exporters/_naming.py` (shared between
  Java/Python/Robot exporters).
- Regression tests for duplicate constant names across all 3 code-generating exporters.

## [1.2.1] - 2026-05-12

### Fixed
- **Critical**: capture deadlock in interactive shell. `_on_capture` (called from
  poll thread) was calling `console.input()` for the description prompt while the
  main `run()` loop was also blocked on `console.input()` for the next command.
  The two threads competed for stdin, leaving captures silently dropped or the
  shell unresponsive.

### Changed
- `_on_capture` no longer prompts for description. Auto-generates one from
  captured data (priority: `nearby_label` > `text` > `id` > `name` >
  `aria-label` > tag fallback).

### Added
- New shell command `describe <index> <new description>` to rename a previously
  captured element after the fact.

## [1.2.0] - 2026-05-12

### Added
- Selenium browser backend as default (corporate-friendly, uses system Chrome, no binary download)
- `XPATH_DETECTOR_BACKEND` environment variable to switch between `selenium` (default) and `playwright`
- Factory function `create_backend()` and abstract `BrowserBackend` interface in `xpath_detector.browser`
- Background thread-based polling of `window.__xpath_capture_queue` (uniform between backends)

### Changed
- Browser communication replaced `console.log("__XPATH_CAPTURE__...")` with `window.__xpath_capture_queue` push + polling
- Playwright moved to optional extra: `pip install xpath-detector[playwright]`
- Old `browser.py` module reorganized into `browser/` package with separate `selenium_backend.py` and `playwright_backend.py`

### Migration

No session format changes. Sessions from v1.0 and v1.1 remain readable.

For users who installed v1.1 with Playwright:
- v1.2 default works with Selenium (no Playwright required)
- To keep using Playwright: install with `[playwright]` extra and set `XPATH_DETECTOR_BACKEND=playwright`

Legacy import `from xpath_detector.browser import BrowserController` continues to work (returns a backend instance via the default selection).

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
