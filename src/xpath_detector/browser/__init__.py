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


def BrowserController() -> BrowserBackend:
    """Legacy alias for create_backend() with default selection.

    Kept for backward compatibility with v1.0 and v1.1 imports.
    """
    return create_backend()
