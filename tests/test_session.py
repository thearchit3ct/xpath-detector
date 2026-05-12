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
