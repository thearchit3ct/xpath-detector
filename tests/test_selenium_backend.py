import pytest

pytest.importorskip("selenium")


def test_selenium_backend_implements_interface():
    from xpath_detector.browser.base import BrowserBackend
    from xpath_detector.browser.selenium_backend import SeleniumBackend

    backend = SeleniumBackend()
    assert isinstance(backend, BrowserBackend)


def test_selenium_backend_methods_exist():
    from xpath_detector.browser.selenium_backend import SeleniumBackend

    backend = SeleniumBackend()
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
    backend._capture_callback({"hello": "world"})
    assert called == [{"hello": "world"}]
