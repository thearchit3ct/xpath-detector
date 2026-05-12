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
