"""Session persistence (save/load JSON)."""
from __future__ import annotations

import json
from pathlib import Path

from xpath_detector.models import Session


def save_session(session: Session, path: Path) -> None:
    """Sauvegarde une session dans un fichier JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(session.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_session(path: Path) -> Session:
    """Charge une session depuis un fichier JSON."""
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return Session.from_dict(data)
