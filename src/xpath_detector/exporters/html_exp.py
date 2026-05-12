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
<title>xpath-detector report - {escape(session.id)}</title>
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
