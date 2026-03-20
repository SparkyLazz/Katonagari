from __future__ import annotations
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.validation import Length, Number
from textual.widget import Widget
from textual.widgets import DataTable, Input, Label, Static, TabbedContent, TabPane

from services.financeService import (
    CATEGORIES,
    FinanceService,
    Transaction,
    fmt_amount,
    fmt_change,
)


# ─── Add Transaction Modal ────────────────────────────────────────────────────

class AddTransactionScreen(ModalScreen[Transaction | None]):
    DEFAULT_CSS = """
        AddTransactionScreen { align: center middle; background: transparent; }
        AddTransactionScreen #dialog {
            width: 52; height: auto;
            border: round $primary; background: transparent; padding: 1 2;
        }
        AddTransactionScreen #title       { text-style: bold; color: $warning; margin-bottom: 1; }
        AddTransactionScreen .field-label { color: $text-muted; margin-top: 1; height: 1; }
        AddTransactionScreen Input        { width: 100%; }
        AddTransactionScreen #error       { color: $error; height: 1; margin-top: 1; }
        AddTransactionScreen #hint        { color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "submit", "Save"),
    ]

    def __init__(self, account_options: list[tuple[str, str]],
                 fixed_account: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._acct_options = account_options
        self._fixed_account = fixed_account  # pre-set when inside a specific tab

    def compose(self) -> ComposeResult:
        cat_list = ", ".join(CATEGORIES)
        acct_list = ", ".join(f"{n} ({a})" for n, a in self._acct_options)
        with Vertical(id="dialog"):
            yield Static("▸ ADD TRANSACTION", id="title")
            yield Label("Date  (YYYY-MM-DD)", classes="field-label")
            yield Input(placeholder="2024-01-15", id="inp-date",
                        validators=[Length(minimum=10, maximum=10)])
            yield Label("Description", classes="field-label")
            yield Input(placeholder="Salary", id="inp-desc",
                        validators=[Length(minimum=1)])
            yield Label(f"Category  ({cat_list})", classes="field-label")
            yield Input(placeholder="Food", id="inp-cat")
            if self._fixed_account:
                acct_name = next(
                    (n for n, a in self._acct_options if a == self._fixed_account),
                    self._fixed_account,
                )
                yield Label(f"Account:  [bold]{acct_name}[/]", classes="field-label", markup=True)
            else:
                yield Label(f"Account  ({acct_list})", classes="field-label")
                yield Input(placeholder="seabank", id="inp-acct")
            yield Label("Amount  (negative = expense)", classes="field-label")
            yield Input(placeholder="-1200", id="inp-amount",
                        validators=[Number()])
            yield Static("", id="error")
            yield Label("[dim]ctrl+s save · esc cancel[/]", id="hint", markup=True)

    def _resolve_account(self, val: str) -> str | None:
        v = val.strip().lower()
        for name, aid in self._acct_options:
            if aid.lower() == v or name.lower() == v:
                return aid
        return None

    def _save(self) -> None:
        from datetime import datetime
        date_val   = self.query_one("#inp-date", Input).value.strip()
        desc_val   = self.query_one("#inp-desc", Input).value.strip()
        cat_val    = self.query_one("#inp-cat",  Input).value.strip()
        amount_val = self.query_one("#inp-amount", Input).value.strip()

        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            self.query_one("#error", Static).update("⚠ Date must be YYYY-MM-DD.")
            return
        if not desc_val:
            self.query_one("#error", Static).update("⚠ Description is required.")
            return
        if cat_val not in CATEGORIES:
            self.query_one("#error", Static).update(f"⚠ Category must be: {', '.join(CATEGORIES)}")
            return

        # Resolve account
        if self._fixed_account:
            acct_id = self._fixed_account
        else:
            acct_raw = self.query_one("#inp-acct", Input).value.strip()
            acct_id  = self._resolve_account(acct_raw)
            if not acct_id:
                self.query_one("#error", Static).update(f"⚠ Unknown account: {acct_raw}")
                return

        try:
            amount = int(amount_val)
        except ValueError:
            self.query_one("#error", Static).update("⚠ Amount must be a whole number.")
            return

        self.dismiss(Transaction(date_val, desc_val, cat_val, amount, account=acct_id))

    def action_cancel(self) -> None: self.dismiss(None)
    def action_submit(self) -> None: self._save()


# ─── Confirm Delete Modal ─────────────────────────────────────────────────────

class ConfirmDeleteScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
        ConfirmDeleteScreen { align: center middle; }
        ConfirmDeleteScreen #dialog {
            width: 46; height: auto;
            border: round $error; background: $surface; padding: 1 2;
        }
        ConfirmDeleteScreen #title { text-style: bold; color: $error; margin-bottom: 1; }
        ConfirmDeleteScreen #desc  { color: $text-muted; margin-bottom: 1; }
        ConfirmDeleteScreen #hint  { color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel",  "Cancel"),
        Binding("y",      "confirm", "Delete"),
    ]

    def __init__(self, tx: Transaction, acct_name: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._tx = tx
        self._acct_name = acct_name

    def compose(self) -> ComposeResult:
        acct_info = f" [dim]@[/]{self._acct_name}" if self._acct_name else ""
        with Vertical(id="dialog"):
            yield Static("▸ CONFIRM DELETE", id="title")
            yield Static(
                f"[dim]Delete[/] [bold]{self._tx.desc}[/] "
                f"[dim]on[/] {self._tx.display_date}{acct_info} "
                f"[dim]([/]{fmt_amount(self._tx.amount)}[dim])?[/]",
                id="desc", markup=True,
            )
            yield Label("[dim]y confirm · esc cancel[/]", id="hint", markup=True)

    def action_cancel(self)  -> None: self.dismiss(False)
    def action_confirm(self) -> None: self.dismiss(True)


# ─── TransactionLog ───────────────────────────────────────────────────────────

class TransactionLog(Widget):
    class DataChanged(Message):
        pass

    DEFAULT_CSS = """
        TransactionLog {
            border: round $primary; width: 100%; height: 1fr;
        }
        TransactionLog DataTable { height: 1fr; background: transparent; }
    """

    BINDINGS = [
        Binding("a", "add_transaction",    "Add",    show=True),
        Binding("d", "delete_transaction", "Delete", show=True),
    ]

    def __init__(self, *, service: FinanceService, account: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service
        self._account = account  # None = all

    def compose(self) -> ComposeResult:
        self.border_title    = "Transaction Log"
        self.border_subtitle = "a add · d delete"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        self._build_table()

    def _build_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        if self._account is None:
            table.add_columns("Date", "Description", "Category", "Account", "Amount", "Balance")
        else:
            table.add_columns("Date", "Description", "Category", "Amount", "Balance")
        table.cursor_type = "row"
        txs = self._svc.transactions_for(self._account)
        for tx in txs:
            acct_name = self._svc.account_name(tx.account)
            if self._account is None:
                table.add_row(
                    f"[dim]{tx.display_date}[/]", tx.desc, f"[dim]{tx.cat}[/]",
                    f"[dim]{acct_name}[/]", fmt_amount(tx.amount), f"[cyan]RP{tx.balance:,}[/]",
                )
            else:
                table.add_row(
                    f"[dim]{tx.display_date}[/]", tx.desc, f"[dim]{tx.cat}[/]",
                    fmt_amount(tx.amount), f"[cyan]RP{tx.balance:,}[/]",
                )
        count = len(txs)
        self.border_subtitle = f"a add · d delete · {count} rows"

    def action_add_transaction(self) -> None:
        acct_options = self._svc.account_options()
        if not acct_options:
            return
        def _on_result(tx: Transaction | None) -> None:
            if tx is None: return
            self._svc.add(tx)
            self._build_table()
            self.post_message(TransactionLog.DataChanged())
        self.app.push_screen(
            AddTransactionScreen(acct_options, fixed_account=self._account),
            _on_result,
        )

    def action_delete_transaction(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count == 0: return
        index = table.cursor_row
        txs   = self._svc.transactions_for(self._account)
        if index >= len(txs): return
        tx = txs[index]
        acct_name = self._svc.account_name(tx.account)
        def _on_result(confirmed: bool) -> None:
            if confirmed:
                self._svc.remove(index, self._account)
                self._build_table()
                self.post_message(TransactionLog.DataChanged())
        self.app.push_screen(ConfirmDeleteScreen(tx, acct_name), _on_result)

    def refresh_data(self) -> None:
        self._build_table()


# ─── BalanceHistory ───────────────────────────────────────────────────────────

class BalanceHistory(Widget):
    DEFAULT_CSS = """
        BalanceHistory {
            border: round $accent; width: 100%; height: 1fr;
        }
        BalanceHistory DataTable { height: 1fr; background: transparent; }
    """

    def __init__(self, *, service: FinanceService, account: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service
        self._account = account

    def compose(self) -> ComposeResult:
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Month", "Income", "Expenses", "Net", "Net Worth", "Change")
        table.cursor_type = "row"
        self._fill_table()

    def _fill_table(self) -> None:
        summaries = self._svc.monthly_summaries(self._account)
        table     = self.query_one(DataTable)
        table.clear()
        if summaries:
            self.border_title    = "Balance History"
            self.border_subtitle = f"{summaries[0].month} – {summaries[-1].month}"
        else:
            self.border_title    = "Balance History"
            self.border_subtitle = ""
        for s in summaries:
            table.add_row(
                f"[dim]{s.month}[/]",
                fmt_amount(s.income,    sign=False),
                fmt_amount(-s.expenses, sign=False),
                fmt_amount(s.net),
                f"[cyan]RP{s.net_worth:,}[/]",
                fmt_change(s.change),
            )

    def refresh_data(self) -> None:
        self._fill_table()

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        self._fill_table()


# ─── Log (composite with account tabs) ───────────────────────────────────────

class Log(Widget):
    DEFAULT_CSS = """
        Log TabbedContent { height: 1fr; }
        Log TabPane        { height: 1fr; padding: 0; }
    """

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("All", id="log-all"):
                with Vertical():
                    yield TransactionLog(service=self._svc, account=None, id="tlog-all")
                    yield BalanceHistory(service=self._svc, account=None, id="bh-all")
            for acct in self._svc.accounts:
                with TabPane(acct.name, id=f"log-{acct.id}"):
                    with Vertical():
                        yield TransactionLog(service=self._svc, account=acct.id, id=f"tlog-{acct.id}")
                        yield BalanceHistory(service=self._svc, account=acct.id, id=f"bh-{acct.id}")

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        """When any tab's log changes, refresh all tabs."""
        for tlog in self.query(TransactionLog):
            tlog.refresh_data()
        for bh in self.query(BalanceHistory):
            bh.refresh_data()