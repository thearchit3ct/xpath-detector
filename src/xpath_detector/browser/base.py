"""Abstract browser backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class BrowserBackend(ABC):
    """Interface pour les backends de navigateur (Selenium, Playwright, ...)."""

    @abstractmethod
    def start(self) -> None:
        """Lance le navigateur et initialise le polling."""

    @abstractmethod
    def open(self, url: str) -> None:
        """Navigue vers une URL, injecte l'overlay."""

    @abstractmethod
    def reinject_overlay(self) -> None:
        """Re-injecte l'overlay (apres navigation interne)."""

    @abstractmethod
    def on_capture(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Enregistre un callback pour les captures."""

    @abstractmethod
    def current_url(self) -> str:
        """URL courante du navigateur."""

    @abstractmethod
    def current_title(self) -> str:
        """Titre courant du navigateur."""

    @abstractmethod
    def stop(self) -> None:
        """Ferme le navigateur et arrete le polling."""
