from textual.app import ComposeResult
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, TabbedContent, TabPane

from widgets.finance.analysis import Analysis
from widgets.finance.log import Log
from widgets.finance.overview import Overview
from widgets.finance.service import FinanceService


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
    Analysis {
        height: 1fr;
    }
    Log {
        height: 1fr;
    }
    """

    def __init__(self, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Overview", id="overview"):
                yield Overview()
            with TabPane("Analysis", id="analysis"):
                yield Analysis()
            with TabPane("Log", id="log"):
                yield Log(service=self._svc)


class FinanceScreen(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = FinanceService()

    def compose(self) -> ComposeResult:
        yield TabContent(self._svc)
        yield Footer(show_command_palette=True)