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
        last_url: str | None = None
        while self._running:
            try:
                if self._driver:
                    # Detect navigation : if URL changed, the overlay is gone -> re-inject.
                    current = self._driver.current_url
                    if current and current != last_url:
                        last_url = current
                        self._driver.execute_script(OVERLAY_JS)

                    items = self._driver.execute_script(
                        "return (window.__xpath_capture_queue || []).splice(0);"
                    )
                    for item in items or []:
                        if self._capture_callback:
                            self._capture_callback(item)
            except Exception as e:
                LOGGER.debug("Poll loop transient error: %s", e)
            time.sleep(self.POLL_INTERVAL)
