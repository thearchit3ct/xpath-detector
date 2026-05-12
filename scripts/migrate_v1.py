"""Migrate xpath-detector session JSON from v1.0 format to v1.1 format.

Usage:
    python scripts/migrate_v1.py <input.json> <output.json>
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
