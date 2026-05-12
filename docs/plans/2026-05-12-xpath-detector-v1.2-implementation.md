# xpath-detector v1.2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor `browser.py` en package pluggable avec Selenium par defaut (corporate-friendly) et Playwright optionnel.

**Architecture:** `src/xpath_detector/browser/` devient un package avec `BrowserBackend` ABC, deux implementations (selenium + playwright), et une factory `create_backend()` controlee par env var `XPATH_DETECTOR_BACKEND`. L'overlay JS communique via une queue `window.__xpath_capture_queue` pollee en background thread (uniforme entre backends, plus de dependance au `console.log` event handler).

**Tech Stack:** Selenium 4 (core), Playwright (optionnel via extra), pytest, threading pour le polling.

**Conventions:** TDD strict, pas d'attribution AI, commits atomiques. Baseline : v1.1.0 = commit `daeec49`, 62 tests passing.

---

## Phase 1 — Infrastructure (ABC + factory)

### Task 1 : Browser ABC + package skeleton

**Files:**
- Create: `src/xpath_detector/browser/__init__.py`
- Create: `src/xpath_detector/browser/base.py`
- Create: `tests/test_browser_base.py`
- Delete (later): `src/xpath_detector/browser.py` (l'ancien fichier)

**Step 1 : Test ABC**

Create `tests/test_browser_base.py`:

```python
import pytest

from xpath_detector.browser.base import BrowserBackend


def test_browser_backend_is_abstract():
    with pytest.raises(TypeError):
        BrowserBackend()
```

**Step 2 : Run (FAIL)**

```bash
cd /Users/nitch/projects/git_projets/xpath_detector
source .venv/bin/activate
pytest tests/test_browser_base.py -v
```

Expected: ImportError on `xpath_detector.browser.base`.

**Step 3 : Move browser.py -> browser/playwright_backend.py temporarily**

```bash
mkdir -p src/xpath_detector/browser
git mv src/xpath_detector/browser.py src/xpath_detector/browser/playwright_backend.py
```

**Step 4 : Create base.py**

`src/xpath_detector/browser/base.py`:

```python
"""Abstract browser backend interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class BrowserBackend(ABC):
    """Interface pour les backends de navigateur (Selenium, Playwright, ...)."""

    @abstractmethod
    def start(self) -> None:
        """Lance le navigateur et initialise le polling."""

    @abstractmethod
    def open(self, url: str) -> None:
        """Navigue vers une URL, injecte l'overlay."""

    @abstractmethod
    def reinject_overlay(self) -> None:
        """Re-injecte l'overlay (apres navigation interne)."""

    @abstractmethod
    def on_capture(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Enregistre un callback pour les captures."""

    @abstractmethod
    def current_url(self) -> str:
        """URL courante du navigateur."""

    @abstractmethod
    def current_title(self) -> str:
        """Titre courant du navigateur."""

    @abstractmethod
    def stop(self) -> None:
        """Ferme le navigateur et arrete le polling."""
```

**Step 5 : Create empty package __init__**

`src/xpath_detector/browser/__init__.py`:

```python
"""Browser backends — Selenium (default) or Playwright (optional)."""
```

**Step 6 : Run (PASS)**

```bash
pytest tests/test_browser_base.py -v
```

Expected: 1 passed.

**Step 7 : Commit**

```bash
git add src/xpath_detector/browser/ tests/test_browser_base.py
git commit -m "refactor(browser): extract BrowserBackend ABC into package"
```

---

### Task 2 : Adapt PlaywrightBackend to new interface

**Files:**
- Modify: `src/xpath_detector/browser/playwright_backend.py`
- Modify: `tests/test_browser.py` -> rename to `tests/test_playwright_backend.py`

**Step 1 : Rename test file**

```bash
git mv tests/test_browser.py tests/test_playwright_backend.py
```

**Step 2 : Update test content**

Replace contents of `tests/test_playwright_backend.py`:

```python
import pytest

pytest.importorskip("playwright.sync_api")


def test_playwright_backend_implements_interface():
    from xpath_detector.browser.base import BrowserBackend
    from xpath_detector.browser.playwright_backend import PlaywrightBackend

    backend = PlaywrightBackend()
    assert isinstance(backend, BrowserBackend)


def test_playwright_backend_raises_if_playwright_missing(monkeypatch):
    """If playwright module is not importable, ImportError raised with helpful message."""
    import sys
    # Simulate playwright not installed
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    # Reimport target with the simulated absence
    sys.modules.pop("xpath_detector.browser.playwright_backend", None)
    with pytest.raises((ImportError, TypeError)):
        from xpath_detector.browser.playwright_backend import PlaywrightBackend
        PlaywrightBackend()
```

**Step 3 : Modify playwright_backend.py**

Replace the entire file:

```python
"""Playwright sync browser backend (optional)."""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

try:
    from playwright.sync_api import Page, Playwright, sync_playwright
except ImportError as e:
    raise ImportError(
        "Playwright not installed. Install with: pip install xpath-detector[playwright]"
    ) from e

from xpath_detector.browser.base import BrowserBackend
from xpath_detector.overlay import OVERLAY_JS

LOGGER = logging.getLogger(__name__)


class PlaywrightBackend(BrowserBackend):
    POLL_INTERVAL = 0.2

    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._browser = None
        self._page: Page | None = None
        self._capture_callback: Callable[[dict[str, Any]], None] | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=False)
        ctx = self._browser.new_context()
        self._page = ctx.new_page()
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def open(self, url: str) -> None:
        if not self._page:
            raise RuntimeError("Browser not started")
        self._page.goto(url, wait_until="domcontentloaded")
        self._page.evaluate(OVERLAY_JS)

    def reinject_overlay(self) -> None:
        if self._page:
            self._page.evaluate(OVERLAY_JS)

    def on_capture(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._capture_callback = callback

    def current_url(self) -> str:
        return self._page.url if self._page else ""

    def current_title(self) -> str:
        return self._page.title() if self._page else ""

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        try:
            if self._browser:
                self._browser.close()
        finally:
            if self._pw:
                self._pw.stop()

    def _poll_loop(self) -> None:
        while self._running:
            try:
                if self._page:
                    items = self._page.evaluate(
                        "() => (window.__xpath_capture_queue || []).splice(0)"
                    )
                    for item in items or []:
                        if self._capture_callback:
                            self._capture_callback(item)
            except Exception as e:
                LOGGER.debug("Poll loop transient error: %s", e)
            time.sleep(self.POLL_INTERVAL)
```

**Step 4 : Run test**

```bash
pytest tests/test_playwright_backend.py -v
```

Expected: 1 or 2 passing (depends on whether playwright is installed). At minimum the first test passes if playwright IS installed, or is skipped if not.

**Step 5 : Commit**

```bash
git add src/xpath_detector/browser/playwright_backend.py tests/test_playwright_backend.py
git commit -m "refactor(playwright): adapt to BrowserBackend interface, use queue-based capture"
```

---

## Phase 2 — SeleniumBackend

### Task 3 : Add selenium to dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1 : Update pyproject.toml**

In `[project]` section, modify `dependencies`:

```toml
dependencies = [
    "selenium>=4.0",
    "rich>=13.0",
    "click>=8.0",
]
```

In `[project.optional-dependencies]`, modify `dev` and add `playwright`:

```toml
[project.optional-dependencies]
playwright = ["playwright>=1.40"]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.4",
    "black>=24.0",
    "pre-commit>=3.0",
]
```

Note: `pytest-playwright` is removed (was unused).

**Step 2 : Reinstall**

```bash
pip install -e ".[dev]"
```

This will install selenium if not already present.

**Step 3 : Verify selenium importable**

```bash
python -c "from selenium import webdriver; print('ok')"
```

Expected: `ok`

**Step 4 : Commit**

```bash
git add pyproject.toml
git commit -m "chore(deps): selenium becomes core, playwright moves to optional extra"
```

---

### Task 4 : SeleniumBackend smoke test + skeleton

**Files:**
- Create: `tests/test_selenium_backend.py`
- Create: `src/xpath_detector/browser/selenium_backend.py`

**Step 1 : Test**

`tests/test_selenium_backend.py`:

```python
import pytest

pytest.importorskip("selenium")


def test_selenium_backend_implements_interface():
    from xpath_detector.browser.base import BrowserBackend
    from xpath_detector.browser.selenium_backend import SeleniumBackend

    backend = SeleniumBackend()
    assert isinstance(backend, BrowserBackend)


def test_selenium_backend_methods_exist():
    """All abstract methods must be implemented (no TypeError on instantiation)."""
    from xpath_detector.browser.selenium_backend import SeleniumBackend

    backend = SeleniumBackend()
    # Methods must be callable
    assert callable(backend.start)
    assert callable(backend.open)
    assert callable(backend.reinject_overlay)
    assert callable(backend.on_capture)
    assert callable(backend.current_url)
    assert callable(backend.current_title)
    assert callable(backend.stop)


def test_selenium_backend_current_url_before_start():
    from xpath_detector.browser.selenium_backend import SeleniumBackend

    backend = SeleniumBackend()
    assert backend.current_url() == ""


def test_selenium_backend_on_capture_stores_callback():
    from xpath_detector.browser.selenium_backend import SeleniumBackend

    backend = SeleniumBackend()
    called = []
    backend.on_capture(lambda d: called.append(d))
    backend._capture_callback({"hello": "world"})  # type: ignore
    assert called == [{"hello": "world"}]
```

**Step 2 : Run (FAIL)**

```bash
pytest tests/test_selenium_backend.py -v
```

Expected: ImportError on `xpath_detector.browser.selenium_backend`.

**Step 3 : Implement**

`src/xpath_detector/browser/selenium_backend.py`:

```python
"""Selenium WebDriver backend (default, corporate-friendly)."""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver

from xpath_detector.browser.base import BrowserBackend
from xpath_detector.overlay import OVERLAY_JS

LOGGER = logging.getLogger(__name__)


class SeleniumBackend(BrowserBackend):
    POLL_INTERVAL = 0.2

    def __init__(self) -> None:
        self._driver: WebDriver | None = None
        self._capture_callback: Callable[[dict[str, Any]], None] | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        self._driver = webdriver.Chrome(options=options)
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def open(self, url: str) -> None:
        if not self._driver:
            raise RuntimeError("Browser not started")
        self._driver.get(url)
        self._driver.execute_script(OVERLAY_JS)

    def reinject_overlay(self) -> None:
        if self._driver:
            self._driver.execute_script(OVERLAY_JS)

    def on_capture(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._capture_callback = callback

    def current_url(self) -> str:
        return self._driver.current_url if self._driver else ""

    def current_title(self) -> str:
        return self._driver.title if self._driver else ""

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._driver:
            self._driver.quit()

    def _poll_loop(self) -> None:
        while self._running:
            try:
                if self._driver:
                    items = self._driver.execute_script(
                        "return (window.__xpath_capture_queue || []).splice(0);"
                    )
                    for item in items or []:
                        if self._capture_callback:
                            self._capture_callback(item)
            except Exception as e:
                LOGGER.debug("Poll loop transient error: %s", e)
            time.sleep(self.POLL_INTERVAL)
```

**Step 4 : Run (PASS)**

```bash
pytest tests/test_selenium_backend.py -v
```

Expected: 4 passed.

**Step 5 : Commit**

```bash
git add src/xpath_detector/browser/selenium_backend.py tests/test_selenium_backend.py
git commit -m "feat(browser): add SeleniumBackend (default, uses system Chrome)"
```

---

## Phase 3 — Factory + queue-based overlay

### Task 5 : Modify overlay.py — queue at end, no console.log

**Files:**
- Modify: `src/xpath_detector/overlay.py`
- Modify: `tests/test_overlay.py`

**Step 1 : Add test**

Append to `tests/test_overlay.py`:

```python
def test_overlay_uses_queue_instead_of_console_log():
    from xpath_detector.overlay import OVERLAY_JS

    assert "__xpath_capture_queue" in OVERLAY_JS
    # console.log of __XPATH_CAPTURE__ should be gone
    assert "console.log('__XPATH_CAPTURE__'" not in OVERLAY_JS


def test_overlay_queue_initialized_idempotent():
    from xpath_detector.overlay import OVERLAY_JS

    assert "window.__xpath_capture_queue = window.__xpath_capture_queue || []" in OVERLAY_JS
```

**Step 2 : Run (FAIL)**

```bash
pytest tests/test_overlay.py -v
```

Expected: 2 new tests fail.

**Step 3 : Modify overlay.py**

In `src/xpath_detector/overlay.py`, find the click handler block:

```javascript
        console.log('__XPATH_CAPTURE__' + JSON.stringify(data));
```

Replace with:

```javascript
        window.__xpath_capture_queue = window.__xpath_capture_queue || [];
        window.__xpath_capture_queue.push(data);
```

**Step 4 : Run (PASS)**

```bash
pytest tests/test_overlay.py -v
```

Expected: all overlay tests pass.

**Step 5 : Commit**

```bash
git add src/xpath_detector/overlay.py tests/test_overlay.py
git commit -m "refactor(overlay): replace console.log with queue (uniform between backends)"
```

---

### Task 6 : Factory create_backend + backward compat

**Files:**
- Modify: `src/xpath_detector/browser/__init__.py`
- Create: `tests/test_browser_factory.py`

**Step 1 : Tests**

`tests/test_browser_factory.py`:

```python
import os

import pytest

from xpath_detector.browser import create_backend
from xpath_detector.browser.base import BrowserBackend


def test_create_backend_default_is_selenium():
    """No argument, no env var -> SeleniumBackend."""
    os.environ.pop("XPATH_DETECTOR_BACKEND", None)
    backend = create_backend()
    assert isinstance(backend, BrowserBackend)
    assert backend.__class__.__name__ == "SeleniumBackend"


def test_create_backend_explicit_selenium():
    backend = create_backend("selenium")
    assert backend.__class__.__name__ == "SeleniumBackend"


def test_create_backend_env_var(monkeypatch):
    """Env var XPATH_DETECTOR_BACKEND controls default selection."""
    monkeypatch.setenv("XPATH_DETECTOR_BACKEND", "selenium")
    backend = create_backend()
    assert backend.__class__.__name__ == "SeleniumBackend"


def test_create_backend_unknown_raises():
    with pytest.raises(ValueError, match="Unknown backend"):
        create_backend("nonexistent")


def test_browser_controller_legacy_alias_still_works():
    """from xpath_detector.browser import BrowserController must still work."""
    from xpath_detector.browser import BrowserController

    backend = BrowserController()
    assert isinstance(backend, BrowserBackend)


def test_create_backend_playwright_if_installed():
    """If playwright is installed, the factory can create it."""
    pytest.importorskip("playwright.sync_api")
    backend = create_backend("playwright")
    assert backend.__class__.__name__ == "PlaywrightBackend"
```

**Step 2 : Run (FAIL)**

```bash
pytest tests/test_browser_factory.py -v
```

Expected: ImportError on `create_backend`.

**Step 3 : Update browser/__init__.py**

Replace contents of `src/xpath_detector/browser/__init__.py`:

```python
"""Browser backends — Selenium (default) or Playwright (optional)."""
from __future__ import annotations

import os

from xpath_detector.browser.base import BrowserBackend


def create_backend(name: str | None = None) -> BrowserBackend:
    """Cree le backend selon le nom ou la var d'env XPATH_DETECTOR_BACKEND."""
    name = name or os.environ.get("XPATH_DETECTOR_BACKEND", "selenium")
    if name == "selenium":
        from xpath_detector.browser.selenium_backend import SeleniumBackend

        return SeleniumBackend()
    if name == "playwright":
        from xpath_detector.browser.playwright_backend import PlaywrightBackend

        return PlaywrightBackend()
    raise ValueError(
        f"Unknown backend: {name}. Expected 'selenium' or 'playwright'."
    )


def BrowserController() -> BrowserBackend:
    """Legacy alias for create_backend() with default selection.

    Kept for backward compatibility with v1.0 and v1.1 imports.
    """
    return create_backend()
```

**Step 4 : Run (PASS)**

```bash
pytest tests/test_browser_factory.py -v
```

Expected: 6 passed (or 5 if playwright not installed - the last test is skipped).

**Step 5 : Commit**

```bash
git add src/xpath_detector/browser/__init__.py tests/test_browser_factory.py
git commit -m "feat(browser): add create_backend factory with env var selection"
```

---

## Phase 4 — Integration into shell

### Task 7 : Update shell.py to use create_backend

**Files:**
- Modify: `src/xpath_detector/shell.py`
- Modify: `tests/test_shell.py`

**Step 1 : Update shell.py**

In `src/xpath_detector/shell.py`, find :

```python
from xpath_detector.browser import BrowserController
```

Keep that import (it still works via alias). But change the usage in `Shell.__init__`:

```python
        self.browser = BrowserController()
```

to:

```python
        from xpath_detector.browser import create_backend
        self.browser = create_backend()
```

And remove the top-level `from xpath_detector.browser import BrowserController` line.

**Step 2 : Update test fixture**

In `tests/test_shell.py`, the fixture currently patches `xpath_detector.shell.BrowserController`. Update to patch `xpath_detector.shell.create_backend`:

```python
@pytest.fixture
def shell_no_browser():
    """Shell with mocked backend factory."""
    with patch("xpath_detector.shell.create_backend") as mock_factory:
        mock_factory.return_value = MagicMock()
        from xpath_detector.shell import Shell

        shell = Shell()
        yield shell
```

Wait — `create_backend` is imported inside `__init__`, so the patch target is correct only if we import it at module level. Adjust shell.py to import at top:

```python
from xpath_detector.browser import create_backend
```

And in `__init__`:

```python
        self.browser = create_backend()
```

**Step 3 : Run shell tests**

```bash
pytest tests/test_shell.py -v
```

Expected: 5 passed.

**Step 4 : Run full suite for regression**

```bash
pytest -q
```

Expected: ~72 tests passing.

**Step 5 : Commit**

```bash
git add src/xpath_detector/shell.py tests/test_shell.py
git commit -m "feat(shell): use create_backend factory (supports XPATH_DETECTOR_BACKEND)"
```

---

## Phase 5 — Documentation + release

### Task 8 : Update README

**Files:**
- Modify: `README.md`

**Step 1 : Update README**

Replace the Installation section and add a new "Choosing a backend" section:

```markdown
## Installation

Default install (Selenium backend, recommended for corporate environments):

\`\`\`bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
\`\`\`

Selenium uses the system Chrome. No additional binary download required.

### Optional: Playwright backend

If you prefer Playwright (faster, more features) and have network access to download Chromium:

\`\`\`bash
pip install -e ".[dev,playwright]"
playwright install chromium
\`\`\`

## Choosing a backend

By default, xpath-detector uses Selenium. To switch to Playwright:

\`\`\`bash
export XPATH_DETECTOR_BACKEND=playwright
python -m xpath_detector
\`\`\`

Supported values: \`selenium\` (default), \`playwright\` (requires \`[playwright]\` extra).
```

**Step 2 : Commit**

```bash
git add README.md
git commit -m "docs: document backend selection (Selenium default, Playwright optional)"
```

---

### Task 9 : Update CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

**Step 1 : Add v1.2.0 entry**

At the top of `CHANGELOG.md`, after the title, before the v1.1.0 section, add:

```markdown
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
```

**Step 2 : Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG entry for v1.2.0"
```

---

### Task 10 : Lint + tag + push + release

**Step 1 : Lint check**

```bash
cd /Users/nitch/projects/git_projets/xpath_detector
source .venv/bin/activate
ruff check src/ tests/ scripts/
black --check src/ tests/ scripts/
```

If issues, auto-fix and commit:
```bash
ruff check src/ tests/ scripts/ --fix
black src/ tests/ scripts/
git add -A && git commit -m "chore: apply ruff/black auto-fixes"
```

**Step 2 : Final tests**

```bash
pytest -q
pytest --cov=xpath_detector --cov-report=term
```

Expected: all tests pass, coverage ~73%+.

**Step 3 : Tag and push**

```bash
git tag v1.2.0
git push origin master
git push origin v1.2.0
```

**Step 4 : Create GitHub release**

```bash
gh release create v1.2.0 --title "v1.2.0 - Pluggable browser backends" --notes "$(awk '/^## \[1\.2\.0\]/{flag=1;next}/^## \[1\.1\.0\]/{flag=0}flag' CHANGELOG.md)"
```

If awk extraction is tricky:
```bash
gh release create v1.2.0 --title "v1.2.0 - Pluggable browser backends" --notes "Adds Selenium backend as default (corporate-friendly, uses system Chrome). Playwright is now optional via the [playwright] extra. New env var XPATH_DETECTOR_BACKEND controls selection. See CHANGELOG.md for details."
```

**Step 5 : Verify release URL**

```bash
gh release view v1.2.0 --web=false
```

---

## Recapitulatif

| Phase | Tasks | Files affected | Duree estimee |
|-------|-------|----------------|---------------|
| Phase 1 (ABC + restructure) | 1, 2 | browser/, tests | 45 min |
| Phase 2 (SeleniumBackend) | 3, 4 | selenium_backend.py, pyproject.toml | 45 min |
| Phase 3 (overlay + factory) | 5, 6 | overlay.py, browser/__init__.py | 45 min |
| Phase 4 (integration) | 7 | shell.py | 30 min |
| Phase 5 (docs + release) | 8, 9, 10 | README, CHANGELOG, release | 30 min |
| **Total** | **10 tasks** | | **~3h** |

**Commits attendus** : ~10 commits atomiques.

**Tests attendus** : 62 (v1.1) + 4 (selenium) + 6 (factory) + 1 (base) + 2 (overlay) - 1 (renamed) = ~74 tests.

**Coverage cible** : 73-75% globale.

---

## Execution

Plan complet et sauvegarde. Deux options :

**1. Subagent-Driven (cette session)** — je delegue par phase

**2. Parallel Session (separee)** — tu ouvres une nouvelle session avec `executing-plans`

Recommandation : **1**, vu que la session a deja tout le contexte v1.0/v1.1.
