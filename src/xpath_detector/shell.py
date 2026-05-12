"""Interactive shell."""
from __future__ import annotations


def parse_command(line: str) -> tuple[str, list[str]]:
    """Parse une ligne de commande en (commande, args)."""
    parts = line.strip().split()
    if not parts:
        return ("", [])
    return (parts[0], parts[1:])
