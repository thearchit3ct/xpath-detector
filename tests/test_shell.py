"""Unit tests for shell.py interactive logic."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from xpath_detector.models import Screen, Session


@pytest.fixture
def shell_no_browser():
    """Shell with mocked BrowserController."""
    with patch("xpath_detector.shell.create_backend") as mock_factory:
        mock_factory.return_value = MagicMock()
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
    """_on_capture should append an Element to the current Screen.

    CRITICAL: _on_capture is called from poll thread. It MUST NOT call console.input()
    (would deadlock the main run() loop also reading stdin).
    """
    shell_no_browser.session = Session(id="test")
    shell_no_browser.session.screens["login"] = Screen(
        name="login", url="https://x.fr", title="Login", timestamp=datetime.now()
    )
    shell_no_browser.current_screen = "login"

    # Spy on console.input - it must NEVER be called from _on_capture
    with patch.object(shell_no_browser.console, "input") as mock_input:
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
        assert (
            mock_input.call_count == 0
        ), "_on_capture must not call console.input() (poll thread cannot block on stdin)"

    assert len(shell_no_browser.session.screens["login"].elements) == 1
    el = shell_no_browser.session.screens["login"].elements[0]
    assert el.tag == "input"
    # Auto-description from nearby_label
    assert el.description == "Username"
    assert any(c.strategy == "by_id" for c in el.xpaths)
    assert any(c.strategy == "by_label_neighbor" for c in el.xpaths)


def test_default_description_priority():
    """Auto-generated description prefers nearby_label > text > id > name > aria-label > tag."""
    from xpath_detector.shell import _default_description

    # nearby_label wins
    assert (
        _default_description(
            {
                "tag": "input",
                "text": "ignored",
                "attributes": {"id": "x"},
                "nearby_label": "Montant :",
            }
        )
        == "Montant :"
    )

    # text wins over id when nearby_label absent
    assert (
        _default_description({"tag": "a", "text": "Click here", "attributes": {"id": "x"}})
        == "Click here"
    )

    # id used when text empty
    assert (
        _default_description({"tag": "input", "text": "", "attributes": {"id": "login"}})
        == "input#login"
    )

    # name fallback
    assert (
        _default_description({"tag": "input", "text": None, "attributes": {"name": "user"}})
        == "input[name=user]"
    )

    # tag fallback last resort
    assert _default_description({"tag": "div", "text": None, "attributes": {}}) == "div"


def test_cmd_describe_updates_existing_capture(shell_no_browser):
    """cmd_describe should rename a previously captured element."""
    from xpath_detector.models import Element, XPathCandidate

    shell_no_browser.session = Session(id="t")
    shell_no_browser.session.screens["main"] = Screen(
        name="main",
        url="",
        title="",
        timestamp=datetime.now(),
        elements=[
            Element(
                tag="input",
                text=None,
                attributes={},
                xpaths=[XPathCandidate("by_id", "//x", 95)],
                is_visible=True,
                is_enabled=True,
                description="auto",
            )
        ],
    )
    shell_no_browser.current_screen = "main"

    shell_no_browser.cmd_describe(["0", "Manually", "renamed"])
    assert shell_no_browser.session.screens["main"].elements[0].description == "Manually renamed"


def test_cmd_describe_invalid_index_errors(shell_no_browser, capsys):
    shell_no_browser.session = Session(id="t")
    shell_no_browser.session.screens["main"] = Screen(
        name="main", url="", title="", timestamp=datetime.now()
    )
    shell_no_browser.current_screen = "main"
    shell_no_browser.cmd_describe(["99", "test"])
    out = capsys.readouterr().out
    assert "out of range" in out


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
