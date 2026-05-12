import pytest

playwright = pytest.importorskip("playwright.sync_api")


def test_browser_can_be_constructed():
    from xpath_detector.browser import BrowserController

    ctrl = BrowserController()
    assert ctrl is not None
