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
        last_url: str | None = None
        while self._running:
            try:
                if self._page:
                    # Detect navigation : if URL changed, the overlay is gone -> re-inject.
                    current = self._page.url
                    if current and current != last_url:
                        last_url = current
                        self._page.evaluate(OVERLAY_JS)

                    items = self._page.evaluate(
                        "() => (window.__xpath_capture_queue || []).splice(0)"
                    )
                    for item in items or []:
                        if self._capture_callback:
                            self._capture_callback(item)
            except Exception as e:
                LOGGER.debug("Poll loop transient error: %s", e)
            time.sleep(self.POLL_INTERVAL)
