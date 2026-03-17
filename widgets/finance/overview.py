from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widget import Widget
from textual.widgets import Label, Static, DataTable


class StatCard(Widget):

    DEFAULT_CSS = """
    StatCard {
        border: round;
        padding: 0 1;
        width: 1fr;
        height: 1fr;
    }
    StatCard .card-value {
        text-style: bold;
        color: $text;
    }
    StatCard .card-diff {
        color: $text-muted;
    }
    
    StatCard.success { border: round $success; }
    StatCard.error   { border: round $error; }
    StatCard.accent  { border: round $accent; }
    
    StatCard.success .card-value { color: $success; }
    StatCard.error   .card-value { color: $error; }
    StatCard.accent  .card-value { color: $accent; }
    """

    def __init__(self, label: str, value: str, diff: str, color: str = "success", **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.diff = diff
        self.color = color

    def on_mount(self):
        self.border_title = self.label
        self.add_class(self.color)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.value, classes=f"card-value {self.color}")
            yield Label(self.diff, classes="card-diff")
class SummaryPanel(Widget):
    DEFAULT_CSS = """
    SummaryPanel {
        border: round $primary;
        width: 28;
        height: 1fr;
        padding: 1 2;
    }
    .big-balance {
        text-style: bold;
        color: $success;
    }
    .divider {
        color: $primary;
    }
    .row-label {
        color: $text-muted;
        width: 12;
    }
    .row-value {
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "Summary"

        yield Static("$24,500", classes="big-balance")
        yield Static("─" * 20, classes="divider")

        with Horizontal():
            yield Label("Income",      classes="row-label")
            yield Static("$8,200",     classes="row-value success")

        with Horizontal():
            yield Label("Expenses",    classes="row-label")
            yield Static("$3,450",     classes="row-value error")

        with Horizontal():
            yield Label("Savings",     classes="row-label")
            yield Static("$4,750",     classes="row-value accent")

        yield Static("─" * 20, classes="divider")

        with Horizontal():
            yield Label("Investments", classes="row-label")
            yield Static("$12,000",    classes="row-value")

        with Horizontal():
            yield Label("Debt",        classes="row-label")
            yield Static("-$2,100",    classes="row-value error")

        yield Static("─" * 20, classes="divider")

        with Horizontal():
            yield Label("Save rate",   classes="row-label")
            yield Static("57.9%",      classes="row-value accent")

        with Horizontal():
            yield Label("vs last mo.", classes="row-label")
            yield Static("+2.4%",      classes="row-value success")
class TransactionTable(Widget):
    DEFAULT_CSS = """
    TransactionTable {
        width: 1fr;
        height: 1fr;
        border: round $accent;
        padding: 0;
    }

    TransactionTable DataTable {
        height: 1fr;
        background: transparent;
    }

    DataTable > .datatable--header {
        background: $panel;
        color: $text-muted;
        text-style: bold;
    }

    DataTable > .datatable--odd-row {
        background: $surface;
    }

    DataTable > .datatable--even-row {
        background: $panel;
    }

    DataTable > .datatable--cursor {
        background: $accent 20%;
        color: $text;
    }
    """

    ROWS = [
        ("Jan 01", "Salary", "Income", "[green]+$8,200[/]"),
        ("Jan 03", "Rent", "Housing", "[red]-$1,200[/]"),
        ("Jan 05", "Groceries", "Food", "[red]-$320[/]"),
        ("Jan 07", "Netflix", "Subscription", "[red]-$15[/]"),
        ("Jan 10", "Freelance", "Income", "[green]+$1,500[/]"),
        ("Jan 12", "Electric", "Utility", "[red]-$90[/]"),
        ("Jan 15", "Gym", "Health", "[red]-$45[/]"),
    ]

    def compose(self) -> ComposeResult:
        self.border_title = "Transactions"
        self.border_subtitle = "January 2024"

        table = DataTable(zebra_stripes=True)
        table.add_columns("Date", "Description", "Category", "Amount")
        table.add_rows(self.ROWS)
        yield table
class Overview(Widget):
    DEFAULT_CSS = """
        Overview {
            width: 100%;
            height: 1fr;
            padding: 1 2;
        }

        .stat-row {
            height: 7;
        }
        
        .bottom-row {
            width: 100%;
            height: 1fr;
        }
        .success { color: $success; }
        .error   { color: $error; }
        .accent  { color: $accent; }
        """

    def compose(self) -> ComposeResult:
        with Horizontal(classes="stat-row"):
            yield StatCard("Total Balance", "$24,500", "+2.4% this month", "success")
            yield StatCard("Monthly Income", "$8,200", "+$1,500 freelance", "success")
            yield StatCard("Expenses", "$3,450", "+12% vs last month", "error")
            yield StatCard("Net Savings", "$4,750", "57.9% save rate", "accent")

        with Horizontal(classes="bottom-row"):
            yield SummaryPanel()
            yield TransactionTable()