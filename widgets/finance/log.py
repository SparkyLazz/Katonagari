from __future__ import annotations
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.validation import Length, Number
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from services.financeService import (
    CATEGORY_OPTIONS,
    FinanceService,
    Transaction,
    fmt_amount,
    fmt_change,
)

# ─── Add Transaction Modal ────────────────────────────────────────────────────

class AddTransactionScreen(ModalScreen[Transaction | None]):
    DEFAULT_CSS = """
        AddTransactionScreen {
            align: center middle;
            background: transparent;
        }
        AddTransactionScreen #dialog {
            width: 52;
            height: auto;
            border: round $primary;
            background: transparent;
            padding: 1 2;
        }
        AddTransactionScreen #title {
            text-style: bold;
            color: $warning;
            margin-bottom: 1;
        }
        AddTransactionScreen .field-label {
            color: $text-muted;
            margin-top: 1;
            height: 1;
        }
        AddTransactionScreen Input  { width: 100%; }
        AddTransactionScreen Select { width: 100%; }
        AddTransactionScreen #error {
            color: $error;
            height: 1;
            margin-top: 1;
        }
        AddTransactionScreen #btn-row {
            margin-top: 2;
            height: 3;
            align: right middle;
        }
        AddTransactionScreen Button { margin-left: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "submit", "Save"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("▸ ADD TRANSACTION", id="title")
            yield Label("Date  (YYYY-MM-DD)", classes="field-label")
            yield Input(placeholder="2024-01-15", id="inp-date",
                        validators=[Length(minimum=10, maximum=10)])
            yield Label("Description", classes="field-label")
            yield Input(placeholder="Salary", id="inp-desc",
                        validators=[Length(minimum=1)])
            yield Label("Category", classes="field-label")
            yield Select[str](CATEGORY_OPTIONS, id="inp-cat", prompt="Select category")
            yield Label("Amount  (negative = expense)", classes="field-label")
            yield Input(placeholder="-1200", id="inp-amount",
                        validators=[Number()])
            yield Static("", id="error")
            with Horizontal(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Save",   variant="primary",  id="btn-save")

    def _save(self) -> None:
        from datetime import datetime
        date_val   = self.query_one("#inp-date",   Input).value.strip()
        desc_val   = self.query_one("#inp-desc",   Input).value.strip()
        cat_val    = self.query_one("#inp-cat",    Select).value
        amount_val = self.query_one("#inp-amount", Input).value.strip()
        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            self.query_one("#error", Static).update("⚠ Date must be YYYY-MM-DD (e.g. 2024-01-15).")
            return
        if not desc_val:
            self.query_one("#error", Static).update("⚠ Description is required.")
            return
        if cat_val is Select.BLANK:
            self.query_one("#error", Static).update("⚠ Please select a category.")
            return
        try:
            amount = int(amount_val)
        except ValueError:
            self.query_one("#error", Static).update("⚠ Amount must be a whole number.")
            return
        self.dismiss(Transaction(date_val, desc_val, str(cat_val), amount))

    def action_cancel(self) -> None: self.dismiss(None)
    def action_submit(self) -> None: self._save()

    @on(Button.Pressed, "#btn-cancel")
    def _on_cancel(self) -> None: self.dismiss(None)

    @on(Button.Pressed, "#btn-save")
    def _on_save(self) -> None: self._save()


# ─── Confirm Delete Modal ─────────────────────────────────────────────────────

class ConfirmDeleteScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
        ConfirmDeleteScreen { align: center middle; }
        ConfirmDeleteScreen #dialog {
            width: 46; height: auto;
            border: round $error;
            background: $surface;
            padding: 1 2;
        }
        ConfirmDeleteScreen #title { text-style: bold; color: $error; margin-bottom: 1; }
        ConfirmDeleteScreen #desc  { color: $text-muted; margin-bottom: 1; }
        ConfirmDeleteScreen #btn-row { margin-top: 1; height: 3; align: right middle; }
        ConfirmDeleteScreen Button { margin-left: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel",  "Cancel"),
        Binding("d",      "confirm", "Delete"),
    ]

    def __init__(self, tx: Transaction, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tx = tx

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("▸ CONFIRM DELETE", id="title")
            yield Static(
                f"[dim]Delete[/] [bold]{self._tx.desc}[/] "
                f"[dim]on[/] {self._tx.display_date} "
                f"[dim]([/]{fmt_amount(self._tx.amount)}[dim])?[/]",
                id="desc", markup=True,
            )
            with Horizontal(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Delete", variant="error",   id="btn-delete")

    def action_cancel(self)  -> None: self.dismiss(False)
    def action_confirm(self) -> None: self.dismiss(True)

    @on(Button.Pressed, "#btn-cancel")
    def _cancel(self) -> None: self.dismiss(False)
    @on(Button.Pressed, "#btn-delete")
    def _delete(self) -> None: self.dismiss(True)


# ─── TransactionLog ───────────────────────────────────────────────────────────

class TransactionLog(Widget):
    """Editable transaction table. Posts DataChanged after every mutation."""

    class DataChanged(Message):
        """Broadcast whenever the transaction list is mutated."""

    DEFAULT_CSS = """
        TransactionLog {
            border: round $primary;
            width: 100%;
            height: 1fr;
        }
        TransactionLog DataTable {
            height: 1fr;
            background: transparent;
        }
    """

    BINDINGS = [
        Binding("a", "add_transaction",    "Add",    show=True),
        Binding("d", "delete_transaction", "Delete", show=True),
    ]

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        self.border_title    = "Transaction Log"
        self.border_subtitle = "a add · d delete"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        self._build_table()

    def _build_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "Description", "Category", "Amount", "Balance")
        table.cursor_type = "row"
        for tx in self._svc.transactions:
            table.add_row(
                f"[dim]{tx.display_date}[/]",
                tx.desc,
                f"[dim]{tx.cat}[/]",
                fmt_amount(tx.amount),
                f"[cyan]RP{tx.balance:,}[/]",
            )
        self.border_subtitle = f"a add · d delete · {len(self._svc.transactions)} rows"

    def action_add_transaction(self) -> None:
        def _on_result(tx: Transaction | None) -> None:
            if tx is None:
                return
            self._svc.add(tx)
            self._build_table()
            self.post_message(TransactionLog.DataChanged())

        self.app.push_screen(AddTransactionScreen(), _on_result)

    def action_delete_transaction(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return
        index = table.cursor_row
        tx    = self._svc.transactions[index]

        def _on_result(confirmed: bool) -> None:
            if confirmed:
                self._svc.remove(index)
                self._build_table()
                self.post_message(TransactionLog.DataChanged())

        self.app.push_screen(ConfirmDeleteScreen(tx), _on_result)


# ─── BalanceHistory ───────────────────────────────────────────────────────────

class BalanceHistory(Widget):
    DEFAULT_CSS = """
        BalanceHistory {
            border: round $accent;
            width: 100%;
            height: 1fr;
        }
        BalanceHistory DataTable {
            height: 1fr;
            background: transparent;
        }
    """

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Month", "Income", "Expenses", "Net", "Net Worth", "Change")
        table.cursor_type = "row"
        self._fill_table()

    def _fill_table(self) -> None:
        summaries = self._svc.monthly_summaries()
        table     = self.query_one(DataTable)
        table.clear()
        if summaries:
            self.border_title    = "Balance History"
            self.border_subtitle = f"{summaries[0].month} – {summaries[-1].month}"
        for s in summaries:
            table.add_row(
                f"[dim]{s.month}[/]",
                fmt_amount(s.income,    sign=False),
                fmt_amount(-s.expenses, sign=False),
                fmt_amount(s.net),
                f"[cyan]RP{s.net_worth:,}[/]",
                fmt_change(s.change),
            )

    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        self._fill_table()


# ─── Log (composite) ─────────────────────────────────────────────────────────

class Log(Widget):

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        with Vertical():
            yield TransactionLog(service=self._svc)
            yield BalanceHistory(service=self._svc)