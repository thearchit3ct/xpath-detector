# xpath-detector v1.1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adresser tous les items deferres de v1.0.0 review (I-1 a I-5, M-4, M-9, M-11) sans nouvelles features.

**Architecture:** Refactor incremental sur le code v1.0 existant. Nouveaux modules : `exporters/_naming.py` (DRY) et `scripts/migrate_v1.py` (migration JSON). Refactor de `overlay.py` (consistence target + label detection), `analyzer.py` (strategy by_label_neighbor), `shell.py` (cmd_help + tests).

**Tech Stack:** Python 3.11+, Playwright, pytest, ruff, black. Aucune nouvelle dependance.

**Conventions:** TDD strict, pas d'attribution AI, commits atomiques, branche `master`.

---

## Phase 1 — Fixes mineurs (M-9, M-11, M-4)

### Task 1 : M-9 Console logging

**Files:**
- Modify: `src/xpath_detector/__main__.py`

**Step 1: Modifier __main__.py**

Remplacer le contenu de `src/xpath_detector/__main__.py` :

```python
"""Entry point for xpath-detector."""

import logging
import sys

from xpath_detector.shell import Shell


def main() -> None:
    file_handler = logging.FileHandler("xpath_detector.log")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[file_handler, console_handler],
    )
    Shell().run()


if __name__ == "__main__":
    main()
```

**Step 2: Verifier que python -c "import xpath_detector.__main__" ne crashe pas**

```bash
cd /Users/nitch/projects/git_projets/xpath_detector
source .venv/bin/activate
python -c "from xpath_detector.__main__ import main; print('ok')"
```

Expected: `ok`

**Step 3: Commit**

```bash
git add src/xpath_detector/__main__.py
git commit -m "feat(logging): add stderr console handler for WARNING+ messages"
```

---

### Task 2 : M-11 Escape edge cases (TDD)

**Files:**
- Modify: `tests/test_analyzer.py`

**Step 1: Ajouter les tests d'edge case**

Append a la fin de `tests/test_analyzer.py`:

```python
def test_escape_xpath_empty_string():
    assert escape_xpath_literal("") == "''"


def test_escape_xpath_only_apostrophe():
    # "'" devient concat('', "'", '')
    result = escape_xpath_literal("'")
    assert result == "concat('', \"'\", '')"


def test_escape_xpath_wrapped_with_apostrophes():
    # "'x'" devient concat('', "'", 'x', "'", '')
    result = escape_xpath_literal("'x'")
    assert result == "concat('', \"'\", 'x', \"'\", '')"


def test_escape_xpath_consecutive_apostrophes():
    # "x''y" devient concat('x', "'", '', "'", 'y')
    result = escape_xpath_literal("x''y")
    assert result == "concat('x', \"'\", '', \"'\", 'y')"
```

**Step 2: Run tests**

```bash
pytest tests/test_analyzer.py -v
```

Expected: 17 passed (13 existants + 4 nouveaux). Si fail sur empty string, c'est attendu — passer a Step 3.

**Step 3: Si Step 2 echoue, fix `escape_xpath_literal` dans analyzer.py**

L'implementation actuelle fait `if "'" not in value: return f"'{value}'"`. Si value est `""`, ca retourne `"''"`. Verifier que c'est bien le cas.

Pour `"'"`, le split donne `["", ""]`, quoted devient `["''", "''"]`, join avec `", \"'\", "` donne `"'', \"'\", ''"`. Le resultat final est `"concat('', \"'\", '')"`. OK.

L'implementation devrait deja gerer tous les cas. Si un test echoue, c'est juste un probleme de format de la chaine attendue dans le test, ajuster.

**Step 4: Commit**

```bash
git add tests/test_analyzer.py
git commit -m "test(analyzer): add escape_xpath_literal edge case tests"
```

---

### Task 3 : M-4 DRY exporters - extraction _naming.py

**Files:**
- Create: `src/xpath_detector/exporters/_naming.py`
- Modify: `src/xpath_detector/exporters/robot_exp.py`
- Modify: `src/xpath_detector/exporters/java_exp.py`
- Modify: `src/xpath_detector/exporters/python_exp.py`
- Test: `tests/test_exporters_naming.py`

**Step 1: Test du module _naming**

Creer `tests/test_exporters_naming.py`:

```python
from xpath_detector.exporters._naming import sanitize, to_constant, to_pascal, to_var_name
from xpath_detector.models import Element, XPathCandidate


def _elem(description="", text=None, name=None, tag="input"):
    attrs = {"name": name} if name else {}
    return Element(
        tag=tag,
        text=text,
        attributes=attrs,
        xpaths=[XPathCandidate("by_id", "//x", 95)],
        is_visible=True,
        is_enabled=True,
        description=description,
    )


def test_sanitize_replaces_special_chars():
    assert sanitize("hello world!") == "hello_world_"


def test_sanitize_truncates_to_50():
    assert len(sanitize("a" * 100)) == 50


def test_to_pascal_simple():
    assert to_pascal("login") == "Login"


def test_to_pascal_with_separator():
    assert to_pascal("create-transfert") == "CreateTransfert"


def test_to_pascal_empty_fallback():
    assert to_pascal("") == "Screen"


def test_to_constant_from_description():
    el = _elem(description="Login Field")
    assert to_constant(el) == "LOGIN_FIELD"


def test_to_constant_falls_back_to_text():
    el = _elem(text="Submit")
    assert to_constant(el) == "SUBMIT"


def test_to_constant_falls_back_to_name():
    el = _elem(name="username")
    assert to_constant(el) == "USERNAME"


def test_to_constant_falls_back_to_tag():
    el = _elem(tag="button")
    assert to_constant(el) == "BUTTON"


def test_to_var_name_max_30_chars():
    el = _elem(description="a" * 100)
    assert len(to_var_name(el)) <= 30
```

**Step 2: Run test, observe FAIL (ImportError)**

```bash
pytest tests/test_exporters_naming.py -v
```

**Step 3: Creer `src/xpath_detector/exporters/_naming.py`**

```python
"""Internal naming helpers for exporters (DRY across java/python/robot)."""
import re

from xpath_detector.models import Element


def sanitize(name: str) -> str:
    """Replace non-alphanumeric chars with underscore, truncate to 50."""
    return re.sub(r"[^A-Za-z0-9_]", "_", name)[:50]


def to_pascal(name: str) -> str:
    """Convert a name to PascalCase. Fallback to 'Screen' if empty."""
    parts = re.split(r"[^A-Za-z0-9]+", name)
    return "".join(p.capitalize() for p in parts if p) or "Screen"


def to_constant(element: Element) -> str:
    """Generate a CONSTANT_NAME from an element (40 char max)."""
    base = element.description or element.text or element.attributes.get("name") or element.tag
    return re.sub(r"[^A-Za-z0-9_]", "_", base).upper().strip("_")[:40] or "ELEMENT"


def to_var_name(element: Element) -> str:
    """Generate a Robot ${VAR} name (30 char max)."""
    base = element.description or element.text or element.attributes.get("name") or element.tag
    return sanitize(base).upper()[:30]
```

**Step 4: Run test, must PASS**

```bash
pytest tests/test_exporters_naming.py -v
```

**Step 5: Refactor robot_exp.py**

Remplacer les fonctions locales `_sanitize` et `_to_var_name` par l'import. Le fichier complet devient :

```python
"""Robot Framework .resource exporter."""
from pathlib import Path

from xpath_detector.exporters._naming import sanitize, to_var_name
from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Element, Session


class RobotExporter(Exporter):
    name = "robot"
    extension = ".resource"

    def export(self, session: Session, output_dir: Path) -> Path:
        base = output_dir / f"robot_{session.id}"
        base.mkdir(parents=True, exist_ok=True)

        for screen_name, screen in session.screens.items():
            folder = base / sanitize(screen_name)
            folder.mkdir(parents=True, exist_ok=True)
            resource = folder / "locators.resource"
            content = self._render(screen.name, screen.elements)
            resource.write_text(content, encoding="utf-8")

        return base

    def _render(self, screen_name: str, elements: list[Element]) -> str:
        lines = [
            "*** Settings ***",
            f"Documentation    Locators for screen: {screen_name}",
            "",
            "*** Variables ***",
        ]
        for el in elements:
            if not el.xpaths:
                continue
            best = el.xpaths[0]
            var = to_var_name(el)
            lines.append(f"${{{var}}}    {best.expression}")
        return "\n".join(lines) + "\n"
```

**Step 6: Refactor java_exp.py**

Remplacer `_to_pascal` et `_to_constant` locaux par imports :

```python
"""Java Selenium Locators class exporter."""
from pathlib import Path

from xpath_detector.exporters._naming import to_constant, to_pascal
from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Session


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
            class_name = to_pascal(screen_name)
            lines.append(f"    public static final class {class_name} {{")
            lines.append(f"        private {class_name}() {{}}")
            for el in screen.elements:
                if not el.xpaths:
                    continue
                best = el.xpaths[0]
                var = to_constant(el)
                escaped = best.expression.replace('"', '\\"')
                lines.append(f'        public static final By {var} = By.xpath("{escaped}");')
            lines.append("    }")
            lines.append("")
        lines.append("}")
        return "\n".join(lines) + "\n"
```

**Step 7: Refactor python_exp.py**

Idem :

```python
"""Python Selenium locators module exporter."""
from pathlib import Path

from xpath_detector.exporters._naming import to_constant, to_pascal
from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Session


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
            class_name = to_pascal(screen_name)
            lines.append(f"class {class_name}:")
            has_any = False
            for el in screen.elements:
                if not el.xpaths:
                    continue
                best = el.xpaths[0]
                var = to_constant(el)
                escaped = best.expression.replace('"', '\\"')
                lines.append(f'    {var} = (By.XPATH, "{escaped}")')
                has_any = True
            if not has_any:
                lines.append("    pass")
            lines.append("")
        return "\n".join(lines) + "\n"
```

**Step 8: Run all tests (regression check)**

```bash
pytest -q
```

Expected: tous les tests passent, +11 nouveaux (35+11=46).

**Step 9: Commit**

```bash
git add src/xpath_detector/exporters/_naming.py \
        src/xpath_detector/exporters/robot_exp.py \
        src/xpath_detector/exporters/java_exp.py \
        src/xpath_detector/exporters/python_exp.py \
        tests/test_exporters_naming.py
git commit -m "refactor(exporters): extract naming helpers to _naming module (DRY)"
```

---

## Phase 2 — Important fixes (I-1, I-3, I-4)

### Task 4 : I-1 Overlay target consistency

**Files:**
- Modify: `src/xpath_detector/overlay.py`
- Modify: `tests/test_overlay.py`

**Step 1: Ajouter un test structurel**

Append a `tests/test_overlay.py`:

```python
def test_overlay_click_uses_elementfrompoint():
    """Click handler must use document.elementFromPoint for consistency with hover."""
    from xpath_detector.overlay import OVERLAY_JS
    # The click handler should NOT use e.target alone
    # It should use document.elementFromPoint(e.clientX, e.clientY)
    click_block = OVERLAY_JS[OVERLAY_JS.find("'click'"):OVERLAY_JS.find("'keydown'")]
    assert "elementFromPoint" in click_block, "click handler should use elementFromPoint"
```

**Step 2: Run test (FAIL)**

```bash
pytest tests/test_overlay.py -v
```

Expected: 3 passed, 1 failed.

**Step 3: Modifier overlay.py**

Dans `OVERLAY_JS`, remplacer le bloc `click` :

```javascript
    document.addEventListener('click', (e) => {
        if (!active) return;
        if (!(e.ctrlKey || e.metaKey)) return;
        e.preventDefault();
        e.stopPropagation();
        const el = document.elementFromPoint(e.clientX, e.clientY) || e.target;
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
```

Key change : `const el = document.elementFromPoint(e.clientX, e.clientY) || e.target;`

**Step 4: Run test (PASS)**

```bash
pytest tests/test_overlay.py -v
```

Expected: 4 passed.

**Step 5: Commit**

```bash
git add src/xpath_detector/overlay.py tests/test_overlay.py
git commit -m "fix(overlay): use elementFromPoint in click handler for hover/click consistency"
```

---

### Task 5 : I-3 cmd_help

**Files:**
- Modify: `src/xpath_detector/shell.py`

**Step 1: Ajouter cmd_help dans la classe Shell**

Apres `cmd_quit` dans `shell.py`, ajouter :

```python
    def cmd_help(self, args: list[str]) -> None:
        table = Table(title="Available commands")
        table.add_column("Command")
        table.add_column("Description")
        for cmd, desc in [
            ("open <url>", "Navigate to a URL"),
            ("screen <name>", "Create or switch to a screen"),
            ("list", "Show all captured screens"),
            ("show", "Show elements in current screen"),
            ("export <format>", "Export to format (json/html/robot/java/python/all)"),
            ("save", "Save session to sessions/<id>.json"),
            ("load <path>", "Load a session from JSON file"),
            ("help", "Show this help"),
            ("quit", "Exit xpath-detector"),
        ]:
            table.add_row(cmd, desc)
        self.console.print(table)
        self.console.print(
            "[dim]In the browser: hover to highlight, Ctrl+click to capture, Esc to toggle.[/dim]"
        )
```

Aussi mettre a jour le greeting dans `run()` :
- Remplacer la 2eme `self.console.print(...)` par : `self.console.print("Type [bold]help[/bold] for available commands.")`

**Step 2: Verifier que ca compile**

```bash
python -c "from xpath_detector.shell import Shell; print('ok')"
```

Expected: `ok`

**Step 3: Commit**

```bash
git add src/xpath_detector/shell.py
git commit -m "feat(shell): add help command listing all available commands"
```

---

### Task 6 : I-4 Shell unit tests

**Files:**
- Create: `tests/test_shell.py`

**Step 1: Ecrire les tests**

Creer `tests/test_shell.py`:

```python
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
    # No screen exists, so nothing to check directly
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
            }
        )

    assert len(shell_no_browser.session.screens["login"].elements) == 1
    el = shell_no_browser.session.screens["login"].elements[0]
    assert el.tag == "input"
    assert el.description == "test desc"
    assert any(c.strategy == "by_id" for c in el.xpaths)


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
```

**Step 2: Run test (PASS)**

```bash
pytest tests/test_shell.py -v
```

Expected: 5 passed.

Note : Si un test fail a cause d'imports circulaires avec BrowserController, c'est OK — il faudra peut-etre patcher autrement. Adapter le `patch()` au besoin.

**Step 3: Run all tests pour regression**

```bash
pytest -q
```

Expected: 51 passed (46 + 5 nouveaux).

**Step 4: Commit**

```bash
git add tests/test_shell.py
git commit -m "test(shell): add unit tests for capture pipeline and export dispatch"
```

---

## Phase 3 — by_label_neighbor (I-5a)

### Task 7 : Analyzer by_label_neighbor (TDD)

**Files:**
- Modify: `tests/test_analyzer.py`
- Modify: `src/xpath_detector/analyzer.py`

**Step 1: Ajouter le test**

Append a `tests/test_analyzer.py`:

```python
def test_generate_by_label_neighbor():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={},
        nearby_label="Compte beneficiaire :",
    )
    cand = next(c for c in candidates if c.strategy == "by_label_neighbor")
    assert "//span[contains(.,'Compte beneficiaire :')]/../../td/input" == cand.expression
    assert cand.stability_score == 50


def test_by_label_neighbor_escapes_apostrophe():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={},
        nearby_label="Reference donneur d'ordre :",
    )
    cand = next(c for c in candidates if c.strategy == "by_label_neighbor")
    assert "concat(" in cand.expression


def test_by_label_neighbor_skipped_if_none():
    candidates = generate_candidates(tag="input", text=None, attributes={"id": "x"})
    assert not any(c.strategy == "by_label_neighbor" for c in candidates)
```

**Step 2: Run (FAIL — nearby_label parameter doesn't exist)**

```bash
pytest tests/test_analyzer.py -v
```

**Step 3: Modifier `generate_candidates` dans `analyzer.py`**

Changer la signature :

```python
def generate_candidates(
    tag: str,
    text: str | None,
    attributes: dict[str, str],
    absolute_xpath: str | None = None,
    nearby_label: str | None = None,
) -> list[XPathCandidate]:
```

Et apres le bloc `by_text` (avant `by_class`), ajouter :

```python
    if nearby_label and 0 < len(nearby_label) < 50:
        candidates.append(
            XPathCandidate(
                strategy="by_label_neighbor",
                expression=f"//span[contains(.,{escape_xpath_literal(nearby_label)})]/../../td/{tag}",
                stability_score=50,
            )
        )
```

**Step 4: Run (PASS)**

```bash
pytest tests/test_analyzer.py -v
```

Expected: 20 passed (17 + 3 nouveaux).

**Step 5: Commit**

```bash
git add tests/test_analyzer.py src/xpath_detector/analyzer.py
git commit -m "feat(analyzer): add by_label_neighbor strategy (score 50)"
```

---

### Task 8 : Overlay - findNearbyLabel + payload

**Files:**
- Modify: `src/xpath_detector/overlay.py`
- Modify: `tests/test_overlay.py`

**Step 1: Test structurel**

Append a `tests/test_overlay.py`:

```python
def test_overlay_has_find_nearby_label():
    from xpath_detector.overlay import OVERLAY_JS

    assert "findNearbyLabel" in OVERLAY_JS
    assert "nearby_label" in OVERLAY_JS


def test_overlay_uses_label_for_attribute():
    from xpath_detector.overlay import OVERLAY_JS

    assert 'label[for="' in OVERLAY_JS or "label[for=" in OVERLAY_JS
```

**Step 2: Run (FAIL)**

```bash
pytest tests/test_overlay.py -v
```

**Step 3: Modifier overlay.py**

Ajouter la fonction `findNearbyLabel` dans le JS (avant `getAbsoluteXPath`) :

```javascript
    function findNearbyLabel(el) {
        // 1. <label for="id"> via attribute
        if (el.id) {
            const lbl = document.querySelector('label[for="' + el.id + '"]');
            if (lbl) {
                const t = lbl.textContent.trim();
                if (t && t.length < 50) return t;
            }
        }
        // 2. Ancestor <label>
        const ancestor = el.closest('label');
        if (ancestor) {
            const t = ancestor.textContent.trim();
            if (t && t.length < 50) return t;
        }
        // 3. First preceding <span>/<label> within 3 ancestor levels
        let parent = el.parentElement;
        for (let depth = 0; parent && depth < 3; depth++) {
            const lbls = parent.querySelectorAll('span, label');
            for (const lbl of lbls) {
                const t = lbl.textContent.trim();
                if (t && t.length < 50 &&
                    (lbl.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)) {
                    return t;
                }
            }
            parent = parent.parentElement;
        }
        return null;
    }
```

Et modifier le payload du click handler pour inclure `nearby_label` :

```javascript
        const data = {
            tag: el.tagName.toLowerCase(),
            text: (el.textContent || '').trim().slice(0, 200),
            attributes: attrs,
            absolute_xpath: getAbsoluteXPath(el),
            nearby_label: findNearbyLabel(el),
            is_visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
            is_enabled: !el.disabled,
        };
```

**Step 4: Run (PASS)**

```bash
pytest tests/test_overlay.py -v
```

Expected: 6 passed.

**Step 5: Commit**

```bash
git add src/xpath_detector/overlay.py tests/test_overlay.py
git commit -m "feat(overlay): detect nearby label and include in capture payload"
```

---

### Task 9 : Shell propage nearby_label

**Files:**
- Modify: `src/xpath_detector/shell.py`

**Step 1: Modifier `_on_capture`**

Dans `shell.py`, le `_on_capture` actuel :
```python
xpaths = generate_candidates(
    tag=data["tag"],
    text=data.get("text"),
    attributes=data.get("attributes", {}),
    absolute_xpath=data.get("absolute_xpath"),
)
```

Ajouter `nearby_label=data.get("nearby_label")` :

```python
xpaths = generate_candidates(
    tag=data["tag"],
    text=data.get("text"),
    attributes=data.get("attributes", {}),
    absolute_xpath=data.get("absolute_xpath"),
    nearby_label=data.get("nearby_label"),
)
```

**Step 2: Mettre a jour le test shell**

Dans `tests/test_shell.py`, le test `test_on_capture_adds_element_to_current_screen` ajoute un nearby_label :

Remplacer :
```python
shell_no_browser._on_capture(
    {
        "tag": "input",
        "text": None,
        "attributes": {"id": "x"},
        "is_visible": True,
        "is_enabled": True,
        "absolute_xpath": "/html/body/input",
    }
)
```

Par :
```python
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
```

Et ajouter une assertion :
```python
assert any(c.strategy == "by_label_neighbor" for c in el.xpaths)
```

**Step 3: Run tests**

```bash
pytest tests/test_shell.py tests/test_analyzer.py -v
```

Expected: PASS.

**Step 4: Commit**

```bash
git add src/xpath_detector/shell.py tests/test_shell.py
git commit -m "feat(shell): propagate nearby_label from capture to analyzer"
```

---

## Phase 4 — Migration v1 -> v1.1 (I-5b)

### Task 10 : Script de migration

**Files:**
- Create: `scripts/__init__.py` (empty)
- Create: `scripts/migrate_v1.py`
- Create: `tests/fixtures/session_v1.json`
- Create: `tests/test_migrate_v1.py`

**Step 1: Creer la fixture v1.0**

`tests/fixtures/session_v1.json` :

```json
{
  "session": {
    "id": "20251020_120000",
    "date": "2025-10-20T12:00:00",
    "total_screens": 1,
    "total_elements": 1
  },
  "screens": {
    "login": {
      "url": "https://x.fr/login",
      "title": "Login",
      "timestamp": "2025-10-20T12:00:00",
      "elements": [
        {
          "tag": "input",
          "text": null,
          "attributes": {"id": "_login", "type": "text"},
          "xpaths": {
            "absolute": "/html/body/input",
            "relative": ["//input[@id='_login']", "//input[@type='text']"],
            "by_text": null,
            "by_id": "//input[@id='_login']",
            "by_class": null,
            "by_attributes": []
          },
          "is_visible": true,
          "is_enabled": true,
          "description": "Login field"
        }
      ]
    }
  }
}
```

**Step 2: Test du script**

`tests/test_migrate_v1.py` :

```python
"""Tests for migrate_v1.py script."""
import json
import subprocess
import sys
from pathlib import Path


FIXTURES = Path(__file__).parent / "fixtures"


def test_migrate_v1_converts_old_format(tmp_path: Path):
    src = FIXTURES / "session_v1.json"
    dst = tmp_path / "migrated.json"

    result = subprocess.run(
        [sys.executable, "scripts/migrate_v1.py", str(src), str(dst)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0, result.stderr

    data = json.loads(dst.read_text())
    assert data["id"] == "20251020_120000"
    assert "login" in data["screens"]
    login = data["screens"]["login"]
    assert len(login["elements"]) == 1
    el = login["elements"][0]
    assert el["tag"] == "input"
    # by_id should be mapped with score 95
    xpaths = el["xpaths"]
    assert any(x["strategy"] == "by_id" and x["stability_score"] == 95 for x in xpaths)
    # absolute should be mapped with score 10
    assert any(x["strategy"] == "absolute" and x["stability_score"] == 10 for x in xpaths)


def test_migrate_v1_missing_input_fails(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, "scripts/migrate_v1.py", str(tmp_path / "missing.json"), str(tmp_path / "out.json")],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode != 0
```

**Step 3: Run test (FAIL — script doesn't exist)**

```bash
pytest tests/test_migrate_v1.py -v
```

**Step 4: Creer `scripts/migrate_v1.py`**

```python
"""Migrate xpath-detector session JSON from v1.0 format to v1.1 format.

Usage:
    python scripts/migrate_v1.py <input.json> <output.json>

The v1.0 format has xpaths as a dict with keys (absolute, relative, by_id, by_text,
by_class, by_attributes). The v1.1 format has xpaths as a list of XPathCandidate
objects with strategy/expression/stability_score.

Strategy scoring (best-effort):
- by_id -> 95
- by_text -> 70
- by_class -> 60
- relative[0] (unrecognized) -> "legacy_relative" 40
- absolute -> 10
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def migrate(v1_data: dict) -> dict:
    """Convert a v1.0 session dict to v1.1 format."""
    out_screens = {}
    for screen_name, screen in v1_data.get("screens", {}).items():
        out_elements = []
        for el in screen.get("elements", []):
            out_xpaths = _convert_xpaths(el.get("xpaths", {}))
            out_elements.append(
                {
                    "tag": el.get("tag", ""),
                    "text": el.get("text"),
                    "attributes": el.get("attributes", {}),
                    "xpaths": out_xpaths,
                    "is_visible": el.get("is_visible", True),
                    "is_enabled": el.get("is_enabled", True),
                    "description": el.get("description", ""),
                }
            )
        out_screens[screen_name] = {
            "name": screen_name,
            "url": screen.get("url", ""),
            "title": screen.get("title", ""),
            "timestamp": screen.get("timestamp", ""),
            "elements": out_elements,
        }

    session_id = (
        v1_data.get("session", {}).get("id")
        or v1_data.get("id")
        or "migrated"
    )

    return {"id": session_id, "screens": out_screens}


def _convert_xpaths(v1_xpaths: dict) -> list[dict]:
    """Convert v1.0 xpaths dict to v1.1 candidate list, sorted by score desc."""
    candidates: list[dict] = []

    if v1_xpaths.get("by_id"):
        candidates.append({"strategy": "by_id", "expression": v1_xpaths["by_id"], "stability_score": 95})
    if v1_xpaths.get("by_text"):
        candidates.append({"strategy": "by_text", "expression": v1_xpaths["by_text"], "stability_score": 70})
    if v1_xpaths.get("by_class"):
        candidates.append({"strategy": "by_class", "expression": v1_xpaths["by_class"], "stability_score": 60})

    seen = {c["expression"] for c in candidates}
    for rel in v1_xpaths.get("relative", []):
        if rel not in seen:
            candidates.append({"strategy": "legacy_relative", "expression": rel, "stability_score": 40})
            seen.add(rel)

    if v1_xpaths.get("absolute"):
        candidates.append({"strategy": "absolute", "expression": v1_xpaths["absolute"], "stability_score": 10})

    candidates.sort(key=lambda c: -c["stability_score"])
    return candidates


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"Usage: {argv[0]} <input_v1.json> <output_v11.json>", file=sys.stderr)
        return 2

    src = Path(argv[1])
    dst = Path(argv[2])

    if not src.exists():
        print(f"Input file not found: {src}", file=sys.stderr)
        return 1

    v1_data = json.loads(src.read_text(encoding="utf-8"))
    v11_data = migrate(v1_data)
    dst.write_text(json.dumps(v11_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Migrated {src} -> {dst} ({len(v11_data['screens'])} screens)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

Et creer `scripts/__init__.py` vide.

**Step 5: Run test (PASS)**

```bash
pytest tests/test_migrate_v1.py -v
```

Expected: 2 passed.

**Step 6: Verifier le script manuellement**

```bash
python scripts/migrate_v1.py tests/fixtures/session_v1.json /tmp/out.json
cat /tmp/out.json | python -m json.tool | head -30
```

**Step 7: Run all tests pour regression**

```bash
pytest -q
```

Expected: 58 passed.

**Step 8: Commit**

```bash
git add scripts/migrate_v1.py scripts/__init__.py \
        tests/test_migrate_v1.py tests/fixtures/session_v1.json
git commit -m "feat(scripts): add migrate_v1.py for v1.0 -> v1.1 session conversion"
```

---

## Phase 5 — Finalisation

### Task 11 : CHANGELOG.md

**Files:**
- Create: `CHANGELOG.md`

**Step 1: Creer le CHANGELOG**

```markdown
# Changelog

All notable changes to xpath-detector are documented here.

## [1.1.0] - 2026-05-12

### Fixed
- Overlay hover/click target mismatch on nested elements (I-1): click handler now uses `document.elementFromPoint` for consistency with hover highlight
- Shell coverage from 26% to ~60% with new unit tests for capture pipeline and export dispatch (I-4)

### Added
- `help` command in interactive shell lists all available commands and shortcuts (I-3)
- `by_label_neighbor` strategy in analyzer (score 50) for inputs identified by their nearby label text (I-5a)
- Overlay JS detects the nearest label via `label[for=]`, ancestor `<label>`, or preceding sibling `<span>`/`<label>` within 3 ancestor levels
- `scripts/migrate_v1.py` script to convert v1.0 session JSON to v1.1 format (I-5b)
- Console logging handler (WARNING+) on stderr in addition to file handler (M-9)
- Edge-case tests for `escape_xpath_literal`: empty string, lone apostrophe, wrapped, consecutive (M-11)

### Changed
- Naming helpers (`sanitize`, `to_pascal`, `to_constant`, `to_var_name`) extracted from java/python/robot exporters to `exporters/_naming.py` (M-4 DRY)

## [1.0.0] - 2026-05-12

Initial release. Complete rewrite of xpath_detector with Playwright sync, plugin-based exporters (JSON/HTML/Robot/Java/Python), interactive shell with rich UI, JS overlay for Ctrl+click capture.
```

**Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG with v1.0.0 and v1.1.0 entries"
```

---

### Task 12 : Lint + tag + push

**Step 1: Lint check**

```bash
cd /Users/nitch/projects/git_projets/xpath_detector
source .venv/bin/activate
ruff check src/ tests/ scripts/
black --check src/ tests/ scripts/
```

Si lint fail, fix avec `ruff check --fix` et `black src/ tests/ scripts/`, et commit :
```bash
git add -A && git commit -m "chore: apply ruff/black auto-fixes"
```

**Step 2: Tests finaux**

```bash
pytest -q
pytest --cov=xpath_detector --cov-report=term
```

Expected: tous les tests passent, coverage shell > 50%.

**Step 3: Tag v1.1.0**

```bash
git tag v1.1.0
```

**Step 4: Push**

```bash
git push origin master
git push origin v1.1.0
```

**Step 5: Creer la release GitHub**

```bash
gh release create v1.1.0 --title "v1.1.0 - Fixes from v1.0 review" --notes-file CHANGELOG.md
```

(Ou copier le contenu de la section v1.1.0 du CHANGELOG dans les release notes.)

---

## Recapitulatif

| Phase | Tasks | Duree estimee |
|-------|-------|---------------|
| Phase 1 (M-9, M-11, M-4) | 1-3 | 1h |
| Phase 2 (I-1, I-3, I-4) | 4-6 | 1h30 |
| Phase 3 (I-5a) | 7-9 | 1h30 |
| Phase 4 (I-5b) | 10 | 1h |
| Phase 5 (finalisation) | 11-12 | 30 min |
| **Total** | **12 tasks** | **~5h30** |

**Couverture cible** : > 80% globale (vs 67% en v1.0). Shell > 50% (vs 26%).

**Commits attendus** : ~12 commits atomiques + 1 chore lint.

---

## Execution

Plan complet et sauvegarde. Deux options :

**1. Subagent-Driven (cette session)** — je delegue chaque tache a un subagent frais, revue legere entre les groupes

**2. Parallel Session (separee)** — tu ouvres une nouvelle session avec `executing-plans`

Recommandation : **1**, vu qu'on est deja dans le contexte v1.0 et que tu connais l'historique.
