from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

class Schedule(Widget):
    def compose(self) -> ComposeResult:
        yield Static("Schedule Group", id="welcome")