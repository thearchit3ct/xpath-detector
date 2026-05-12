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
