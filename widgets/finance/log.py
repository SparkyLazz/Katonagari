"""
widgets/finance/log.py — Transaction log + balance history.
Per-account tabs in compose(). Keybinds: a=add d=delete
"""
from __future__ import annotations
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.validation import Length, Number
from textual.widget import Widget
from textual.widgets import DataTable, Input, Label, Static, TabbedContent, TabPane
from services.financeService import CATEGORIES, FinanceService, Transaction, fmt, fmt_change


class AddTransactionScreen(ModalScreen[Transaction | None]):
    DEFAULT_CSS = """
    AddTransactionScreen         { align: center middle; background: transparent; }
    AddTransactionScreen #dialog { width: 52; height: auto; border: round $primary; background: transparent; padding: 1 2; }
    AddTransactionScreen #title  { text-style: bold; color: $warning; margin-bottom: 1; }
    AddTransactionScreen .fl     { color: $text-muted; margin-top: 1; height: 1; }
    AddTransactionScreen Input   { width: 100%; }
    AddTransactionScreen #error  { color: $error; height: 1; margin-top: 1; }
    AddTransactionScreen #hint   { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [Binding("escape","cancel"), Binding("ctrl+s","submit")]
    def __init__(self, acct_name: str, acct_id: str, **kw) -> None:
        super().__init__(**kw); self._aname, self._aid = acct_name, acct_id
    def compose(self) -> ComposeResult:
        cats = ", ".join(CATEGORIES)
        with Vertical(id="dialog"):
            yield Static("▸ ADD TRANSACTION", id="title")
            yield Label(f"Account: [bold]{self._aname}[/]", classes="fl", markup=True)
            yield Label("Date (YYYY-MM-DD)", classes="fl")
            yield Input(placeholder="2024-01-15", id="inp-date", validators=[Length(minimum=10,maximum=10)])
            yield Label("Description", classes="fl")
            yield Input(placeholder="Salary", id="inp-desc", validators=[Length(minimum=1)])
            yield Label(f"Category ({cats})", classes="fl")
            yield Input(placeholder="Food", id="inp-cat")
            yield Label("Amount (negative = expense)", classes="fl")
            yield Input(placeholder="-1200", id="inp-amt", validators=[Number()])
            yield Static("", id="error")
            yield Label("[dim]ctrl+s save · esc cancel[/]", id="hint", markup=True)
    def _save(self) -> None:
        from datetime import datetime as dt
        date = self.query_one("#inp-date",Input).value.strip()
        desc = self.query_one("#inp-desc",Input).value.strip()
        cat = self.query_one("#inp-cat",Input).value.strip()
        amt = self.query_one("#inp-amt",Input).value.strip()
        err = self.query_one("#error",Static)
        try: dt.strptime(date,"%Y-%m-%d")
        except ValueError: err.update("⚠ YYYY-MM-DD required."); return
        if not desc: err.update("⚠ Description required."); return
        if cat not in CATEGORIES: err.update(f"⚠ Category: {', '.join(CATEGORIES)}"); return
        try: amount = int(amt)
        except ValueError: err.update("⚠ Integer required."); return
        self.dismiss(Transaction(date, desc, cat, amount, self._aid))
    def action_cancel(self) -> None: self.dismiss(None)
    def action_submit(self) -> None: self._save()


class ConfirmDeleteScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmDeleteScreen         { align: center middle; }
    ConfirmDeleteScreen #dialog { width: 46; height: auto; border: round $error; background: $surface; padding: 1 2; }
    ConfirmDeleteScreen #title  { text-style: bold; color: $error; margin-bottom: 1; }
    ConfirmDeleteScreen #desc   { color: $text-muted; margin-bottom: 1; }
    ConfirmDeleteScreen #hint   { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [Binding("escape","cancel"), Binding("y","confirm")]
    def __init__(self, tx: Transaction, **kw) -> None:
        super().__init__(**kw); self._tx = tx
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("▸ CONFIRM DELETE", id="title")
            yield Static(f"[dim]Delete[/] [bold]{self._tx.desc}[/] [dim]on[/] "
                         f"{self._tx.display_date} [dim]([/]{fmt(self._tx.amount)}[dim])?[/]",
                         id="desc", markup=True)
            yield Label("[dim]y confirm · esc cancel[/]", id="hint", markup=True)
    def action_cancel(self) -> None: self.dismiss(False)
    def action_confirm(self) -> None: self.dismiss(True)


class TransactionLog(Widget):
    class DataChanged(Message): pass
    DEFAULT_CSS = """
    TransactionLog           { border: round $primary; width: 100%; height: 1fr; }
    TransactionLog DataTable { height: 1fr; background: transparent; }
    """
    BINDINGS = [Binding("a","add_transaction","Add",show=True), Binding("d","delete_transaction","Delete",show=True)]

    def __init__(self, *, service: FinanceService, account: str, **kw) -> None:
        super().__init__(**kw); self._svc, self._acct = service, account

    def compose(self) -> ComposeResult:
        self.border_title = "Transaction Log"
        self.border_subtitle = "a add · d delete"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None: self._build()

    def _build(self) -> None:
        t = self.query_one(DataTable); t.clear(columns=True)
        t.add_columns("Date","Description","Category","Amount")
        t.cursor_type = "row"
        for tx in self._svc.transactions_for(self._acct):
            t.add_row(f"[dim]{tx.display_date}[/]", tx.desc, f"[dim]{tx.cat}[/]", fmt(tx.amount))
        self.border_subtitle = f"a add · d delete · {t.row_count} rows"

    def action_add_transaction(self) -> None:
        aname = self._svc.account_name(self._acct)
        def cb(tx: Transaction|None) -> None:
            if not tx: return
            self._svc.add(tx); self._build()
            self.post_message(self.DataChanged())
        self.app.push_screen(AddTransactionScreen(aname, self._acct), cb)

    def action_delete_transaction(self) -> None:
        t = self.query_one(DataTable)
        if t.row_count == 0: return
        idx = t.cursor_row
        txs = self._svc.transactions_for(self._acct)
        if idx >= len(txs): return
        def cb(ok: bool) -> None:
            if ok:
                self._svc.remove(idx, self._acct); self._build()
                self.post_message(self.DataChanged())
        self.app.push_screen(ConfirmDeleteScreen(txs[idx]), cb)

    def refresh_data(self) -> None: self._build()


class BalanceHistory(Widget):
    DEFAULT_CSS = """
    BalanceHistory           { border: round $accent; width: 100%; height: 1fr; }
    BalanceHistory DataTable { height: 1fr; background: transparent; }
    """
    def __init__(self, *, service: FinanceService, account: str, **kw) -> None:
        super().__init__(**kw); self._svc, self._acct = service, account

    def compose(self) -> ComposeResult:
        self.border_title = "Balance History"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        t = self.query_one(DataTable)
        t.add_columns("Month","Income","Expenses","Net"); t.cursor_type = "row"
        self._fill()

    def _fill(self) -> None:
        sums = self._svc.monthly_summaries(self._acct)
        t = self.query_one(DataTable); t.clear()
        self.border_subtitle = f"{sums[0].month} – {sums[-1].month}" if sums else ""
        for s in sums:
            t.add_row(f"[dim]{s.month}[/]", fmt(s.income,sign=False),
                       fmt(-s.expenses,sign=False), fmt(s.net))

    def refresh_data(self) -> None: self._fill()


class Log(Widget):
    DEFAULT_CSS = """
    Log TabbedContent { height: 1fr; }
    Log TabPane       { height: 1fr; padding: 0; }
    """
    def __init__(self, *, service: FinanceService, **kw) -> None:
        super().__init__(**kw); self._svc = service

    def compose(self) -> ComposeResult:
        with TabbedContent():
            for a in self._svc.accounts:
                with TabPane(a.name, id=f"log-{a.id}"):
                    with Vertical():
                        yield TransactionLog(service=self._svc, account=a.id, id=f"tl-{a.id}")
                        yield BalanceHistory(service=self._svc, account=a.id, id=f"bh-{a.id}")

    def refresh_data(self) -> None:
        for w in self.query(TransactionLog): w.refresh_data()
        for w in self.query(BalanceHistory): w.refresh_data()

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        self.refresh_data()