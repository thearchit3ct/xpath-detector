"""Immutable data model for sessions, screens, elements, xpaths."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class XPathCandidate:
    strategy: str
    expression: str
    stability_score: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "expression": self.expression,
            "stability_score": self.stability_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> XPathCandidate:
        return cls(
            strategy=data["strategy"],
            expression=data["expression"],
            stability_score=data["stability_score"],
        )


@dataclass
class Element:
    tag: str
    text: str | None
    attributes: dict[str, str]
    xpaths: list[XPathCandidate]
    is_visible: bool
    is_enabled: bool
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag": self.tag,
            "text": self.text,
            "attributes": dict(self.attributes),
            "xpaths": [x.to_dict() for x in self.xpaths],
            "is_visible": self.is_visible,
            "is_enabled": self.is_enabled,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Element:
        return cls(
            tag=data["tag"],
            text=data.get("text"),
            attributes=dict(data.get("attributes", {})),
            xpaths=[XPathCandidate.from_dict(x) for x in data.get("xpaths", [])],
            is_visible=data.get("is_visible", True),
            is_enabled=data.get("is_enabled", True),
            description=data.get("description", ""),
        )


@dataclass
class Screen:
    name: str
    url: str
    title: str
    timestamp: datetime
    elements: list[Element] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp.isoformat(),
            "elements": [e.to_dict() for e in self.elements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Screen:
        return cls(
            name=data["name"],
            url=data["url"],
            title=data["title"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            elements=[Element.from_dict(e) for e in data.get("elements", [])],
        )


@dataclass
class Session:
    id: str
    screens: dict[str, Screen] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "screens": {name: screen.to_dict() for name, screen in self.screens.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        return cls(
            id=data["id"],
            screens={name: Screen.from_dict(s) for name, s in data.get("screens", {}).items()},
        )
