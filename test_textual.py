#!/usr/bin/env python3
"""
Minimaler Textual-Test — prüft ob Textual auf diesem System funktioniert.
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import ListView, ListItem, Label, Input, RichLog


class TestApp(App):
    CSS = """
    Screen { background: $surface; }
    #main { layout: horizontal; height: 1fr; }
    #left { width: 1fr; border: solid $primary; }
    #right { width: 2fr; border: solid $accent; }
    #log { height: 1fr; padding: 0 1; }
    #input-bar { height: 3; dock: bottom; border: solid $primary; }
    #status { height: 1; dock: bottom; background: $primary; color: $text; padding: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield ListView(id="chat-list")
            with Vertical(id="right"):
                yield RichLog(id="log", markup=True)
        with Vertical(id="input-bar"):
            yield Input(id="input", placeholder="Test-Eingabe...")
        yield Label(id="status", markup=True)

    def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        log.write("[bold green]Textual funktioniert![/]")
        log.write("")
        log.write("Wenn du das siehst, ist Textual OK.")
        log.write("Das Problem liegt woanders.")
        self.query_one("#status", Label).update(" OK — Textual funktioniert")


app = TestApp()
app.run()
