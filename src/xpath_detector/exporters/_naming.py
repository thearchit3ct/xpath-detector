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


def dedup_name(name: str, seen: dict[str, int]) -> str:
    """Return a unique name by appending _2, _3, ... if already in `seen`.

    Mutates `seen` to track the next available suffix. First call with a given
    name returns it unchanged. Subsequent calls return name_2, name_3, etc.
    """
    if name not in seen:
        seen[name] = 1
        return name
    seen[name] += 1
    return f"{name}_{seen[name]}"
