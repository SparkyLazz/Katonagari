from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

class Finance(Widget):
    def compose(self) -> ComposeResult:
        yield Static("Finance Group", id="welcome")