"""Unit tests for shell.py interactive logic."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from xpath_detector.models import Screen, Session


@pytest.fixture
def shell_no_browser():
    """Shell with mocked BrowserController."""
    with patch("xpath_detector.shell.BrowserController") as mock_browser_class:
        mock_browser_class.return_value = MagicMock()
        from xpath_detector.shell import Shell

        shell = Shell()
        yield shell


def test_load_exporters_returns_registered():
    """_load_exporters() should discover all 5 exporters via entry_points."""
    from xpath_detector.shell import _load_exporters

    exporters = _load_exporters()
    assert "json" in exporters
    assert "html" in exporters
    assert "robot" in exporters
    assert "java" in exporters
    assert "python" in exporters


def test_on_capture_with_no_screen_ignores(shell_no_browser):
    """Capture without a current screen should be ignored (no element added)."""
    shell_no_browser.current_screen = None
    shell_no_browser._on_capture({"tag": "input", "attributes": {}})
    assert shell_no_browser.current_screen is None


def test_on_capture_adds_element_to_current_screen(shell_no_browser):
    """_on_capture should append an Element to the current Screen."""
    shell_no_browser.session = Session(id="test")
    shell_no_browser.session.screens["login"] = Screen(
        name="login", url="https://x.fr", title="Login", timestamp=datetime.now()
    )
    shell_no_browser.current_screen = "login"

    with patch.object(shell_no_browser.console, "input", return_value="test desc"):
        shell_no_browser._on_capture(
            {
                "tag": "input",
                "text": None,
                "attributes": {"id": "x"},
                "is_visible": True,
                "is_enabled": True,
                "absolute_xpath": "/html/body/input",
                "nearby_label": "Username",
            }
        )

    assert len(shell_no_browser.session.screens["login"].elements) == 1
    el = shell_no_browser.session.screens["login"].elements[0]
    assert el.tag == "input"
    assert el.description == "test desc"
    assert any(c.strategy == "by_id" for c in el.xpaths)
    assert any(c.strategy == "by_label_neighbor" for c in el.xpaths)


def test_cmd_export_all_dispatches_to_each_exporter(shell_no_browser, tmp_path: Path, monkeypatch):
    """cmd_export('all') should call every exporter."""
    monkeypatch.chdir(tmp_path)

    called = []
    for name, exporter in shell_no_browser.exporters.items():
        original_export = exporter.export

        def make_wrapper(n, orig):
            def wrapper(session, output_dir):
                called.append(n)
                return orig(session, output_dir)

            return wrapper

        exporter.export = make_wrapper(name, original_export)

    shell_no_browser.session = Session(id="test_all")
    shell_no_browser.cmd_export(["all"])

    assert set(called) == {"json", "html", "robot", "java", "python"}


def test_cmd_export_unknown_prints_error(shell_no_browser, capsys):
    """cmd_export with unknown format should print an error."""
    shell_no_browser.cmd_export(["nonexistent_format"])
    captured = capsys.readouterr()
    assert "Unknown exporter" in captured.out or "Unknown exporter" in captured.err
