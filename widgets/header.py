from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Rule


class Header(Widget):
    DEFAULT_CSS = """
    Header {
        layout: horizontal;
        height: 3;
        padding: 1 2;
    }

    #title {
        width: 1fr;
        text-style: bold;
        color: $primary;
    }

    #version {
        text-style: italic;
        text-opacity: 50%;
        color: $primary;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Katonagari", id="title")
        yield Label("v1.0", id="version")