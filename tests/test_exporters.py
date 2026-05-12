from datetime import datetime
from pathlib import Path

import pytest

from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Element, Screen, Session, XPathCandidate


def test_exporter_is_abstract():
    with pytest.raises(TypeError):
        Exporter()


def _sample_session() -> Session:
    return Session(
        id="20260512_120000",
        screens={
            "login": Screen(
                name="login",
                url="https://x.fr",
                title="Login",
                timestamp=datetime(2026, 5, 12, 12, 0, 0),
                elements=[
                    Element(
                        tag="input",
                        text=None,
                        attributes={"id": "_login"},
                        xpaths=[XPathCandidate("by_id", "//input[@id='_login']", 95)],
                        is_visible=True,
                        is_enabled=True,
                        description="Login field",
                    )
                ],
            )
        },
    )


def test_json_exporter_creates_file(tmp_path: Path):
    import json

    from xpath_detector.exporters.json_exp import JsonExporter

    exporter = JsonExporter()
    out = exporter.export(_sample_session(), tmp_path)
    assert out.suffix == ".json"
    data = json.loads(out.read_text())
    assert data["id"] == "20260512_120000"
    assert "login" in data["screens"]


def test_robot_exporter_writes_resource_per_screen(tmp_path: Path):
    from xpath_detector.exporters.robot_exp import RobotExporter

    out = RobotExporter().export(_sample_session(), tmp_path)
    resource = out / "login" / "locators.resource"
    assert resource.exists()
    content = resource.read_text()
    assert "*** Variables ***" in content
    assert "//input[@id='_login']" in content


def test_java_exporter_generates_locators_class(tmp_path: Path):
    from xpath_detector.exporters.java_exp import JavaExporter

    out = JavaExporter().export(_sample_session(), tmp_path)
    java_file = out / "Locators.java"
    content = java_file.read_text()
    assert "public final class Locators" in content
    assert "public static final class Login" in content
    assert "By.xpath(\"//input[@id='_login']\")" in content


def test_python_exporter_generates_module(tmp_path: Path):
    from xpath_detector.exporters.python_exp import PythonExporter

    out = PythonExporter().export(_sample_session(), tmp_path)
    py_file = out / "locators.py"
    content = py_file.read_text()
    assert "from selenium.webdriver.common.by import By" in content
    assert "class Login:" in content
    assert "(By.XPATH, \"//input[@id='_login']\")" in content


def test_html_exporter_escapes_user_content(tmp_path: Path):
    from xpath_detector.exporters.html_exp import HtmlExporter

    session = _sample_session()
    session.screens["login"].elements[0].description = "<script>alert(1)</script>"

    out = HtmlExporter().export(session, tmp_path)
    content = out.read_text()
    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;" in content


def test_html_exporter_contains_session_info(tmp_path: Path):
    from xpath_detector.exporters.html_exp import HtmlExporter

    out = HtmlExporter().export(_sample_session(), tmp_path)
    content = out.read_text()
    assert "20260512_120000" in content
    assert "login" in content


def _session_with_duplicate_descriptions() -> Session:
    """Two elements producing the same CONSTANT name (regression test v1.2.2)."""
    return Session(
        id="dup_test",
        screens={
            "form": Screen(
                name="form",
                url="x",
                title="t",
                timestamp=datetime(2026, 5, 12, 12, 0, 0),
                elements=[
                    Element(
                        tag="input",
                        text=None,
                        attributes={"id": "a"},
                        xpaths=[XPathCandidate("by_id", "//input[@id='a']", 95)],
                        is_visible=True,
                        is_enabled=True,
                        description="Montant",
                    ),
                    Element(
                        tag="button",
                        text=None,
                        attributes={"id": "b"},
                        xpaths=[XPathCandidate("by_id", "//button[@id='b']", 95)],
                        is_visible=True,
                        is_enabled=True,
                        description="Montant",
                    ),
                ],
            )
        },
    )


def test_java_exporter_deduplicates_constant_names(tmp_path: Path):
    """Java exporter must not generate duplicate `public static final By X` declarations."""
    from xpath_detector.exporters.java_exp import JavaExporter

    out = JavaExporter().export(_session_with_duplicate_descriptions(), tmp_path)
    content = (out / "Locators.java").read_text()
    assert "public static final By MONTANT = " in content
    assert "public static final By MONTANT_2 = " in content
    decls = [line for line in content.splitlines() if "public static final By" in line]
    names = [line.split()[4] for line in decls]
    assert len(names) == len(set(names)), f"Duplicate names in: {names}"


def test_python_exporter_deduplicates(tmp_path: Path):
    from xpath_detector.exporters.python_exp import PythonExporter

    out = PythonExporter().export(_session_with_duplicate_descriptions(), tmp_path)
    content = (out / "locators.py").read_text()
    assert "MONTANT = (By.XPATH," in content
    assert "MONTANT_2 = (By.XPATH," in content


def test_robot_exporter_deduplicates(tmp_path: Path):
    from xpath_detector.exporters.robot_exp import RobotExporter

    out = RobotExporter().export(_session_with_duplicate_descriptions(), tmp_path)
    content = (out / "form" / "locators.resource").read_text()
    assert "${MONTANT}" in content
    assert "${MONTANT_2}" in content
