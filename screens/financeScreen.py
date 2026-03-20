"""
screens/financeScreen.py — Finance screen.
On account change: remounts Log (has account tabs in compose).
On transaction change: refreshes data in-place.
"""
from __future__ import annotations
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, TabbedContent, TabPane
from services.financeService import FinanceService
from widgets.finance.account import Accounts
from widgets.finance.analysis import Analysis
from widgets.finance.log import Log, TransactionLog
from widgets.finance.overview import Overview

class TabContent(Widget):
    DEFAULT_CSS = """
    TabContent { padding: 1; }
    Tab        { margin-right: 4; }
    Overview   { height: 1fr; }
    Accounts   { height: 1fr; }
    Analysis   { height: 1fr; }
    Log        { height: 1fr; }
    """
    BINDINGS = [Binding("r","refresh_all","Refresh",show=True)]

    def __init__(self, service: FinanceService, **kw) -> None:
        super().__init__(**kw); self._svc = service

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Overview", id="t-overview"):
                yield Overview(service=self._svc, id="w-overview")
            with TabPane("Accounts", id="t-accounts"):
                yield Accounts(service=self._svc, id="w-accounts")
            with TabPane("Analysis", id="t-analysis"):
                yield Analysis(service=self._svc, id="w-analysis")
            with TabPane("Log", id="t-log"):
                yield Log(service=self._svc, id="w-log")

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        for wid in ("w-overview","w-accounts","w-analysis","w-log"):
            try: self.query_one(f"#{wid}").refresh_data()
            except Exception: pass

    def on_accounts_data_changed(self, _: Accounts.DataChanged) -> None:
        # Overview/Analysis have no account tabs — just refresh
        try: self.query_one("#w-overview",Overview).refresh_data()
        except Exception: pass
        try: self.query_one("#w-analysis",Analysis).refresh_data()
        except Exception: pass
        try: self.query_one("#w-accounts",Accounts).refresh_data()
        except Exception: pass
        # Log has account tabs in compose() — remount entirely
        pane = self.query_one("#t-log", TabPane)
        async def _do() -> None:
            try: await self.query_one("#w-log",Log).remove()
            except Exception: pass
            await pane.mount(Log(service=self._svc, id="w-log"))
        self.app.call_later(_do)

    def action_refresh_all(self) -> None:
        self.on_accounts_data_changed(Accounts.DataChanged())

class FinanceScreen(Screen):
    def __init__(self, **kw) -> None:
        super().__init__(**kw); self._svc = FinanceService()
    def compose(self) -> ComposeResult:
        yield TabContent(self._svc)
        yield Footer(show_command_palette=True)