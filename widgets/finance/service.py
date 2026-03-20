from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.validation import Length, Number
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static, Select
from dataclasses import dataclass

# ─── Model ───────────────────────────────────────────────────────────────────

CATEGORIES: list[str] = [
    "Food", "Health", "Housing", "Income",
    "Other", "Subscription", "Transport", "Utility",
]

CATEGORY_OPTIONS: list[tuple[str, str]] = [(cat, cat) for cat in CATEGORIES]


@dataclass
class Transaction:
    date:    str
    desc:    str
    cat:     str
    amount:  int
    balance: int = 0


# ─── Service ─────────────────────────────────────────────────────────────────

class FinanceService:
    """Single source of truth for all transaction data."""

    def __init__(self) -> None:
        self._transactions: list[Transaction] = [
            Transaction("Jan 01", "Salary",       "Income",        +8200, 8200),
            Transaction("Jan 03", "Rent",         "Housing",       -1200, 7000),
            Transaction("Jan 05", "Groceries",    "Food",           -320, 6680),
            Transaction("Jan 07", "Netflix",      "Subscription",    -15, 6665),
            Transaction("Jan 10", "Freelance",    "Income",        +1500, 8165),
            Transaction("Jan 12", "Electric",     "Utility",         -90, 8075),
            Transaction("Jan 15", "Gym",          "Health",          -45, 8030),
            Transaction("Jan 18", "Transport",    "Transport",      -195, 7835),
            Transaction("Jan 20", "Dining out",   "Food",            -80, 7755),
            Transaction("Jan 22", "Side project", "Income",         +400, 8155),
            Transaction("Jan 25", "Misc",         "Other",          -120, 8035),
            Transaction("Jan 28", "Insurance",    "Health",         -210, 7825),
        ]

    @property
    def transactions(self) -> list[Transaction]:
        return list(self._transactions)

    def add(self, tx: Transaction) -> None:
        self._recalc_balance(tx)
        self._transactions.append(tx)

    def remove(self, index: int) -> Transaction:
        removed = self._transactions.pop(index)
        self._rebuild_balances()
        return removed

    def _recalc_balance(self, tx: Transaction) -> None:
        last = self._transactions[-1].balance if self._transactions else 0
        tx.balance = last + tx.amount

    def _rebuild_balances(self) -> None:
        running = 0
        for tx in self._transactions:
            running += tx.amount
            tx.balance = running


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _fmt_amount(n: int, sign: bool = True) -> str:
    prefix = ("+" if n > 0 else "") if sign else ""
    color  = "green" if n >= 0 else "red"
    return f"[{color}]{prefix}RP {abs(n):,}[/]"


# ─── Add Transaction Modal ────────────────────────────────────────────────────

class AddTransactionScreen(ModalScreen):
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
        AddTransactionScreen Input {
            width: 100%;
        }
        AddTransactionScreen Select {
            width: 100%;
        }
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
        AddTransactionScreen Button {
            margin-left: 1;
        }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "submit", "Save"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("▸ ADD TRANSACTION", id="title")

            yield Label("Date  (e.g. Jan 01)", classes="field-label")
            yield Input(placeholder="Jan 01", id="inp-date",
                        validators=[Length(minimum=4)])

            yield Label("Description", classes="field-label")
            yield Input(placeholder="Salary", id="inp-desc",
                        validators=[Length(minimum=1)])

            yield Label("Category", classes="field-label")
            yield Select(
                [(cat, cat) for cat in CATEGORIES],
                id="inp-cat",
                prompt="Select category",
            )

            yield Label("Amount  (negative = expense)", classes="field-label")
            yield Input(placeholder="-1200", id="inp-amount",
                        validators=[Number()])

            yield Static("", id="error")

            with Horizontal(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Save",   variant="primary",  id="btn-save")

    def _save(self) -> None:
        date_val   = self.query_one("#inp-date",   Input).value.strip()
        desc_val   = self.query_one("#inp-desc",   Input).value.strip()
        cat_val    = self.query_one("#inp-cat",    Select).value
        amount_val = self.query_one("#inp-amount", Input).value.strip()

        if not date_val or not desc_val:
            self.query_one("#error", Static).update("⚠ Date and description are required.")
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
        ConfirmDeleteScreen {
            align: center middle;
        }
        ConfirmDeleteScreen #dialog {
            width: 44;
            height: auto;
            border: round $error;
            background: $surface;
            padding: 1 2;
        }
        ConfirmDeleteScreen #title {
            text-style: bold;
            color: $error;
            margin-bottom: 1;
        }
        ConfirmDeleteScreen #desc {
            color: $text-muted;
            margin-bottom: 1;
        }
        ConfirmDeleteScreen #btn-row {
            margin-top: 1;
            height: 3;
            align: right middle;
        }
        ConfirmDeleteScreen Button { margin-left: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
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
                f"[dim]on[/] {self._tx.date} "
                f"[dim]([/]{_fmt_amount(self._tx.amount)}[dim])?[/]",
                id="desc", markup=True,
            )
            with Horizontal(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Delete", variant="error",   id="btn-delete")

    def action_cancel(self)  -> None: self.dismiss(False)
    def action_confirm(self) -> None: self.dismiss(True)

    @on(Button.Pressed, "#btn-cancel")
    def _cancel(self, _) -> None: self.dismiss(False)
    @on(Button.Pressed, "#btn-delete")
    def _delete(self, _) -> None: self.dismiss(True)


# ─── TransactionLog widget ────────────────────────────────────────────────────

class TransactionLog(Widget):
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

    def __init__(self, service: FinanceService, **kwargs) -> None:
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
                f"[dim]{tx.date}[/]",
                tx.desc,
                f"[dim]{tx.cat}[/]",
                _fmt_amount(tx.amount),
                f"[cyan]RP {tx.balance:,}[/]",
            )

    def action_add_transaction(self) -> None:
        def _on_result(tx: Transaction | None) -> None:
            if tx is None:
                return
            self._svc.add(tx)
            self._build_table()
            self.border_subtitle = f"a add · d delete · {len(self._svc.transactions)} rows"

        self.app.push_screen(AddTransactionScreen(), _on_result)

    def action_delete_transaction(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return

        index = table.cursor_row
        tx    = self._svc.transactions[index]

        def _on_result(confirmed: bool) -> None:
            if not confirmed:
                return
            self._svc.remove(index)
            self._build_table()

        self.app.push_screen(ConfirmDeleteScreen(tx), _on_result)