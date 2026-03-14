from __future__ import annotations
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label

class SidebarBox(Widget):
    DEFAULT_CSS = """
    SidebarBox {
        width: 100%;
        height: auto;
        background: $surface;
        padding: 0 1;
        margin-bottom: 1;
        overflow: hidden hidden;
        border: round $primary;
        border-title-align: left;
        border-title-color: $primary;
        border-title-style: bold;
    }
    """

    def __init__(self, title: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.border_title = title

    def compose(self) -> ComposeResult:
        return []


class TablePanel(Widget):
    DEFAULT_CSS = """
    TablePanel {
        width: 100%;
        height: 1fr;
        background: $surface;
        layout: vertical;
        overflow: hidden hidden;
        border: round $primary;
        border-title-align: left;
        border-title-color: $primary;
        border-title-style: bold;
        padding: 0 1;
        margin-bottom: 1;
    }
    """
