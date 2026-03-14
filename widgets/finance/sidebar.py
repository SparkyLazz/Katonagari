from __future__ import annotations
from datetime import date

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Label

from databases.financeData import (
    ACCOUNTS, ACCOUNT_ICON,
    get_monthly_summary, fmt_rp_short,
)

class FinanceSidebar(Widget):
    """Left sidebar: account balances + this-month summary."""

    DEFAULT_CSS = """
    FinanceSidebar {
        width: 28;
        height: 1fr;
        layout: vertical;
        overflow: hidden hidden;
        padding: 0 1 0 0;
    }

    .sb-box {
        width: 100%;
        height: auto;
        border: round $surface-lighten-2;
        padding: 0 1 1 1;
        margin-bottom: 1;
        overflow: hidden hidden;
    }

    .sb-row { height: 1; layout: horizontal; width: 100%; }
    .sb-lbl { width: 1fr; overflow: hidden hidden; color: $text-muted; }
    .sb-val { width: 9; text-align: right; text-style: bold; }
    .sb-sep { height: 1; color: $surface-lighten-2; }

    .acc-gopay   { color: $primary; }
    .acc-seabank { color: $success; }
    .acc-neobank { color: $accent;  }
    .acc-cash    { color: $warning; }
    """

    _ACC_CLS = {
        "GoPay":   "acc-gopay",
        "SeaBank": "acc-seabank",
        "NeoBank": "acc-neobank",
        "Cash":    "acc-cash",
    }

    def compose(self) -> ComposeResult:
        with Vertical(classes="sb-box") as b:
            b.border_title = "Accounts"
            for acc in ACCOUNTS:
                with Horizontal(classes="sb-row"):
                    yield Label(
                        f"● {ACCOUNT_ICON[acc]} {acc}",
                        classes=f"sb-lbl {self._ACC_CLS[acc]}")
                    yield Label("", id=f"bal-{acc.lower()}", classes="sb-val")
            yield Label("─" * 22, classes="sb-sep")
            with Horizontal(classes="sb-row"):
                yield Label("Total", classes="sb-lbl")
                yield Label("", id="bal-total", classes="sb-val")

        with Vertical(classes="sb-box") as b2:
            b2.border_title = "This Month"
            with Horizontal(classes="sb-row"):
                yield Label("↑ Income",  classes="sb-lbl")
                yield Label("", id="mon-inc", classes="sb-val")
            with Horizontal(classes="sb-row"):
                yield Label("↓ Expense", classes="sb-lbl")
                yield Label("", id="mon-exp", classes="sb-val")
            yield Label("─" * 22, classes="sb-sep")
            with Horizontal(classes="sb-row"):
                yield Label("= Net", classes="sb-lbl")
                yield Label("", id="mon-net", classes="sb-val")

    def refresh_data(self, data: dict) -> None:
        accounts = data.get("accounts", {})
        total    = 0.0
        for acc in ACCOUNTS:
            bal    = accounts.get(acc, 0)
            total += bal
            color  = "green" if bal >= 0 else "red"
            self.query_one(f"#bal-{acc.lower()}", Label).update(
                f"[{color}]{fmt_rp_short(bal)}[/]")
        tc = "green" if total >= 0 else "red"
        self.query_one("#bal-total", Label).update(
            f"[{tc} bold]{fmt_rp_short(total)}[/]")

        today = date.today()
        ms    = get_monthly_summary(data["transactions"], today.year, today.month)
        self.query_one("#mon-inc", Label).update(
            f"[green]{fmt_rp_short(ms['income'])}[/]")
        self.query_one("#mon-exp", Label).update(
            f"[red]{fmt_rp_short(ms['expense'])}[/]")
        nc = "green" if ms["net"] >= 0 else "red"
        self.query_one("#mon-net", Label).update(
            f"[{nc}]{fmt_rp_short(ms['net'])}[/]")
