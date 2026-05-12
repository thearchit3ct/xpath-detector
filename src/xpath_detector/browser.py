"""Playwright sync browser wrapper."""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from playwright.sync_api import Page, Playwright, sync_playwright

from xpath_detector.overlay import OVERLAY_JS

LOGGER = logging.getLogger(__name__)
_CAPTURE_PREFIX = "__XPATH_CAPTURE__"


class BrowserController:
    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._browser = None
        self._page: Page | None = None
        self._capture_callback: Callable[[dict[str, Any]], None] | None = None

    def start(self) -> None:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=False)
        ctx = self._browser.new_context()
        self._page = ctx.new_page()
        self._page.on("console", self._on_console_message)

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
        try:
            if self._browser:
                self._browser.close()
        finally:
            if self._pw:
                self._pw.stop()

    def _on_console_message(self, msg: Any) -> None:
        text = msg.text
        if not text.startswith(_CAPTURE_PREFIX):
            return
        payload = text[len(_CAPTURE_PREFIX):]
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            LOGGER.warning("Invalid capture payload: %s", payload[:100])
            return
        if self._capture_callback:
            self._capture_callback(data)
