import pytest

from xpath_detector.browser.base import BrowserBackend


def test_browser_backend_is_abstract():
    with pytest.raises(TypeError):
        BrowserBackend()
