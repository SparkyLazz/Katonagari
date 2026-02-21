from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label

class Home(Widget):
    def compose(self) -> ComposeResult:
        yield Label("Welcome to Katonagari App")