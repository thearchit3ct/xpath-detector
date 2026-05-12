"""Robot Framework .resource exporter."""

from pathlib import Path

from xpath_detector.exporters._naming import dedup_name, sanitize, to_var_name
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
        seen: dict[str, int] = {}
        for el in elements:
            if not el.xpaths:
                continue
            best = el.xpaths[0]
            var = dedup_name(to_var_name(el), seen)
            lines.append(f"${{{var}}}    {best.expression}")
        return "\n".join(lines) + "\n"
