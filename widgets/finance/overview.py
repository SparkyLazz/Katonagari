from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static, TabbedContent, TabPane

from services.financeService import FinanceService, fmt_amount
from widgets.finance.log import TransactionLog


# ─── StatCard ─────────────────────────────────────────────────────────────────

class StatCard(Widget):
    DEFAULT_CSS = """
    StatCard {
        border: round; padding: 0 1; width: 1fr; height: 1fr;
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
        border: round $primary; width: 28; height: 1fr; padding: 1 2;
    }
    .big-balance { text-style: bold; color: $success; }
    .divider     { color: $primary; }
    .row-label   { color: $text-muted; width: 12; }
    .row-value   { text-style: bold; }
    """

    def __init__(self, *, service: FinanceService, account: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service
        self._account = account

    def compose(self) -> ComposeResult:
        self.border_title = "Summary"
        s = self._svc.current_stats(self._account)
        yield Static(f"RP{s.get('net_worth', 0):,}", classes="big-balance", id=f"sum-nw-{self.id}")
        yield Static("─" * 20, classes="divider")
        with Horizontal():
            yield Label("Income",      classes="row-label")
            yield Static(f"RP{s.get('income', 0):,}",      classes="row-value success", id=f"sum-inc-{self.id}")
        with Horizontal():
            yield Label("Expenses",    classes="row-label")
            yield Static(f"RP{s.get('expenses', 0):,}",    classes="row-value error",   id=f"sum-exp-{self.id}")
        with Horizontal():
            yield Label("Savings",     classes="row-label")
            yield Static(f"RP{s.get('net_savings', 0):,}", classes="row-value accent",  id=f"sum-sav-{self.id}")
        yield Static("─" * 20, classes="divider")
        with Horizontal():
            yield Label("Investments", classes="row-label")
            yield Static(f"RP{s.get('investments', 0):,}", classes="row-value",        id=f"sum-inv-{self.id}")
        with Horizontal():
            yield Label("Debt",        classes="row-label")
            yield Static(f"-RP{s.get('debt', 0):,}",       classes="row-value error",  id=f"sum-dbt-{self.id}")
        yield Static("─" * 20, classes="divider")
        sr    = s.get("save_rate", 0.0)
        sr_ch = s.get("save_rate_change", 0.0)
        with Horizontal():
            yield Label("Save rate",   classes="row-label")
            yield Static(f"{sr:.1f}%", classes="row-value accent", id=f"sum-sr-{self.id}")
        with Horizontal():
            yield Label("vs last mo.", classes="row-label")
            sr_sign = "+" if sr_ch >= 0 else ""
            sr_col  = "success" if sr_ch >= 0 else "error"
            yield Static(f"{sr_sign}{sr_ch:.1f}%", classes=f"row-value {sr_col}", id=f"sum-src-{self.id}")

    def refresh_data(self) -> None:
        s     = self._svc.current_stats(self._account)
        sr    = s.get("save_rate", 0.0)
        sr_ch = s.get("save_rate_change", 0.0)
        sr_sign = "+" if sr_ch >= 0 else ""
        sr_col  = "success" if sr_ch >= 0 else "error"
        self.query_one(f"#sum-nw-{self.id}",  Static).update(f"RP{s.get('net_worth', 0):,}")
        self.query_one(f"#sum-inc-{self.id}",  Static).update(f"RP{s.get('income', 0):,}")
        self.query_one(f"#sum-exp-{self.id}",  Static).update(f"RP{s.get('expenses', 0):,}")
        self.query_one(f"#sum-sav-{self.id}",  Static).update(f"RP{s.get('net_savings', 0):,}")
        self.query_one(f"#sum-inv-{self.id}",  Static).update(f"RP{s.get('investments', 0):,}")
        self.query_one(f"#sum-dbt-{self.id}",  Static).update(f"-RP{s.get('debt', 0):,}")
        self.query_one(f"#sum-sr-{self.id}",   Static).update(f"{sr:.1f}%")
        src = self.query_one(f"#sum-src-{self.id}", Static)
        src.update(f"{sr_sign}{sr_ch:.1f}%")
        src.remove_class("success", "error")
        src.add_class(sr_col)

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        self.refresh_data()


# ─── TransactionTable ─────────────────────────────────────────────────────────

class TransactionTable(Widget):
    DEFAULT_CSS = """
    TransactionTable {
        width: 1fr; height: 1fr; border: round $accent; padding: 0;
    }
    TransactionTable DataTable        { height: 1fr; background: transparent; }
    DataTable > .datatable--header    { background: $panel;  color: $text-muted; text-style: bold; }
    DataTable > .datatable--odd-row   { background: $surface; }
    DataTable > .datatable--even-row  { background: $panel;   }
    DataTable > .datatable--cursor    { background: $accent 20%; color: $text; }
    """

    def __init__(self, *, service: FinanceService, account: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service
        self._account = account

    def compose(self) -> ComposeResult:
        stats = self._svc.current_stats(self._account)
        self.border_title    = "Transactions"
        self.border_subtitle = stats.get("current_month", "")
        table = DataTable(zebra_stripes=True)
        if self._account is None:
            table.add_columns("Date", "Description", "Account", "Category", "Amount")
        else:
            table.add_columns("Date", "Description", "Category", "Amount")
        yield table

    def on_mount(self) -> None:
        self._fill_table()

    def _fill_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        txs = self._svc.transactions_for(self._account)
        for tx in txs[-10:]:
            if self._account is None:
                acct_name = self._svc.account_name(tx.account)
                table.add_row(
                    f"[dim]{tx.display_date}[/]", tx.desc,
                    f"[dim]{acct_name}[/]", f"[dim]{tx.cat}[/]", fmt_amount(tx.amount),
                )
            else:
                table.add_row(
                    f"[dim]{tx.display_date}[/]", tx.desc,
                    f"[dim]{tx.cat}[/]", fmt_amount(tx.amount),
                )
        stats = self._svc.current_stats(self._account)
        self.border_subtitle = stats.get("current_month", "")

    def refresh_data(self) -> None:
        self._fill_table()

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        self._fill_table()


# ─── OverviewContent (one account view) ──────────────────────────────────────

class OverviewContent(Widget):
    DEFAULT_CSS = """
        OverviewContent { width: 100%; height: 1fr; padding: 1 2; }
        .stat-row   { height: 7; }
        .bottom-row { width: 100%; height: 1fr; }
    """

    def __init__(self, *, service: FinanceService, account: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service
        self._account = account

    def _stat_values(self) -> dict:
        s = self._svc.current_stats(self._account)
        return dict(
            nw=s.get("net_worth", 0), income=s.get("income", 0),
            expenses=s.get("expenses", 0), net_sav=s.get("net_savings", 0),
            save_r=s.get("save_rate", 0.0), nw_pct=s.get("nw_change_pct", 0.0),
            inc_ch=s.get("income_change", 0), exp_pct=s.get("expenses_pct", 0.0),
        )

    def compose(self) -> ComposeResult:
        v = self._stat_values()
        nw_s  = "+" if v["nw_pct"]  >= 0 else ""
        inc_s = "+" if v["inc_ch"]  >= 0 else ""
        exp_s = "+" if v["exp_pct"] >= 0 else ""

        sfx = self._account or "all"
        with Horizontal(classes="stat-row"):
            yield StatCard("Total Balance",  f"RP{v['nw']:,}",
                           f"{nw_s}{v['nw_pct']:.1f}% this month",   "success", id=f"card-bal-{sfx}")
            yield StatCard("Monthly Income", f"RP{v['income']:,}",
                           f"{inc_s}RP{abs(v['inc_ch']):,} vs last",  "success", id=f"card-inc-{sfx}")
            yield StatCard("Expenses",       f"RP{v['expenses']:,}",
                           f"{exp_s}{v['exp_pct']:.1f}% vs last",     "error",   id=f"card-exp-{sfx}")
            yield StatCard("Net Savings",    f"RP{v['net_sav']:,}",
                           f"{v['save_r']:.1f}% save rate",           "accent",  id=f"card-sav-{sfx}")

        with Horizontal(classes="bottom-row"):
            yield SummaryPanel(service=self._svc, account=self._account, id=f"sumpan-{sfx}")
            yield TransactionTable(service=self._svc, account=self._account, id=f"txtbl-{sfx}")

    def refresh_data(self) -> None:
        v = self._stat_values()
        nw_s  = "+" if v["nw_pct"]  >= 0 else ""
        inc_s = "+" if v["inc_ch"]  >= 0 else ""
        exp_s = "+" if v["exp_pct"] >= 0 else ""
        sfx = self._account or "all"

        self.query_one(f"#card-bal-{sfx}", StatCard).set_content(
            f"RP{v['nw']:,}", f"{nw_s}{v['nw_pct']:.1f}% this month")
        self.query_one(f"#card-inc-{sfx}", StatCard).set_content(
            f"RP{v['income']:,}", f"{inc_s}RP{abs(v['inc_ch']):,} vs last")
        self.query_one(f"#card-exp-{sfx}", StatCard).set_content(
            f"RP{v['expenses']:,}", f"{exp_s}{v['exp_pct']:.1f}% vs last")
        self.query_one(f"#card-sav-{sfx}", StatCard).set_content(
            f"RP{v['net_sav']:,}", f"{v['save_r']:.1f}% save rate")

        try: self.query_one(f"#sumpan-{sfx}", SummaryPanel).refresh_data()
        except Exception: pass
        try: self.query_one(f"#txtbl-{sfx}", TransactionTable).refresh_data()
        except Exception: pass


# ─── Overview (tabbed by account) ─────────────────────────────────────────────

class Overview(Widget):
    DEFAULT_CSS = """
        Overview { width: 100%; height: 1fr; }
        Overview TabbedContent { height: 1fr; }
        Overview TabPane       { height: 1fr; padding: 0; }
    """

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("All", id="ov-all"):
                yield OverviewContent(service=self._svc, account=None, id="ovc-all")
            for acct in self._svc.accounts:
                with TabPane(acct.name, id=f"ov-{acct.id}"):
                    yield OverviewContent(service=self._svc, account=acct.id, id=f"ovc-{acct.id}")

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        for ovc in self.query(OverviewContent):
            ovc.refresh_data()