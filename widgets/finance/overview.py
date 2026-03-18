from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static

from services.financeService import FinanceService, fmt_amount
from widgets.finance.log import TransactionLog


# ─── StatCard ─────────────────────────────────────────────────────────────────

class StatCard(Widget):
    DEFAULT_CSS = """
    StatCard {
        border: round;
        padding: 0 1;
        width: 1fr;
        height: 1fr;
    }
    StatCard .card-value { text-style: bold; color: $text; }
    StatCard .card-diff  { color: $text-muted; }
    StatCard.success { border: round $success; }
    StatCard.error   { border: round $error;   }
    StatCard.accent  { border: round $accent;  }
    StatCard.success .card-value { color: $success; }
    StatCard.error   .card-value { color: $error;   }
    StatCard.accent  .card-value { color: $accent;  }
    """

    def __init__(self, label: str, value: str, diff: str,
                 color: str = "success", **kwargs) -> None:
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.diff  = diff
        self.color = color

    def on_mount(self) -> None:
        self.border_title = self.label
        self.add_class(self.color)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.value, classes="card-value", id=f"val-{self.id}")
            yield Label(self.diff,   classes="card-diff",  id=f"dif-{self.id}")

    def set_content(self, value: str, diff: str) -> None:
        self.query_one(f"#val-{self.id}", Static).update(value)
        self.query_one(f"#dif-{self.id}", Label).update(diff)


# ─── SummaryPanel ─────────────────────────────────────────────────────────────

class SummaryPanel(Widget):
    DEFAULT_CSS = """
    SummaryPanel {
        border: round $primary;
        width: 28;
        height: 1fr;
        padding: 1 2;
    }
    .big-balance { text-style: bold; color: $success; }
    .divider     { color: $primary; }
    .row-label   { color: $text-muted; width: 12; }
    .row-value   { text-style: bold; }
    """

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        self.border_title = "Summary"
        s = self._svc.current_stats()
        yield Static(f"${s.get('net_worth', 0):,}", classes="big-balance", id="sum-nw")
        yield Static("─" * 20, classes="divider")

        with Horizontal():
            yield Label("Income",      classes="row-label")
            yield Static(f"${s.get('income', 0):,}",      classes="row-value success", id="sum-income")
        with Horizontal():
            yield Label("Expenses",    classes="row-label")
            yield Static(f"${s.get('expenses', 0):,}",    classes="row-value error",   id="sum-expenses")
        with Horizontal():
            yield Label("Savings",     classes="row-label")
            yield Static(f"${s.get('net_savings', 0):,}", classes="row-value accent",  id="sum-savings")

        yield Static("─" * 20, classes="divider")

        with Horizontal():
            yield Label("Investments", classes="row-label")
            yield Static(f"${s.get('investments', 0):,}", classes="row-value",        id="sum-invest")
        with Horizontal():
            yield Label("Debt",        classes="row-label")
            yield Static(f"-${s.get('debt', 0):,}",       classes="row-value error",  id="sum-debt")

        yield Static("─" * 20, classes="divider")

        sr       = s.get("save_rate", 0.0)
        sr_ch    = s.get("save_rate_change", 0.0)
        sr_sign  = "+" if sr_ch >= 0 else ""
        sr_color = "success" if sr_ch >= 0 else "error"

        with Horizontal():
            yield Label("Save rate",   classes="row-label")
            yield Static(f"{sr:.1f}%", classes="row-value accent",    id="sum-saverate")
        with Horizontal():
            yield Label("vs last mo.", classes="row-label")
            yield Static(f"{sr_sign}{sr_ch:.1f}%",
                         classes=f"row-value {sr_color}", id="sum-srchange")

    def refresh_data(self) -> None:
        s        = self._svc.current_stats()
        sr       = s.get("save_rate", 0.0)
        sr_ch    = s.get("save_rate_change", 0.0)
        sr_sign  = "+" if sr_ch >= 0 else ""
        sr_color = "success" if sr_ch >= 0 else "error"

        self.query_one("#sum-nw",       Static).update(f"${s.get('net_worth', 0):,}")
        self.query_one("#sum-income",   Static).update(f"${s.get('income', 0):,}")
        self.query_one("#sum-expenses", Static).update(f"${s.get('expenses', 0):,}")
        self.query_one("#sum-savings",  Static).update(f"${s.get('net_savings', 0):,}")
        self.query_one("#sum-invest",   Static).update(f"${s.get('investments', 0):,}")
        self.query_one("#sum-debt",     Static).update(f"-${s.get('debt', 0):,}")
        self.query_one("#sum-saverate", Static).update(f"{sr:.1f}%")
        self.query_one("#sum-srchange", Static).update(f"{sr_sign}{sr_ch:.1f}%")
        self.query_one("#sum-srchange", Static).remove_class("success", "error")
        self.query_one("#sum-srchange", Static).add_class(sr_color)

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        self.refresh_data()


# ─── TransactionTable ─────────────────────────────────────────────────────────

class TransactionTable(Widget):
    DEFAULT_CSS = """
    TransactionTable {
        width: 1fr;
        height: 1fr;
        border: round $accent;
        padding: 0;
    }
    TransactionTable DataTable        { height: 1fr; background: transparent; }
    DataTable > .datatable--header    { background: $panel;  color: $text-muted; text-style: bold; }
    DataTable > .datatable--odd-row   { background: $surface; }
    DataTable > .datatable--even-row  { background: $panel;   }
    DataTable > .datatable--cursor    { background: $accent 20%; color: $text; }
    """

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        stats = self._svc.current_stats()
        self.border_title    = "Transactions"
        self.border_subtitle = stats.get("current_month", "")
        table = DataTable(zebra_stripes=True)
        table.add_columns("Date", "Description", "Category", "Amount")
        yield table

    def on_mount(self) -> None:
        self._fill_table()

    def _fill_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for tx in self._svc.transactions[-10:]:
            table.add_row(
                f"[dim]{tx.display_date}[/]",
                tx.desc,
                f"[dim]{tx.cat}[/]",
                fmt_amount(tx.amount),
            )
        stats = self._svc.current_stats()
        self.border_subtitle = stats.get("current_month", "")

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        self._fill_table()


# ─── Overview ─────────────────────────────────────────────────────────────────

class Overview(Widget):
    DEFAULT_CSS = """
        Overview { width: 100%; height: 1fr; padding: 1 2; }
        .stat-row   { height: 7; }
        .bottom-row { width: 100%; height: 1fr; }
    """

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def _stat_values(self) -> dict:
        s        = self._svc.current_stats()
        nw       = s.get("net_worth",     0)
        income   = s.get("income",        0)
        expenses = s.get("expenses",      0)
        net_sav  = s.get("net_savings",   0)
        save_r   = s.get("save_rate",     0.0)
        nw_pct   = s.get("nw_change_pct", 0.0)
        inc_ch   = s.get("income_change", 0)
        exp_pct  = s.get("expenses_pct",  0.0)
        return dict(
            nw=nw, income=income, expenses=expenses, net_sav=net_sav,
            save_r=save_r, nw_pct=nw_pct, inc_ch=inc_ch, exp_pct=exp_pct,
        )

    def compose(self) -> ComposeResult:
        v = self._stat_values()
        nw_sign  = "+" if v["nw_pct"]  >= 0 else ""
        inc_sign = "+" if v["inc_ch"]  >= 0 else ""
        exp_sign = "+" if v["exp_pct"] >= 0 else ""

        with Horizontal(classes="stat-row"):
            yield StatCard("Total Balance",  f"${v['nw']:,}",
                           f"{nw_sign}{v['nw_pct']:.1f}% this month",  "success",
                           id="card-balance")
            yield StatCard("Monthly Income", f"${v['income']:,}",
                           f"{inc_sign}${abs(v['inc_ch']):,} vs last month", "success",
                           id="card-income")
            yield StatCard("Expenses",       f"${v['expenses']:,}",
                           f"{exp_sign}{v['exp_pct']:.1f}% vs last month",  "error",
                           id="card-expenses")
            yield StatCard("Net Savings",    f"${v['net_sav']:,}",
                           f"{v['save_r']:.1f}% save rate",             "accent",
                           id="card-savings")

        with Horizontal(classes="bottom-row"):
            yield SummaryPanel(service=self._svc)
            yield TransactionTable(service=self._svc)

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        v = self._stat_values()
        nw_sign  = "+" if v["nw_pct"]  >= 0 else ""
        inc_sign = "+" if v["inc_ch"]  >= 0 else ""
        exp_sign = "+" if v["exp_pct"] >= 0 else ""

        self.query_one("#card-balance",  StatCard).set_content(
            f"${v['nw']:,}",
            f"{nw_sign}{v['nw_pct']:.1f}% this month",
        )
        self.query_one("#card-income",   StatCard).set_content(
            f"${v['income']:,}",
            f"{inc_sign}${abs(v['inc_ch']):,} vs last month",
        )
        self.query_one("#card-expenses", StatCard).set_content(
            f"${v['expenses']:,}",
            f"{exp_sign}{v['exp_pct']:.1f}% vs last month",
        )
        self.query_one("#card-savings",  StatCard).set_content(
            f"${v['net_sav']:,}",
            f"{v['save_r']:.1f}% save rate",
        )