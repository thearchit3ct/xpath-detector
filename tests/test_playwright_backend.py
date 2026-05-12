import pytest

pytest.importorskip("playwright.sync_api")


def test_playwright_backend_implements_interface():
    from xpath_detector.browser.base import BrowserBackend
    from xpath_detector.browser.playwright_backend import PlaywrightBackend

    backend = PlaywrightBackend()
    assert isinstance(backend, BrowserBackend)
