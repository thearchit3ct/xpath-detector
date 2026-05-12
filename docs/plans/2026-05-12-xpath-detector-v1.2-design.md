# xpath-detector v1.2 — Design

**Date** : 2026-05-12
**Statut** : Approuve
**Cible** : Pluggable browser backends — Selenium par defaut (corporate-friendly), Playwright en option

---

## 1. Contexte

v1.1.0 publiee avec une dependance forte sur Playwright. Probleme remonte par l'utilisateur :

> "Je ne peux pas installer playwright sur ma machine pour utiliser l'application"

Diagnostic :
- PyPI accessible
- Selenium fonctionne (deja utilise dans le projet vpu-functions)
- `pip install playwright` ou `playwright install chromium` est bloque (probablement le download du binaire Chromium depuis Microsoft)

v1.2 vise a rendre le backend pluggable, avec Selenium comme defaut corporate-friendly et Playwright en option.

---

## 2. Decisions de design

| # | Sujet | Choix |
|---|-------|-------|
| 1 | Approche | Hybride (option C) : Selenium par defaut, Playwright optionnel |
| 2 | Selection backend | Variable d'env `XPATH_DETECTOR_BACKEND` (defaut `selenium`) |
| 3 | Communication overlay -> Python | Queue JS `window.__xpath_capture_queue` + polling Python (uniforme entre backends) |
| 4 | Compat ascendante | `from xpath_detector.browser import BrowserController` continue de fonctionner (alias) |
| 5 | Tests existants Playwright | Renommes + skip si Playwright absent |

---

## 3. Architecture

### Structure

```
src/xpath_detector/
├── browser/                       # nouveau package (remplace browser.py)
│   ├── __init__.py                # alias BrowserController + factory create_backend
│   ├── base.py                    # BrowserBackend ABC
│   ├── selenium_backend.py        # SeleniumBackend (defaut)
│   └── playwright_backend.py      # PlaywrightBackend (optionnel)
├── overlay.py                     # Modifie : queue JS, plus de console.log
└── shell.py                       # Modifie : create_backend() au lieu de BrowserController()
```

### `browser/base.py`

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

### `browser/selenium_backend.py`

Le backend par defaut, base sur Selenium 4 et le Chrome systeme.

Points cles :
- `webdriver.Chrome(options=...)` — utilise le Chrome installe (pas de download)
- Thread daemon pour poller `window.__xpath_capture_queue`
- Polling interval : 200ms (configurable plus tard)
- Tolerance aux exceptions (navigateur peut etre en navigation)

```python
class SeleniumBackend(BrowserBackend):
    POLL_INTERVAL = 0.2

    def __init__(self) -> None:
        self._driver: WebDriver | None = None
        self._capture_callback: Callable[[dict], None] | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        self._driver = webdriver.Chrome(options=options)
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def open(self, url: str) -> None:
        self._driver.get(url)
        self._driver.execute_script(OVERLAY_JS)

    def reinject_overlay(self) -> None:
        self._driver.execute_script(OVERLAY_JS)

    def on_capture(self, callback):
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
                items = self._driver.execute_script(
                    "return (window.__xpath_capture_queue || []).splice(0);"
                )
                for item in items or []:
                    if self._capture_callback:
                        self._capture_callback(item)
            except Exception:
                pass  # navigation/page rebuild, skip this poll
            time.sleep(self.POLL_INTERVAL)
```

### `browser/playwright_backend.py`

Le code de l'ancien `browser.py`, adapte pour utiliser la queue (au lieu du console handler) :

```python
class PlaywrightBackend(BrowserBackend):
    POLL_INTERVAL = 0.2

    def __init__(self) -> None:
        try:
            from playwright.sync_api import sync_playwright  # noqa
        except ImportError as e:
            raise ImportError(
                "Playwright not installed. Install with: pip install xpath-detector[playwright]"
            ) from e
        # ... init similaire a Selenium
```

L'event handler `page.on("console", ...)` est supprime au profit du polling — code uniforme entre backends.

### `browser/__init__.py`

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
    raise ValueError(f"Unknown backend: {name}. Expected 'selenium' or 'playwright'.")


# Backward compatibility alias
def BrowserController() -> BrowserBackend:
    """Legacy alias for create_backend() with default selection."""
    return create_backend()
```

### `overlay.py` modifie

Remplacer le `console.log` final par push dans queue :

```javascript
window.__xpath_capture_queue = window.__xpath_capture_queue || [];
window.__xpath_capture_queue.push(data);
```

### `shell.py` modifie

```python
# Avant :
from xpath_detector.browser import BrowserController
...
self.browser = BrowserController()

# Apres :
from xpath_detector.browser import create_backend
...
self.browser = create_backend()
```

---

## 4. pyproject.toml

```toml
dependencies = [
    "selenium>=4.0",     # Devient core
    "rich>=13.0",
    "click>=8.0",
]

[project.optional-dependencies]
playwright = ["playwright>=1.40"]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.4",
    "black>=24.0",
    "pre-commit>=3.0",
    # Playwright NOT in dev — install separately if needed
]
```

`pytest-playwright` est retire (n'etait pas utilise).

---

## 5. Tests

| Test file | Backend | Skip si |
|-----------|---------|---------|
| `tests/test_browser_base.py` | ABC | n/a (toujours run) |
| `tests/test_selenium_backend.py` | Selenium | importorskip("selenium") - toujours dispo |
| `tests/test_playwright_backend.py` | Playwright | importorskip("playwright") - skip si pas installe |
| `tests/test_browser_factory.py` | create_backend | n/a |

Les tests sont **smoke tests** (instanciation, dispatch correct) — pas de vrai navigateur en CI.

---

## 6. Migration / Compat ascendante

- Import `from xpath_detector.browser import BrowserController` continue de fonctionner
- Le code de `shell.py` actuel (`BrowserController()` -> instance) continue de fonctionner via l'alias
- Sessions JSON v1.1 sont 100% compatibles (aucun changement de format)

---

## 7. Documentation

Mettre a jour `README.md` :
- Section "Installation" :
  - Defaut : `pip install -e ".[dev]"` (Selenium uniquement)
  - Optionnel : `pip install -e ".[dev,playwright]"` + `playwright install chromium`
- Nouvelle section "Choosing a backend" expliquant `XPATH_DETECTOR_BACKEND`

---

## 8. Livrables et metriques

- **Commits** : ~10 atomiques
- **Tests** : +4 a +6 (browser_base + selenium + playwright + factory)
- **Tag** : `v1.2.0`
- **CHANGELOG.md** : nouvelle section [1.2.0]

---

## 9. Risques

| Risque | Impact | Mitigation |
|--------|:------:|------------|
| Selenium thread polling bloque sur navigation | Moyen | `try/except` autour de `execute_script`, ignore les erreurs transitoires |
| Race condition sur queue (push pendant splice) | Faible | `splice(0)` est atomique en JS single-thread |
| ChromeDriver pas synchro avec Chrome installe | Eleve | Documenter `webdriver-manager` comme option |
| Playwright tests cassent en CI | Faible | `importorskip` les saute proprement |

---

## 10. Hors scope (a v1.3+)

- CLI flag `--backend` (utilise env var pour v1.2)
- Mode headless (`--headless`)
- Firefox/Edge backends Selenium
- Shadow DOM
- Multi-tabs

---

## 11. Prochaines etapes

Apres validation, invoquer `superpowers:writing-plans` pour generer le plan TDD.
