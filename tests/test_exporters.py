import pytest

from xpath_detector.exporters.base import Exporter


def test_exporter_is_abstract():
    with pytest.raises(TypeError):
        Exporter()


from datetime import datetime
from pathlib import Path

from xpath_detector.models import Element, Screen, Session, XPathCandidate


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
