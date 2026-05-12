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
    xpaths = el["xpaths"]
    assert any(x["strategy"] == "by_id" and x["stability_score"] == 95 for x in xpaths)
    assert any(x["strategy"] == "absolute" and x["stability_score"] == 10 for x in xpaths)


def test_migrate_v1_missing_input_fails(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, "scripts/migrate_v1.py", str(tmp_path / "missing.json"), str(tmp_path / "out.json")],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode != 0
