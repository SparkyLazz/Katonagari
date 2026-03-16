from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widget import Widget
from textual.widgets import Label, Static


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
    }
    """
    def compose(self) -> ComposeResult:
        self.border_title = "Summary Panel"
        yield Label("Overview", classes="panel-title")
        yield Static("$24,500", classes="big-balance")


class TransactionTable(Widget):
    pass


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

        with Horizontal(classes="bottow-row"):
            yield SummaryPanel()
            yield TransactionTable()