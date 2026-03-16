from textual import events
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Label, Footer, Header, TabbedContent, TabPane

from widgets.finance.overview import Overview


class TabContent(Widget):
    DEFAULT_CSS = """
    TabContent {
        padding: 1;
    }
    Tab {
        margin-right: 4;
    }
    Overview {
        height: 1fr;
    }
    """
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Overview", id="overview"):
                yield Overview()
            with TabPane("Analysis", id="analysis"):
                yield Label("Analysis")
            with TabPane("Log", id="log"):
                yield Label("Log")


class FinanceScreen(Screen):
    def compose(self) -> ComposeResult:
        yield TabContent()
        yield Footer(show_command_palette=True)
