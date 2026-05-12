import os

import pytest

from xpath_detector.browser import create_backend
from xpath_detector.browser.base import BrowserBackend


def test_create_backend_default_is_selenium():
    os.environ.pop("XPATH_DETECTOR_BACKEND", None)
    backend = create_backend()
    assert isinstance(backend, BrowserBackend)
    assert backend.__class__.__name__ == "SeleniumBackend"


def test_create_backend_explicit_selenium():
    backend = create_backend("selenium")
    assert backend.__class__.__name__ == "SeleniumBackend"


def test_create_backend_env_var(monkeypatch):
    monkeypatch.setenv("XPATH_DETECTOR_BACKEND", "selenium")
    backend = create_backend()
    assert backend.__class__.__name__ == "SeleniumBackend"


def test_create_backend_unknown_raises():
    with pytest.raises(ValueError, match="Unknown backend"):
        create_backend("nonexistent")


def test_browser_controller_legacy_alias_still_works():
    from xpath_detector.browser import BrowserController

    backend = BrowserController()
    assert isinstance(backend, BrowserBackend)


def test_create_backend_playwright_if_installed():
    pytest.importorskip("playwright.sync_api")
    backend = create_backend("playwright")
    assert backend.__class__.__name__ == "PlaywrightBackend"
