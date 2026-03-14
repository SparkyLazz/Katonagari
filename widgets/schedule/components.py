from __future__ import annotations
from textual.widget import Widget

class SidebarBox(Widget):
    DEFAULT_CSS = """
    SidebarBox {
        width: 100%;
        height: auto;
        border: round $surface-lighten-2;
        padding: 0 1;
        margin-bottom: 1;
        background: $surface 30%;
        overflow: hidden hidden;
    }
    """

    def __init__(self, title: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.border_title = title


class TablePanel(Widget):
    DEFAULT_CSS = """
    TablePanel {
        width: 100%;
        height: 1fr;
        border: round $surface-lighten-2;
        background: $surface 10%;
        layout: vertical;
        overflow: hidden hidden;
    }
    """
