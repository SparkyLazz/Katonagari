from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane, Label
from widgets.header import Header
from widgets.home import Home

class Dashboard(Screen):
    CSS = """
    Tabs {
        align: center middle;
        width: 100%;
    }

    Tab {
        width: auto;
        padding: 0 4;
    }

    TabbedContent {
        height: 1fr;
    }

    Home {
        height: 1fr;
        width: 100%;
        padding: 0 1;
    }
    """
    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Home", id="home"):
                yield Home()