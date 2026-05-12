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
