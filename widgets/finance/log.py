from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import DataTable

# ─── Data ────────────────────────────────────────────────────────────────────

TRANSACTIONS: list[tuple] = [
    ("Jan 01", "Salary",       "Income",       +8200, 8200),
    ("Jan 03", "Rent",         "Housing",      -1200, 7000),
    ("Jan 05", "Groceries",    "Food",          -320, 6680),
    ("Jan 07", "Netflix",      "Subscription",  -15,  6665),
    ("Jan 10", "Freelance",    "Income",       +1500, 8165),
    ("Jan 12", "Electric",     "Utility",        -90, 8075),
    ("Jan 15", "Gym",          "Health",         -45, 8030),
    ("Jan 18", "Transport",    "Transport",     -195, 7835),
    ("Jan 20", "Dining out",   "Food",           -80, 7755),
    ("Jan 22", "Side project", "Income",        +400, 8155),
    ("Jan 25", "Misc",         "Other",         -120, 8035),
    ("Jan 28", "Insurance",    "Health",        -210, 7825),
]

BALANCE_HISTORY: list[tuple] = [
    ("Aug 2023", 7800, 3900, 3900, 19250,     0),
    ("Sep 2023", 8100, 3600, 4500, 19950,   700),
    ("Oct 2023", 8200, 3500, 4700, 20650,   700),
    ("Nov 2023", 7600, 3800, 3800, 21250,   600),
    ("Dec 2023", 9100, 4100, 5000, 23250,  2000),
    ("Jan 2024", 9700, 3450, 6250, 24500,  1250),
]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _fmt_amount(n: int, sign: bool = True) -> str:
    prefix = ("+" if n > 0 else "") if sign else ""
    color  = "green" if n >= 0 else "red"
    return f"[{color}]{prefix}${abs(n):,}[/]"

def _fmt_change(n: int) -> str:
    if n == 0:   return "[dim]─[/]"
    if n > 0:    return f"[green]+${n:,}[/]"
    return f"[red]-${abs(n):,}[/]"

# ─── Widgets ─────────────────────────────────────────────────────────────────

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

    def compose(self) -> ComposeResult:
        self.border_title = "Transaction Log"
        self.border_subtitle = "Jan 2024"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Date", "Description", "Category", "Amount", "Balance")
        table.cursor_type = "row"

        for date, desc, cat, amount, balance in TRANSACTIONS:
            table.add_row(
                f"[dim]{date}[/]",
                desc,
                f"[dim]{cat}[/]",
                _fmt_amount(amount),
                f"[cyan]${balance:,}[/]",
            )

    def sort_by(self, col: int) -> None:
        self.query_one(DataTable).sort(col)


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

    def compose(self) -> ComposeResult:
        self.border_title = "Balance History"
        self.border_subtitle = "Aug – Jan 2024"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Month", "Income", "Expenses", "Net", "Net Worth", "Change")
        table.cursor_type = "row"

        for month, income, expenses, net, net_worth, change in BALANCE_HISTORY:
            table.add_row(
                f"[dim]{month}[/]",
                _fmt_amount(income,   sign=False),
                _fmt_amount(-expenses, sign=False),
                _fmt_amount(net),
                f"[cyan]${net_worth:,}[/]",
                _fmt_change(change),
            )


class Log(Widget):
    DEFAULT_CSS = """
        Log {
            width: 100%;
            height: 1fr;
            padding: 1 2;
        }
        Log Vertical {
            width: 100%;
            height: 1fr;
        }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield TransactionLog()
            yield BalanceHistory()