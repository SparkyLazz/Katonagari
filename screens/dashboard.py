from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane, Label
from widgets.header import Header

class Dashboard(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Home", id="home"):
                yield Label("Welcome Home!")
            with TabPane("Settings", id="settings"):
                yield Label("Settings go here")
            with TabPane("About", id="about"):
                yield Label("About this app")