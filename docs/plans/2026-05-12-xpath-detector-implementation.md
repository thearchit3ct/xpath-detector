# xpath-detector Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reecrire l'outil xpath-detector avec une architecture moderne (Playwright sync + rich + pytest), exports multi-frameworks (JSON/HTML/Robot/Java/Python), capture interactive par Ctrl+clic avec highlight on hover.

**Architecture:** Package Python `src/xpath_detector/` avec modules separes (models, browser, overlay JS, analyzer, shell, session, exporters/plugin). Communication overlay->shell via `console.log` Playwright. Tests TDD pytest > 70% sur fonctions pures.

**Tech Stack:** Python 3.11+, Playwright sync, rich, click, pytest, ruff, black, pre-commit, uv (gestion deps).

**Conventions :**
- Commits frequents apres chaque test passe
- TDD strict (test FAIL -> implementation -> test PASS -> commit)
- Pas d'emojis dans le code/commits
- Pas de references AI dans les commits

---

## Phase 1 — Setup du projet

### Task 1 : Creation `pyproject.toml`

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.pre-commit-config.yaml`
- Create: `src/xpath_detector/__init__.py`

**Step 1 : Creer le pyproject.toml**

```toml
[project]
name = "xpath-detector"
version = "1.0.0"
description = "Interactive XPath capture tool for web applications"
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.40",
    "rich>=13.0",
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "pytest-playwright>=0.4",
    "ruff>=0.4",
    "black>=24.0",
    "pre-commit>=3.0",
]

[project.scripts]
xpath-detector = "xpath_detector.__main__:main"

[project.entry-points."xpath_detector.exporters"]
json = "xpath_detector.exporters.json_exp:JsonExporter"
html = "xpath_detector.exporters.html_exp:HtmlExporter"
robot = "xpath_detector.exporters.robot_exp:RobotExporter"
java = "xpath_detector.exporters.java_exp:JavaExporter"
python = "xpath_detector.exporters.python_exp:PythonExporter"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/xpath_detector"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.pytest.ini_options]
addopts = "--cov=xpath_detector --cov-report=term-missing -v"
testpaths = ["tests"]
```

**Step 2 : Creer `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.coverage
.coverage.*
htmlcov/
dist/
build/
*.egg-info/
.venv/
venv/
sessions/
exports/
*.log
.ruff_cache/
.idea/
.vscode/
```

**Step 3 : Creer `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/psf/black
    rev: 24.0.0
    hooks:
      - id: black
```

**Step 4 : Creer le package vide**

```python
# src/xpath_detector/__init__.py
"""xpath-detector - interactive XPath capture tool."""
__version__ = "1.0.0"
```

**Step 5 : Commit**

```bash
git add pyproject.toml .gitignore .pre-commit-config.yaml src/xpath_detector/__init__.py
git commit -m "chore: bootstrap package structure"
```

---

### Task 2 : Installation et venv

**Step 1 : Creer venv et installer**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

**Step 2 : Verifier l'install**

```bash
python -c "import xpath_detector; print(xpath_detector.__version__)"
# Attendu : 1.0.0
pytest --version
# Attendu : pytest 8.x.x
playwright --version
# Attendu : Version 1.4x.x
```

**Step 3 : Commit (pas de nouveau fichier)**

Aucun commit (juste installation locale).

---

## Phase 2 — Modeles de donnees

### Task 3 : `models.py` - TDD

**Files:**
- Test: `tests/test_models.py`
- Create: `src/xpath_detector/models.py`

**Step 1 : Ecrire les tests**

```python
# tests/test_models.py
import json
from datetime import datetime

from xpath_detector.models import Element, Screen, Session, XPathCandidate


def test_xpathcandidate_immutable():
    candidate = XPathCandidate(strategy="by_id", expression="//input[@id='a']", stability_score=95)
    assert candidate.strategy == "by_id"
    assert candidate.stability_score == 95


def test_element_to_dict():
    element = Element(
        tag="input",
        text=None,
        attributes={"id": "login"},
        xpaths=[XPathCandidate("by_id", "//input[@id='login']", 95)],
        is_visible=True,
        is_enabled=True,
        description="Login field",
    )
    data = element.to_dict()
    assert data["tag"] == "input"
    assert data["attributes"]["id"] == "login"
    assert data["xpaths"][0]["strategy"] == "by_id"


def test_session_round_trip_json():
    session = Session(id="test_001", screens={})
    screen = Screen(
        name="login",
        url="https://x.fr",
        title="Login",
        timestamp=datetime(2026, 5, 12, 10, 0, 0),
        elements=[],
    )
    session.screens["login"] = screen

    data = session.to_dict()
    json_str = json.dumps(data)
    restored = Session.from_dict(json.loads(json_str))
    assert restored.id == "test_001"
    assert "login" in restored.screens
    assert restored.screens["login"].url == "https://x.fr"
```

**Step 2 : Run test (doit echouer)**

```bash
pytest tests/test_models.py -v
# Attendu : ImportError sur xpath_detector.models
```

**Step 3 : Implementer `models.py`**

```python
# src/xpath_detector/models.py
"""Immutable data model for sessions, screens, elements, xpaths."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class XPathCandidate:
    strategy: str
    expression: str
    stability_score: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "expression": self.expression,
            "stability_score": self.stability_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> XPathCandidate:
        return cls(**data)


@dataclass
class Element:
    tag: str
    text: str | None
    attributes: dict[str, str]
    xpaths: list[XPathCandidate]
    is_visible: bool
    is_enabled: bool
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag": self.tag,
            "text": self.text,
            "attributes": dict(self.attributes),
            "xpaths": [x.to_dict() for x in self.xpaths],
            "is_visible": self.is_visible,
            "is_enabled": self.is_enabled,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Element:
        return cls(
            tag=data["tag"],
            text=data.get("text"),
            attributes=dict(data.get("attributes", {})),
            xpaths=[XPathCandidate.from_dict(x) for x in data.get("xpaths", [])],
            is_visible=data.get("is_visible", True),
            is_enabled=data.get("is_enabled", True),
            description=data.get("description", ""),
        )


@dataclass
class Screen:
    name: str
    url: str
    title: str
    timestamp: datetime
    elements: list[Element] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp.isoformat(),
            "elements": [e.to_dict() for e in self.elements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Screen:
        return cls(
            name=data["name"],
            url=data["url"],
            title=data["title"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            elements=[Element.from_dict(e) for e in data.get("elements", [])],
        )


@dataclass
class Session:
    id: str
    screens: dict[str, Screen] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "screens": {name: screen.to_dict() for name, screen in self.screens.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        return cls(
            id=data["id"],
            screens={name: Screen.from_dict(s) for name, s in data.get("screens", {}).items()},
        )
```

**Step 4 : Run tests (doivent passer)**

```bash
pytest tests/test_models.py -v
# Attendu : 3 passed
```

**Step 5 : Commit**

```bash
git add tests/test_models.py src/xpath_detector/models.py
git commit -m "feat(models): add immutable data model with JSON round-trip"
```

---

## Phase 3 — Analyzer (generation des xpath)

### Task 4 : `analyzer.py` - strategy by_id

**Files:**
- Test: `tests/test_analyzer.py`
- Create: `src/xpath_detector/analyzer.py`

**Step 1 : Test by_id**

```python
# tests/test_analyzer.py
from xpath_detector.analyzer import escape_xpath_literal, generate_candidates
from xpath_detector.models import XPathCandidate


def test_generate_by_id():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={"id": "login", "type": "text"},
    )
    by_id = next(c for c in candidates if c.strategy == "by_id")
    assert by_id.expression == "//input[@id='login']"
    assert by_id.stability_score == 95


def test_escape_xpath_simple():
    assert escape_xpath_literal("hello") == "'hello'"


def test_escape_xpath_with_apostrophe():
    # "L'utilisateur" -> concat('L', "'", 'utilisateur')
    result = escape_xpath_literal("L'utilisateur")
    assert result == "concat('L', \"'\", 'utilisateur')"
```

**Step 2 : Run (echec)**

```bash
pytest tests/test_analyzer.py -v
# Attendu : ImportError
```

**Step 3 : Implementer minimal**

```python
# src/xpath_detector/analyzer.py
"""XPath candidate generation with stability scoring."""
from __future__ import annotations

from xpath_detector.models import XPathCandidate


def escape_xpath_literal(value: str) -> str:
    """Echappe une chaine pour usage dans un xpath."""
    if "'" not in value:
        return f"'{value}'"
    parts = value.split("'")
    quoted = [f"'{p}'" for p in parts]
    return "concat(" + ", \"'\", ".join(quoted) + ")"


def generate_candidates(
    tag: str,
    text: str | None,
    attributes: dict[str, str],
) -> list[XPathCandidate]:
    """Genere une liste de candidats xpath tries par score decroissant."""
    candidates: list[XPathCandidate] = []

    if "id" in attributes and attributes["id"]:
        candidates.append(
            XPathCandidate(
                strategy="by_id",
                expression=f"//{tag}[@id='{attributes['id']}']",
                stability_score=95,
            )
        )

    candidates.sort(key=lambda c: -c.stability_score)
    return candidates
```

**Step 4 : Run (passe)**

```bash
pytest tests/test_analyzer.py -v
# Attendu : 3 passed
```

**Step 5 : Commit**

```bash
git add tests/test_analyzer.py src/xpath_detector/analyzer.py
git commit -m "feat(analyzer): add by_id strategy and xpath literal escaping"
```

---

### Task 5 : Analyzer - data-testid, name, aria-label

**Files:**
- Modify: `tests/test_analyzer.py`
- Modify: `src/xpath_detector/analyzer.py`

**Step 1 : Ajouter les tests**

```python
def test_generate_by_data_testid():
    candidates = generate_candidates(tag="button", text=None, attributes={"data-testid": "submit"})
    cand = next(c for c in candidates if c.strategy == "by_data_testid")
    assert cand.expression == "//button[@data-testid='submit']"
    assert cand.stability_score == 90


def test_generate_by_name():
    candidates = generate_candidates(tag="input", text=None, attributes={"name": "username"})
    cand = next(c for c in candidates if c.strategy == "by_name")
    assert cand.expression == "//input[@name='username']"
    assert cand.stability_score == 80


def test_generate_by_aria_label():
    candidates = generate_candidates(tag="button", text=None, attributes={"aria-label": "Close"})
    cand = next(c for c in candidates if c.strategy == "by_aria_label")
    assert cand.expression == "//button[@aria-label='Close']"
    assert cand.stability_score == 75
```

**Step 2 : Run (echec)**

```bash
pytest tests/test_analyzer.py -v
```

**Step 3 : Etendre `generate_candidates`**

Apres le bloc `by_id`, ajouter :

```python
    for attr, strategy, score in [
        ("data-testid", "by_data_testid", 90),
        ("name", "by_name", 80),
        ("aria-label", "by_aria_label", 75),
    ]:
        if attr in attributes and attributes[attr]:
            candidates.append(
                XPathCandidate(
                    strategy=strategy,
                    expression=f"//{tag}[@{attr}='{attributes[attr]}']",
                    stability_score=score,
                )
            )
```

**Step 4 : Run (passe)**

```bash
pytest tests/test_analyzer.py -v
```

**Step 5 : Commit**

```bash
git add tests/test_analyzer.py src/xpath_detector/analyzer.py
git commit -m "feat(analyzer): add by_data_testid, by_name, by_aria_label strategies"
```

---

### Task 6 : Analyzer - by_text avec escape

**Step 1 : Tests**

```python
def test_generate_by_text():
    candidates = generate_candidates(tag="a", text="Valider", attributes={})
    cand = next(c for c in candidates if c.strategy == "by_text")
    assert cand.expression == "//a[contains(.,'Valider')]"
    assert cand.stability_score == 70


def test_by_text_escapes_apostrophe():
    candidates = generate_candidates(tag="a", text="L'utilisateur", attributes={})
    cand = next(c for c in candidates if c.strategy == "by_text")
    assert "concat(" in cand.expression


def test_by_text_skipped_if_too_long():
    long_text = "a" * 80
    candidates = generate_candidates(tag="div", text=long_text, attributes={})
    assert not any(c.strategy == "by_text" for c in candidates)


def test_by_text_skipped_if_empty():
    candidates = generate_candidates(tag="div", text="", attributes={})
    assert not any(c.strategy == "by_text" for c in candidates)
```

**Step 2 : Run, Step 3 : Implementer**

Ajouter dans `generate_candidates` :

```python
    if text and 0 < len(text) < 50:
        candidates.append(
            XPathCandidate(
                strategy="by_text",
                expression=f"//{tag}[contains(.,{escape_xpath_literal(text)})]",
                stability_score=70,
            )
        )
```

**Step 4-5 : Run + Commit**

```bash
git commit -m "feat(analyzer): add by_text strategy with apostrophe escaping"
```

---

### Task 7 : Analyzer - by_class, absolute, scoring

**Step 1 : Tests**

```python
def test_generate_by_class():
    candidates = generate_candidates(tag="button", text=None, attributes={"class": "btn-primary"})
    cand = next(c for c in candidates if c.strategy == "by_class")
    assert "contains(@class,'btn-primary')" in cand.expression
    assert cand.stability_score == 60


def test_generate_absolute_fallback():
    # Element sans aucun attribut stable
    candidates = generate_candidates(tag="div", text=None, attributes={}, absolute_xpath="/html/body/div[3]")
    cand = next(c for c in candidates if c.strategy == "absolute")
    assert cand.expression == "/html/body/div[3]"
    assert cand.stability_score == 10


def test_candidates_sorted_by_score_desc():
    candidates = generate_candidates(
        tag="input",
        text="Login",
        attributes={"id": "x", "name": "y", "class": "z"},
    )
    scores = [c.stability_score for c in candidates]
    assert scores == sorted(scores, reverse=True)
```

**Step 2-3 : Etendre**

```python
def generate_candidates(
    tag: str,
    text: str | None,
    attributes: dict[str, str],
    absolute_xpath: str | None = None,
) -> list[XPathCandidate]:
    candidates: list[XPathCandidate] = []
    # ... bloc by_id, by_data_testid, etc. ...

    if "class" in attributes and attributes["class"]:
        classes = attributes["class"].split()
        if classes:
            first_class = classes[0]
            candidates.append(
                XPathCandidate(
                    strategy="by_class",
                    expression=f"//{tag}[contains(@class,'{first_class}')]",
                    stability_score=60,
                )
            )

    if absolute_xpath:
        candidates.append(
            XPathCandidate(
                strategy="absolute",
                expression=absolute_xpath,
                stability_score=10,
            )
        )

    candidates.sort(key=lambda c: -c.stability_score)
    return candidates
```

**Step 4-5 : Run + Commit**

```bash
git commit -m "feat(analyzer): add by_class, absolute fallback, ensure score sorting"
```

---

## Phase 4 — Persistance (Session save/load)

### Task 8 : `session.py` - save/load

**Files:**
- Test: `tests/test_session.py`
- Create: `src/xpath_detector/session.py`

**Step 1 : Tests**

```python
# tests/test_session.py
import json
from pathlib import Path

import pytest

from xpath_detector.models import Session
from xpath_detector.session import load_session, save_session


def test_save_session_writes_json(tmp_path: Path):
    session = Session(id="test", screens={})
    path = tmp_path / "session.json"
    save_session(session, path)
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["id"] == "test"


def test_load_session_reads_json(tmp_path: Path):
    path = tmp_path / "session.json"
    path.write_text(json.dumps({"id": "loaded", "screens": {}}))
    session = load_session(path)
    assert session.id == "loaded"


def test_load_nonexistent_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_session(tmp_path / "missing.json")
```

**Step 2 : Run (echec)**

**Step 3 : Implementer**

```python
# src/xpath_detector/session.py
"""Session persistence (save/load JSON)."""
from __future__ import annotations

import json
from pathlib import Path

from xpath_detector.models import Session


def save_session(session: Session, path: Path) -> None:
    """Sauvegarde une session dans un fichier JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def load_session(path: Path) -> Session:
    """Charge une session depuis un fichier JSON."""
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return Session.from_dict(data)
```

**Step 4-5 : Run + Commit**

```bash
git commit -m "feat(session): add save/load JSON persistence"
```

---

## Phase 5 — Exporters (plugin-based)

### Task 9 : Exporter ABC

**Files:**
- Test: `tests/test_exporters.py`
- Create: `src/xpath_detector/exporters/__init__.py`
- Create: `src/xpath_detector/exporters/base.py`

**Step 1 : Test**

```python
# tests/test_exporters.py
import pytest

from xpath_detector.exporters.base import Exporter


def test_exporter_is_abstract():
    with pytest.raises(TypeError):
        Exporter()
```

**Step 2-3 : Implementer**

```python
# src/xpath_detector/exporters/__init__.py
"""Plugin-based exporters."""

# src/xpath_detector/exporters/base.py
"""Abstract exporter base class."""
from abc import ABC, abstractmethod
from pathlib import Path

from xpath_detector.models import Session


class Exporter(ABC):
    name: str = ""
    extension: str = ""

    @abstractmethod
    def export(self, session: Session, output_dir: Path) -> Path:
        """Genere les fichiers d'export et retourne le chemin du fichier/dossier principal."""
        raise NotImplementedError
```

**Step 4-5 : Run + Commit**

```bash
git commit -m "feat(exporters): add abstract Exporter base class"
```

---

### Task 10 : JsonExporter

**Files:**
- Modify: `tests/test_exporters.py`
- Create: `src/xpath_detector/exporters/json_exp.py`

**Step 1 : Test**

```python
import json
from datetime import datetime
from pathlib import Path

from xpath_detector.exporters.json_exp import JsonExporter
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
    exporter = JsonExporter()
    out = exporter.export(_sample_session(), tmp_path)
    assert out.suffix == ".json"
    data = json.loads(out.read_text())
    assert data["id"] == "20260512_120000"
    assert "login" in data["screens"]
```

**Step 2-3 : Implementer**

```python
# src/xpath_detector/exporters/json_exp.py
"""JSON exporter."""
import json
from pathlib import Path

from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Session


class JsonExporter(Exporter):
    name = "json"
    extension = ".json"

    def export(self, session: Session, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"session_{session.id}.json"
        path.write_text(
            json.dumps(session.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path
```

**Step 4-5 : Run + Commit**

```bash
git commit -m "feat(exporters): add JsonExporter"
```

---

### Task 11 : RobotExporter

**Files:**
- Modify: `tests/test_exporters.py`
- Create: `src/xpath_detector/exporters/robot_exp.py`

**Step 1 : Test**

```python
def test_robot_exporter_writes_resource_per_screen(tmp_path: Path):
    from xpath_detector.exporters.robot_exp import RobotExporter

    out = RobotExporter().export(_sample_session(), tmp_path)
    # Structure : out/login/locators.resource
    resource = out / "login" / "locators.resource"
    assert resource.exists()
    content = resource.read_text()
    assert "*** Variables ***" in content
    assert "//input[@id='_login']" in content
```

**Step 2-3 : Implementer**

```python
# src/xpath_detector/exporters/robot_exp.py
"""Robot Framework .resource exporter."""
import re
from pathlib import Path

from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Element, Session


class RobotExporter(Exporter):
    name = "robot"
    extension = ".resource"

    def export(self, session: Session, output_dir: Path) -> Path:
        base = output_dir / f"robot_{session.id}"
        base.mkdir(parents=True, exist_ok=True)

        for screen_name, screen in session.screens.items():
            folder = base / _sanitize(screen_name)
            folder.mkdir(parents=True, exist_ok=True)
            resource = folder / "locators.resource"
            content = self._render(screen.name, screen.elements)
            resource.write_text(content, encoding="utf-8")

        return base

    def _render(self, screen_name: str, elements: list[Element]) -> str:
        lines = [
            "*** Settings ***",
            f"Documentation Locators for screen: {screen_name}",
            "",
            "*** Variables ***",
        ]
        for el in elements:
            if not el.xpaths:
                continue
            best = el.xpaths[0]
            var = _to_var_name(el)
            lines.append(f"${{{var}}}    {best.expression}")
        return "\n".join(lines) + "\n"


def _sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", name)[:50]


def _to_var_name(element: Element) -> str:
    base = element.description or element.text or element.attributes.get("name") or element.tag
    return _sanitize(base).upper()[:30]
```

**Step 4-5 : Run + Commit**

```bash
git commit -m "feat(exporters): add RobotExporter (one .resource per screen)"
```

---

### Task 12 : JavaExporter

**Files:**
- Modify: `tests/test_exporters.py`
- Create: `src/xpath_detector/exporters/java_exp.py`

**Step 1 : Test**

```python
def test_java_exporter_generates_locators_class(tmp_path: Path):
    from xpath_detector.exporters.java_exp import JavaExporter

    out = JavaExporter().export(_sample_session(), tmp_path)
    java_file = out / "Locators.java"
    content = java_file.read_text()
    assert "public final class Locators" in content
    assert "public static final class Login" in content
    assert "By.xpath(\"//input[@id='_login']\")" in content
```

**Step 2-3 : Implementer**

```python
# src/xpath_detector/exporters/java_exp.py
"""Java Selenium Locators class exporter."""
import re
from pathlib import Path

from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Element, Screen, Session


class JavaExporter(Exporter):
    name = "java"
    extension = ".java"

    def export(self, session: Session, output_dir: Path) -> Path:
        base = output_dir / f"java_{session.id}"
        base.mkdir(parents=True, exist_ok=True)
        java_file = base / "Locators.java"
        java_file.write_text(self._render(session), encoding="utf-8")
        return base

    def _render(self, session: Session) -> str:
        lines = [
            "import org.openqa.selenium.By;",
            "",
            "public final class Locators {",
            "    private Locators() {}",
            "",
        ]
        for screen_name, screen in session.screens.items():
            class_name = _to_pascal(screen_name)
            lines.append(f"    public static final class {class_name} {{")
            lines.append(f"        private {class_name}() {{}}")
            for el in screen.elements:
                if not el.xpaths:
                    continue
                best = el.xpaths[0]
                var = _to_constant(el)
                escaped = best.expression.replace('"', '\\"')
                lines.append(f'        public static final By {var} = By.xpath("{escaped}");')
            lines.append("    }")
            lines.append("")
        lines.append("}")
        return "\n".join(lines) + "\n"


def _to_pascal(name: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", name)
    return "".join(p.capitalize() for p in parts if p) or "Screen"


def _to_constant(element: Element) -> str:
    base = element.description or element.text or element.attributes.get("name") or element.tag
    return re.sub(r"[^A-Za-z0-9_]", "_", base).upper().strip("_")[:40] or "ELEMENT"
```

**Step 4-5 : Run + Commit**

```bash
git commit -m "feat(exporters): add JavaExporter for Selenium Locators class"
```

---

### Task 13 : PythonExporter

**Step 1 : Test**

```python
def test_python_exporter_generates_module(tmp_path: Path):
    from xpath_detector.exporters.python_exp import PythonExporter

    out = PythonExporter().export(_sample_session(), tmp_path)
    py_file = out / "locators.py"
    content = py_file.read_text()
    assert "from selenium.webdriver.common.by import By" in content
    assert "class Login:" in content
    assert "(By.XPATH, \"//input[@id='_login']\")" in content
```

**Step 2-3 : Implementer**

```python
# src/xpath_detector/exporters/python_exp.py
"""Python Selenium locators module exporter."""
import re
from pathlib import Path

from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Element, Session


class PythonExporter(Exporter):
    name = "python"
    extension = ".py"

    def export(self, session: Session, output_dir: Path) -> Path:
        base = output_dir / f"python_{session.id}"
        base.mkdir(parents=True, exist_ok=True)
        py_file = base / "locators.py"
        py_file.write_text(self._render(session), encoding="utf-8")
        return base

    def _render(self, session: Session) -> str:
        lines = [
            '"""Auto-generated Selenium locators."""',
            "from selenium.webdriver.common.by import By",
            "",
        ]
        for screen_name, screen in session.screens.items():
            class_name = _to_pascal(screen_name)
            lines.append(f"class {class_name}:")
            has_any = False
            for el in screen.elements:
                if not el.xpaths:
                    continue
                best = el.xpaths[0]
                var = _to_constant(el)
                escaped = best.expression.replace('"', '\\"')
                lines.append(f'    {var} = (By.XPATH, "{escaped}")')
                has_any = True
            if not has_any:
                lines.append("    pass")
            lines.append("")
        return "\n".join(lines) + "\n"


def _to_pascal(name: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", name)
    return "".join(p.capitalize() for p in parts if p) or "Screen"


def _to_constant(element: Element) -> str:
    base = element.description or element.text or element.attributes.get("name") or element.tag
    return re.sub(r"[^A-Za-z0-9_]", "_", base).upper().strip("_")[:40] or "ELEMENT"
```

**Step 4-5 : Commit**

```bash
git commit -m "feat(exporters): add PythonExporter for Selenium locators"
```

---

### Task 14 : HtmlExporter (avec html.escape)

**Step 1 : Test**

```python
def test_html_exporter_escapes_user_content(tmp_path: Path):
    from xpath_detector.exporters.html_exp import HtmlExporter

    session = _sample_session()
    # Injecter du contenu malicieux
    session.screens["login"].elements[0].description = "<script>alert(1)</script>"

    out = HtmlExporter().export(session, tmp_path)
    html_file = out
    content = html_file.read_text()
    # Pas de script execute
    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;" in content


def test_html_exporter_contains_session_info(tmp_path: Path):
    from xpath_detector.exporters.html_exp import HtmlExporter

    out = HtmlExporter().export(_sample_session(), tmp_path)
    content = out.read_text()
    assert "20260512_120000" in content
    assert "login" in content
```

**Step 2-3 : Implementer**

```python
# src/xpath_detector/exporters/html_exp.py
"""HTML report exporter with proper escaping."""
from html import escape
from pathlib import Path

from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Session


class HtmlExporter(Exporter):
    name = "html"
    extension = ".html"

    def export(self, session: Session, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"report_{session.id}.html"
        path.write_text(self._render(session), encoding="utf-8")
        return path

    def _render(self, session: Session) -> str:
        screens_html = []
        for name, screen in session.screens.items():
            elements_html = []
            for el in screen.elements:
                xpaths = "".join(
                    f"<li><code>{escape(c.expression)}</code> "
                    f"<small>({escape(c.strategy)}, score: {c.stability_score})</small></li>"
                    for c in el.xpaths
                )
                elements_html.append(
                    f"<div class='element'>"
                    f"<h3>{escape(el.description or el.tag)}</h3>"
                    f"<p><strong>Tag:</strong> {escape(el.tag)}</p>"
                    f"<ul>{xpaths}</ul>"
                    f"</div>"
                )
            screens_html.append(
                f"<section><h2>{escape(name)}</h2>"
                f"<p>URL: <code>{escape(screen.url)}</code></p>"
                + "".join(elements_html)
                + "</section>"
            )

        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>xpath-detector report — {escape(session.id)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 1000px; }}
section {{ border: 1px solid #ddd; padding: 1rem; margin: 1rem 0; border-radius: 8px; }}
.element {{ background: #f7f7f7; padding: 0.5rem; margin: 0.5rem 0; border-radius: 4px; }}
code {{ background: #eaeaea; padding: 2px 4px; border-radius: 3px; word-break: break-all; }}
</style>
</head>
<body>
<h1>xpath-detector report</h1>
<p>Session: <code>{escape(session.id)}</code></p>
{"".join(screens_html)}
</body>
</html>
"""
```

**Step 4-5 : Commit**

```bash
git commit -m "feat(exporters): add HtmlExporter with proper HTML escaping"
```

---

## Phase 6 — Browser + Overlay

### Task 15 : `overlay.py` - script JS embedded

**Files:**
- Create: `src/xpath_detector/overlay.py`
- Test: `tests/test_overlay.py`

**Step 1 : Test (structural)**

```python
# tests/test_overlay.py
from xpath_detector.overlay import OVERLAY_JS


def test_overlay_js_is_non_empty():
    assert len(OVERLAY_JS) > 100


def test_overlay_js_contains_capture_marker():
    assert "__XPATH_CAPTURE__" in OVERLAY_JS


def test_overlay_js_listens_to_ctrl_click():
    assert "ctrlKey" in OVERLAY_JS or "metaKey" in OVERLAY_JS
```

**Step 2-3 : Implementer**

```python
# src/xpath_detector/overlay.py
"""JavaScript overlay injected in the page for click capture."""

OVERLAY_JS = r"""
(function () {
    if (window.__xpath_detector_installed) return;
    window.__xpath_detector_installed = true;

    const style = document.createElement('style');
    style.textContent = `
        .__xpath_detector_highlight {
            outline: 2px solid red !important;
            outline-offset: 2px !important;
            cursor: crosshair !important;
        }
        .__xpath_detector_tooltip {
            position: fixed;
            background: #222;
            color: #fff;
            padding: 4px 8px;
            font: 12px monospace;
            border-radius: 4px;
            pointer-events: none;
            z-index: 2147483647;
        }
    `;
    document.head.appendChild(style);

    let current = null;
    let tooltip = null;
    let active = true;

    function showTooltip(text, x, y) {
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.className = '__xpath_detector_tooltip';
            document.body.appendChild(tooltip);
        }
        tooltip.textContent = text;
        tooltip.style.left = (x + 10) + 'px';
        tooltip.style.top = (y + 10) + 'px';
    }

    function hideTooltip() {
        if (tooltip) tooltip.style.display = 'none';
    }

    document.addEventListener('mousemove', (e) => {
        if (!active) return;
        const el = document.elementFromPoint(e.clientX, e.clientY);
        if (!el || el === current) return;
        if (current) current.classList.remove('__xpath_detector_highlight');
        current = el;
        current.classList.add('__xpath_detector_highlight');
        if (tooltip) tooltip.style.display = 'block';
        showTooltip(el.tagName.toLowerCase() + (el.id ? '#' + el.id : ''), e.clientX, e.clientY);
    }, true);

    document.addEventListener('click', (e) => {
        if (!active) return;
        if (!(e.ctrlKey || e.metaKey)) return;
        e.preventDefault();
        e.stopPropagation();
        const el = e.target;
        const attrs = {};
        for (const a of el.attributes) attrs[a.name] = a.value;
        const data = {
            tag: el.tagName.toLowerCase(),
            text: (el.textContent || '').trim().slice(0, 200),
            attributes: attrs,
            absolute_xpath: getAbsoluteXPath(el),
            is_visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
            is_enabled: !el.disabled,
        };
        console.log('__XPATH_CAPTURE__' + JSON.stringify(data));
    }, true);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            active = !active;
            if (!active && current) current.classList.remove('__xpath_detector_highlight');
            hideTooltip();
        }
    });

    function getAbsoluteXPath(el) {
        if (el.id) return '//*[@id="' + el.id + '"]';
        if (el === document.body) return '/html/body';
        let ix = 0;
        const siblings = el.parentNode ? el.parentNode.childNodes : [];
        for (const sibling of siblings) {
            if (sibling === el) {
                return getAbsoluteXPath(el.parentNode) + '/' + el.tagName.toLowerCase() + '[' + (ix + 1) + ']';
            }
            if (sibling.nodeType === 1 && sibling.tagName === el.tagName) ix++;
        }
        return '';
    }
})();
"""
```

**Step 4-5 : Commit**

```bash
git commit -m "feat(overlay): add JS overlay for hover highlight and Ctrl+click capture"
```

---

### Task 16 : `browser.py` - Playwright wrapper

**Files:**
- Create: `src/xpath_detector/browser.py`
- Test: `tests/test_browser.py` (smoke test seulement)

**Step 1 : Test smoke**

```python
# tests/test_browser.py
import pytest

playwright = pytest.importorskip("playwright.sync_api")


def test_browser_can_be_constructed():
    from xpath_detector.browser import BrowserController

    ctrl = BrowserController()
    assert ctrl is not None
```

**Step 2-3 : Implementer**

```python
# src/xpath_detector/browser.py
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
```

**Step 4-5 : Commit**

```bash
git commit -m "feat(browser): add Playwright sync wrapper with overlay injection"
```

---

## Phase 7 — Shell interactif

### Task 17 : `shell.py` - parser de commandes

**Files:**
- Test: `tests/test_shell_parser.py`
- Create: `src/xpath_detector/shell.py` (parser uniquement dans cette task)

**Step 1 : Tests**

```python
# tests/test_shell_parser.py
from xpath_detector.shell import parse_command


def test_parse_simple_command():
    assert parse_command("list") == ("list", [])


def test_parse_command_with_args():
    assert parse_command("open https://x.fr") == ("open", ["https://x.fr"])


def test_parse_command_strips_whitespace():
    assert parse_command("  list  ") == ("list", [])


def test_parse_empty_returns_empty_command():
    assert parse_command("") == ("", [])
```

**Step 2-3 : Implementer**

```python
# src/xpath_detector/shell.py
"""Interactive shell."""
from __future__ import annotations


def parse_command(line: str) -> tuple[str, list[str]]:
    """Parse une ligne de commande en (commande, args)."""
    parts = line.strip().split()
    if not parts:
        return ("", [])
    return (parts[0], parts[1:])
```

**Step 4-5 : Commit**

```bash
git commit -m "feat(shell): add command parser"
```

---

### Task 18 : `shell.py` - boucle interactive

**Files:**
- Modify: `src/xpath_detector/shell.py`
- Test: integration manuelle

**Step 1 : Pas de test unitaire (UI)**

**Step 2 : Implementer**

```python
# src/xpath_detector/shell.py (etendu)
from __future__ import annotations

import logging
from datetime import datetime
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from xpath_detector.analyzer import generate_candidates
from xpath_detector.browser import BrowserController
from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Element, Screen, Session
from xpath_detector.session import load_session, save_session

LOGGER = logging.getLogger(__name__)
SESSIONS_DIR = Path("sessions")
EXPORTS_DIR = Path("exports")


def parse_command(line: str) -> tuple[str, list[str]]:
    parts = line.strip().split()
    if not parts:
        return ("", [])
    return (parts[0], parts[1:])


def _load_exporters() -> dict[str, Exporter]:
    result: dict[str, Exporter] = {}
    for ep in entry_points(group="xpath_detector.exporters"):
        cls = ep.load()
        result[ep.name] = cls()
    return result


class Shell:
    def __init__(self) -> None:
        self.console = Console()
        self.session = Session(id=datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.current_screen: str | None = None
        self.browser = BrowserController()
        self.exporters = _load_exporters()
        self.running = True
        self.browser.on_capture(self._on_capture)

    def run(self) -> None:
        self.browser.start()
        self.console.print("[bold green]xpath-detector started.[/bold green]")
        self.console.print("Commands: open <url>, screen <name>, list, show, export <format>, save, quit")

        while self.running:
            try:
                line = self.console.input("[cyan]> [/cyan]")
            except (EOFError, KeyboardInterrupt):
                self.running = False
                break
            cmd, args = parse_command(line)
            if not cmd:
                continue
            handler = getattr(self, f"cmd_{cmd}", None)
            if handler is None:
                self.console.print(f"[red]Unknown command: {cmd}[/red]")
                continue
            try:
                handler(args)
            except Exception as e:
                LOGGER.exception("Command failed")
                self.console.print(f"[red]Error: {e}[/red]")

        self.browser.stop()

    def cmd_open(self, args: list[str]) -> None:
        if not args:
            self.console.print("[red]Usage: open <url>[/red]")
            return
        url = args[0]
        self.browser.open(url)
        self.console.print(f"[green]Opened {url}[/green]")

    def cmd_screen(self, args: list[str]) -> None:
        if not args:
            self.console.print("[red]Usage: screen <name>[/red]")
            return
        name = args[0]
        if name not in self.session.screens:
            self.session.screens[name] = Screen(
                name=name,
                url=self.browser.current_url(),
                title=self.browser.current_title(),
                timestamp=datetime.now(),
            )
            self.console.print(f"[green]Created screen '{name}'[/green]")
        self.current_screen = name
        self.console.print(f"[cyan]Current screen: {name}[/cyan]")

    def cmd_list(self, args: list[str]) -> None:
        table = Table(title="Screens")
        table.add_column("Name")
        table.add_column("Elements")
        table.add_column("URL")
        for name, screen in self.session.screens.items():
            marker = " (current)" if name == self.current_screen else ""
            table.add_row(name + marker, str(len(screen.elements)), screen.url)
        self.console.print(table)

    def cmd_show(self, args: list[str]) -> None:
        if not self.current_screen:
            self.console.print("[red]No current screen[/red]")
            return
        screen = self.session.screens[self.current_screen]
        for i, el in enumerate(screen.elements):
            xpath = el.xpaths[0].expression if el.xpaths else "-"
            self.console.print(f"[{i}] [yellow]{el.tag}[/yellow] {el.description} -> {xpath}")

    def cmd_export(self, args: list[str]) -> None:
        if not args:
            self.console.print(f"[red]Available: {', '.join(self.exporters)}[/red]")
            return
        target = args[0]
        EXPORTS_DIR.mkdir(exist_ok=True)
        if target == "all":
            for name, exporter in self.exporters.items():
                out = exporter.export(self.session, EXPORTS_DIR)
                self.console.print(f"[green]{name}[/green] -> {out}")
            return
        exporter = self.exporters.get(target)
        if exporter is None:
            self.console.print(f"[red]Unknown exporter: {target}[/red]")
            return
        out = exporter.export(self.session, EXPORTS_DIR)
        self.console.print(f"[green]Exported to {out}[/green]")

    def cmd_save(self, args: list[str]) -> None:
        SESSIONS_DIR.mkdir(exist_ok=True)
        path = SESSIONS_DIR / f"{self.session.id}.json"
        save_session(self.session, path)
        self.console.print(f"[green]Session saved: {path}[/green]")

    def cmd_load(self, args: list[str]) -> None:
        if not args:
            self.console.print("[red]Usage: load <path>[/red]")
            return
        self.session = load_session(Path(args[0]))
        self.console.print(f"[green]Loaded session {self.session.id}[/green]")

    def cmd_quit(self, args: list[str]) -> None:
        self.running = False

    def _on_capture(self, data: dict[str, Any]) -> None:
        if not self.current_screen:
            self.console.print("[yellow]No current screen, capture ignored. Use 'screen <name>' first.[/yellow]")
            return
        desc = self.console.input("[cyan]Description (Enter to skip): [/cyan]")
        xpaths = generate_candidates(
            tag=data["tag"],
            text=data.get("text"),
            attributes=data.get("attributes", {}),
            absolute_xpath=data.get("absolute_xpath"),
        )
        element = Element(
            tag=data["tag"],
            text=data.get("text"),
            attributes=data.get("attributes", {}),
            xpaths=xpaths,
            is_visible=data.get("is_visible", True),
            is_enabled=data.get("is_enabled", True),
            description=desc,
        )
        self.session.screens[self.current_screen].elements.append(element)
        best = xpaths[0].expression if xpaths else "-"
        self.console.print(f"[green]Captured {element.tag} -> {best}[/green]")
```

**Step 3 : Commit**

```bash
git commit -m "feat(shell): add interactive shell loop with command handlers"
```

---

## Phase 8 — Entry point + finalisation

### Task 19 : `__main__.py`

**Files:**
- Create: `src/xpath_detector/__main__.py`

**Step 1 : Implementer**

```python
# src/xpath_detector/__main__.py
"""Entry point for xpath-detector."""
import logging

from xpath_detector.shell import Shell


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename="xpath_detector.log",
    )
    Shell().run()


if __name__ == "__main__":
    main()
```

**Step 2 : Verifier**

```bash
python -m xpath_detector
# Doit lancer le shell (verifier visuellement) - taper "quit" pour sortir
```

**Step 3 : Commit**

```bash
git commit -m "feat: add main entry point"
```

---

### Task 20 : README + finalisation

**Files:**
- Create: `README.md`

**Step 1 : Ecrire le README**

```markdown
# xpath-detector

Outil interactif de capture XPath pour applications web.

## Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

## Usage

```bash
python -m xpath_detector
```

Commandes :
- `open <url>` — ouvre une URL
- `screen <name>` — cree/bascule sur un ecran
- `list` — liste les ecrans
- `show` — affiche les elements de l'ecran courant
- `export <format>` — exporte (json/html/robot/java/python/all)
- `save` — sauvegarde la session JSON
- `load <path>` — recharge une session
- `quit` — quitte

Dans le navigateur :
- **Survol** : surligne l'element en rouge
- **Ctrl+clic** : capture l'element
- **Escape** : active/desactive l'overlay

## Tests

```bash
pytest
```

## Architecture

Voir `docs/plans/2026-05-12-xpath-detector-redesign.md`.
```

**Step 2 : Commit**

```bash
git commit -m "docs: add README with installation and usage"
```

---

### Task 21 : Validation finale

**Step 1 : Lancer tous les tests**

```bash
pytest --cov=xpath_detector --cov-report=term-missing
# Verifier coverage > 70%
```

**Step 2 : Lint**

```bash
ruff check src/ tests/
black --check src/ tests/
```

**Step 3 : Test manuel end-to-end**

```bash
python -m xpath_detector
# > open https://example.com
# > screen home
# Ctrl+clic sur "More information..."
# Description : link more info
# > show
# > export all
# > save
# > quit
```

**Step 4 : Verifier que les exports existent**

```bash
ls exports/
# json/, html/, robot_*/, java_*/, python_*/
```

**Step 5 : Commit final**

```bash
git commit -m "chore: finalize v1.0.0 - rewrite with Playwright + plugin exporters"
git tag v1.0.0
```

---

## Recapitulatif

| # | Tache | Type | Duree |
|---|-------|------|-------|
| 1-2 | Setup + install | Setup | 15 min |
| 3 | models.py + tests | TDD | 30 min |
| 4-7 | analyzer.py + tests | TDD | 1h |
| 8 | session.py + tests | TDD | 20 min |
| 9-14 | exporters (6 fichiers) | TDD | 2h |
| 15-16 | overlay + browser | Code | 1h |
| 17-18 | shell | Code | 1h |
| 19-21 | entry point + README + validation | Wrap | 30 min |
| | **Total** | | **~6h30** |

**Coverage cible :** > 70% sur les modules `models`, `analyzer`, `session`, `exporters/*`.

Les modules `browser`, `overlay`, `shell` ne sont pas couverts par les tests unitaires (UI/I/O), validation manuelle en Task 21.
