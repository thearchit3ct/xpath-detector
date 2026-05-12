"""Interactive shell."""
from __future__ import annotations

import logging
from datetime import datetime
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from xpath_detector.analyzer import generate_candidates
from xpath_detector.browser import BrowserController
from xpath_detector.exporters.base import Exporter
from xpath_detector.models import Element, Screen, Session
from xpath_detector.session import load_session, save_session

LOGGER = logging.getLogger(__name__)
SESSIONS_DIR = Path("sessions")
EXPORTS_DIR = Path("exports")


def parse_command(line: str) -> tuple[str, list[str]]:
    """Parse une ligne de commande en (commande, args)."""
    parts = line.strip().split()
    if not parts:
        return ("", [])
    return (parts[0], parts[1:])


def _load_exporters() -> dict[str, Exporter]:
    result: dict[str, Exporter] = {}
    for ep in entry_points(group="xpath_detector.exporters"):
        cls = ep.load()
        result[ep.name] = cls()
    return result


class Shell:
    def __init__(self) -> None:
        self.console = Console()
        self.session = Session(id=datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.current_screen: str | None = None
        self.browser = BrowserController()
        self.exporters = _load_exporters()
        self.running = True
        self.browser.on_capture(self._on_capture)

    def run(self) -> None:
        self.browser.start()
        self.console.print("[bold green]xpath-detector started.[/bold green]")
        self.console.print("Commands: open <url>, screen <name>, list, show, export <format>, save, quit")

        while self.running:
            try:
                line = self.console.input("[cyan]> [/cyan]")
            except (EOFError, KeyboardInterrupt):
                self.running = False
                break
            cmd, args = parse_command(line)
            if not cmd:
                continue
            handler = getattr(self, f"cmd_{cmd}", None)
            if handler is None:
                self.console.print(f"[red]Unknown command: {cmd}[/red]")
                continue
            try:
                handler(args)
            except Exception as e:
                LOGGER.exception("Command failed")
                self.console.print(f"[red]Error: {e}[/red]")

        self.browser.stop()

    def cmd_open(self, args: list[str]) -> None:
        if not args:
            self.console.print("[red]Usage: open <url>[/red]")
            return
        url = args[0]
        self.browser.open(url)
        self.console.print(f"[green]Opened {url}[/green]")

    def cmd_screen(self, args: list[str]) -> None:
        if not args:
            self.console.print("[red]Usage: screen <name>[/red]")
            return
        name = args[0]
        if name not in self.session.screens:
            self.session.screens[name] = Screen(
                name=name,
                url=self.browser.current_url(),
                title=self.browser.current_title(),
                timestamp=datetime.now(),
            )
            self.console.print(f"[green]Created screen '{name}'[/green]")
        self.current_screen = name
        self.console.print(f"[cyan]Current screen: {name}[/cyan]")

    def cmd_list(self, args: list[str]) -> None:
        table = Table(title="Screens")
        table.add_column("Name")
        table.add_column("Elements")
        table.add_column("URL")
        for name, screen in self.session.screens.items():
            marker = " (current)" if name == self.current_screen else ""
            table.add_row(name + marker, str(len(screen.elements)), screen.url)
        self.console.print(table)

    def cmd_show(self, args: list[str]) -> None:
        if not self.current_screen:
            self.console.print("[red]No current screen[/red]")
            return
        screen = self.session.screens[self.current_screen]
        for i, el in enumerate(screen.elements):
            xpath = el.xpaths[0].expression if el.xpaths else "-"
            self.console.print(f"[{i}] [yellow]{el.tag}[/yellow] {el.description} -> {xpath}")

    def cmd_export(self, args: list[str]) -> None:
        if not args:
            self.console.print(f"[red]Available: {', '.join(self.exporters)}[/red]")
            return
        target = args[0]
        EXPORTS_DIR.mkdir(exist_ok=True)
        if target == "all":
            for name, exporter in self.exporters.items():
                out = exporter.export(self.session, EXPORTS_DIR)
                self.console.print(f"[green]{name}[/green] -> {out}")
            return
        exporter = self.exporters.get(target)
        if exporter is None:
            self.console.print(f"[red]Unknown exporter: {target}[/red]")
            return
        out = exporter.export(self.session, EXPORTS_DIR)
        self.console.print(f"[green]Exported to {out}[/green]")

    def cmd_save(self, args: list[str]) -> None:
        SESSIONS_DIR.mkdir(exist_ok=True)
        path = SESSIONS_DIR / f"{self.session.id}.json"
        save_session(self.session, path)
        self.console.print(f"[green]Session saved: {path}[/green]")

    def cmd_load(self, args: list[str]) -> None:
        if not args:
            self.console.print("[red]Usage: load <path>[/red]")
            return
        self.session = load_session(Path(args[0]))
        self.console.print(f"[green]Loaded session {self.session.id}[/green]")

    def cmd_quit(self, args: list[str]) -> None:
        self.running = False

    def _on_capture(self, data: dict[str, Any]) -> None:
        if not self.current_screen:
            self.console.print("[yellow]No current screen, capture ignored. Use 'screen <name>' first.[/yellow]")
            return
        desc = self.console.input("[cyan]Description (Enter to skip): [/cyan]")
        xpaths = generate_candidates(
            tag=data["tag"],
            text=data.get("text"),
            attributes=data.get("attributes", {}),
            absolute_xpath=data.get("absolute_xpath"),
        )
        element = Element(
            tag=data["tag"],
            text=data.get("text"),
            attributes=data.get("attributes", {}),
            xpaths=xpaths,
            is_visible=data.get("is_visible", True),
            is_enabled=data.get("is_enabled", True),
            description=desc,
        )
        self.session.screens[self.current_screen].elements.append(element)
        best = xpaths[0].expression if xpaths else "-"
        self.console.print(f"[green]Captured {element.tag} -> {best}[/green]")
