from __future__ import annotations
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, TabbedContent, TabPane
from widgets.finance.account import Accounts
from widgets.finance.analysis import Analysis
from widgets.finance.log import Log, TransactionLog, BalanceHistory
from widgets.finance.overview import Overview, SummaryPanel, TransactionTable
from services.financeService import FinanceService


class TabContent(Widget):
    DEFAULT_CSS = """
        TabContent { padding: 1; }
        Tab        { margin-right: 4; }
        Overview   { height: 1fr; }
        Analysis   { height: 1fr; }
        Log        { height: 1fr; }
        Accounts   { height: 1fr; }
    """
    BINDINGS = [
        Binding("r", "refresh_all", "Refresh", show=True),
    ]

    def __init__(self, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Overview", id="overview"):
                yield Overview(service=self._svc)
            with TabPane("Accounts", id="accounts"):
                yield Accounts(service=self._svc)
            with TabPane("Analysis", id="analysis"):
                yield Analysis(service=self._svc)
            with TabPane("Log", id="log"):
                yield Log(service=self._svc)

    def _do_refresh(self) -> None:
        msg = TransactionLog.DataChanged()

        # ── Overview ──────────────────────────────────────────────────────────
        try: self.query_one(Overview).on_transaction_log_data_changed(msg)
        except Exception: pass
        try: self.query_one(SummaryPanel).on_transaction_log_data_changed(msg)
        except Exception: pass
        try: self.query_one(TransactionTable).on_transaction_log_data_changed(msg)
        except Exception: pass

        # ── Log tab ───────────────────────────────────────────────────────────
        try: self.query_one(BalanceHistory).on_transaction_log_data_changed(msg)
        except Exception: pass

        # ── Analysis ──────────────────────────────────────────────────────────
        try: self.query_one(Analysis).refresh_data()
        except Exception: pass

        # ── Accounts ──────────────────────────────────────────────────────────
        try: self.query_one(Accounts).refresh_data()
        except Exception: pass

    # auto-refresh when DataChanged bubbles up from TransactionLog
    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        self._do_refresh()

    # auto-refresh when Accounts tab changes data
    def on_accounts_data_changed(self, _: Accounts.DataChanged) -> None:
        self._do_refresh()

    # manual refresh with r
    def action_refresh_all(self) -> None:
        self._do_refresh()


class FinanceScreen(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = FinanceService()

    def compose(self) -> ComposeResult:
        yield TabContent(self._svc)
        yield Footer(show_command_palette=True)