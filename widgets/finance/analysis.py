from dataclasses import dataclass
from statistics import mean, stdev
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Label, ProgressBar, Static, TabbedContent, TabPane

# ─── Raw historical data ─────────────────────────────────────────────────────

MONTHS_ALL: list[str] = ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan"]
INCOME_ALL: list[int] = [7800, 8100, 8200, 7600, 9100, 9700]
LIQUID = 11_750

CATEGORY_HISTORY: dict[str, list[int]] = {
    "Food":         [290,  270,  260,  280,  310,  320],
    "Health":       [ 45,   45,   45,   45,   45,   45],
    "Housing":      [1200, 1200, 1200, 1200, 1200, 1200],
    "Other":        [2090, 1825, 1705, 2025, 2210, 1585],
    "Subscription": [ 20,   20,   20,   20,   20,   15],
    "Transport":    [180,  160,  200,  150,  220,  195],
    "Utility":      [ 75,   80,   70,   80,   95,   90],
}

# ─── Period ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PeriodData:
    months:       list[str]
    income:       list[int]
    category_rows: list[tuple[str, int, int]]  # (cat, this_avg, prev_avg)
    avg_expense:  float


def _build_period(n: int) -> PeriodData:
    months = MONTHS_ALL[-n:]
    income = INCOME_ALL[-n:]

    cat_rows = []
    for cat, history in CATEGORY_HISTORY.items():
        curr = history[-n:]
        prev = history[max(0, len(history) - 2 * n) : len(history) - n]
        cat_rows.append((
            cat,
            round(mean(curr)),
            round(mean(prev)) if prev else curr[0],
        ))

    monthly_exp = [
        sum(CATEGORY_HISTORY[c][len(MONTHS_ALL) - n + i] for c in CATEGORY_HISTORY)
        for i in range(n)
    ]

    return PeriodData(
        months=months,
        income=income,
        category_rows=cat_rows,
        avg_expense=mean(monthly_exp),
    )


PERIODS: dict[str, PeriodData] = {
    "1M": _build_period(1),
    "3M": _build_period(3),
    "6M": _build_period(6),
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _verdict(months: float) -> tuple[str, str]:
    if months < 3:  return "⚠ CRITICAL — build emergency fund", "red"
    if months < 6:  return "▲ FAIR — aim for 6+ months",        "yellow"
    if months < 12: return "✓ GOOD",                             "cyan"
    return "✓ EXCELLENT — 12+ months covered",                   "green"

def _volatility(data: list[int]) -> tuple[str, str]:
    if len(data) < 2: return "N/A", "dim"
    cv = stdev(data) / mean(data)
    if cv < 0.06:  return "LOW",    "green"
    if cv < 0.15:  return "MEDIUM", "yellow"
    return "HIGH", "red"

def _color_delta(delta: int) -> str:
    if delta > 0: return "red"
    if delta < 0: return "green"
    return "dim"

def _trend_symbol(delta: int) -> str:
    if delta > 0: return "[red]▲[/]"
    if delta < 0: return "[green]▼[/]"
    return "[dim]─[/]"

# ─── Widgets ─────────────────────────────────────────────────────────────────

class BurnRate(Widget):
    DEFAULT_CSS = """
        BurnRate {
            border: round $warning;
            width: 1fr;
            height: 10;
            padding: 1 2;
        }
        BurnRate #runway  { text-style: bold; color: $warning; }
        BurnRate #meta    { color: $text-muted; margin-top: 1; }
        BurnRate #verdict { text-style: bold; margin-top: 1; }
        BurnRate ProgressBar { width: 100%; margin-top: 1; }
    """

    def __init__(self, period: PeriodData, **kwargs) -> None:
        super().__init__(**kwargs)
        self._period = period

    def compose(self) -> ComposeResult:
        self.border_title = "Burn Rate"
        runway = LIQUID / self._period.avg_expense
        verdict_text, verdict_color = _verdict(runway)

        yield Label(f"{runway:.1f} months of runway", id="runway")
        yield ProgressBar(total=12, show_eta=False, show_percentage=False)
        yield Label(
            f"avg burn [bold]${self._period.avg_expense:,.0f}/mo[/] · liquid [bold]${LIQUID:,}[/]",
            id="meta", markup=True,
        )
        yield Label(f"[{verdict_color}]{verdict_text}[/]", id="verdict", markup=True)

    def on_mount(self) -> None:
        runway = LIQUID / self._period.avg_expense
        self.query_one(ProgressBar).progress = min(runway, 12)


class IncomeStability(Widget):
    DEFAULT_CSS = """
        IncomeStability {
            border: round $success;
            width: 1fr;
            height: 1fr;
        }
        IncomeStability VerticalScroll { padding: 1 2; }
        IncomeStability #vol-row       { height: 1; margin-bottom: 1; }
        IncomeStability #vol-label     { color: $text-muted; width: 13; }
        IncomeStability .bar-row       { height: 1; margin-bottom: 1; }
        IncomeStability .bar-month     { color: $text-muted; width: 5; }
        IncomeStability .bar-value     { color: $text-muted; width: 8; text-align: right; }
        IncomeStability ProgressBar    { width: 1fr; }
        IncomeStability .row-label     { color: $text-muted; width: 14; }
        IncomeStability .row-value     { text-style: bold; }
    """

    def __init__(self, period: PeriodData, **kwargs) -> None:
        super().__init__(**kwargs)
        self._period = period

    def compose(self) -> ComposeResult:
        self.border_title = "Income Stability"
        income = self._period.income
        months = self._period.months
        vol_label, vol_color = _volatility(income)
        max_inc = max(income)
        avg_inc = mean(income)
        min_inc = min(income)
        spread  = max_inc - min_inc
        sd      = stdev(income) if len(income) > 1 else 0

        with VerticalScroll():
            with Horizontal(id="vol-row"):
                yield Label("volatility: ", id="vol-label")
                yield Label(f"[{vol_color}][bold]{vol_label}[/bold][/]", markup=True)
                yield Label(f"  [dim]σ = ${sd:,.0f}[/]", markup=True)

            for month, value in zip(months, income):
                is_last = month == months[-1]
                with Horizontal(classes="bar-row"):
                    yield Label(
                        f"[yellow]{month}[/]" if is_last else month,
                        markup=True, classes="bar-month",
                    )
                    yield ProgressBar(total=max_inc, show_eta=False, show_percentage=False)
                    yield Label(
                        f"[yellow]${value:,}[/]" if is_last else f"[dim]${value:,}[/]",
                        markup=True, classes="bar-value",
                    )

            with Horizontal():
                yield Label("avg income",   classes="row-label")
                yield Static(f"${avg_inc:,.0f}", classes="row-value success")

            with Horizontal():
                yield Label("min / max",    classes="row-label")
                yield Static(f"${min_inc:,} / ${max_inc:,}", classes="row-value")

            with Horizontal():
                yield Label("range spread", classes="row-label")
                yield Static(f"${spread:,}", classes="row-value accent")

    def on_mount(self) -> None:
        max_inc = max(self._period.income)
        for bar, value in zip(self.query(ProgressBar), self._period.income):
            bar.progress = value


class SpendingByCategory(Widget):
    DEFAULT_CSS = """
        SpendingByCategory {
            border: round $primary;
            width: 1fr;
            height: 1fr;
        }
        SpendingByCategory DataTable { height: 1fr; background: transparent; }
    """

    def __init__(self, period: PeriodData, **kwargs) -> None:
        super().__init__(**kwargs)
        self._period = period

    def compose(self) -> ComposeResult:
        self.border_title = "Spending by Category"
        self.border_subtitle = f"{self._period.months[0]} – {self._period.months[-1]} 2024"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Category", "This Period", "Prev Period", "Trend")
        for cat, this, prev in sorted(self._period.category_rows):
            table.add_row(cat, f"${this:,}", f"${prev:,}", _trend_symbol(this - prev))


class BiggestMovers(Widget):
    DEFAULT_CSS = """
        BiggestMovers {
            border: round $error;
            width: 1fr;
            height: 1fr;
        }
        BiggestMovers DataTable { height: 1fr; background: transparent; }
    """

    def __init__(self, period: PeriodData, **kwargs) -> None:
        super().__init__(**kwargs)
        self._period = period

    def compose(self) -> ComposeResult:
        self.border_title = "Biggest Movers"
        self.border_subtitle = f"{self._period.months[0]} – {self._period.months[-1]} 2024"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Category", "Δ ($)", "Δ (%)", "Dir")

        rows = sorted(
            (
                (cat, this - prev, (this - prev) / prev * 100 if prev else 0)
                for cat, this, prev in self._period.category_rows
            ),
            key=lambda r: abs(r[2]),
            reverse=True,
        )

        for cat, delta, pct in rows:
            color = _color_delta(delta)
            sign  = "+" if delta > 0 else ""
            table.add_row(
                cat,
                f"[{color}]{sign}{delta:,}[/]",
                f"[{color}]{sign}{pct:.1f}%[/]",
                _trend_symbol(delta),
            )


class AnalysisContent(Widget):
    DEFAULT_CSS = """
        AnalysisContent { width: 100%; height: 1fr; }
        AnalysisContent .main-row  { width: 100%; height: 1fr; }
        AnalysisContent .left-col  { width: 1fr; height: 1fr; }
        AnalysisContent .right-col { width: 1fr; height: 1fr; }
    """

    def __init__(self, period: PeriodData, **kwargs) -> None:
        super().__init__(**kwargs)
        self._period = period

    def compose(self) -> ComposeResult:
        with Horizontal(classes="main-row"):
            with Vertical(classes="left-col"):
                yield BurnRate(self._period)
                yield IncomeStability(self._period)
            with Vertical(classes="right-col"):
                yield SpendingByCategory(self._period)
                yield BiggestMovers(self._period)


class Analysis(Widget):
    DEFAULT_CSS = """
        Analysis { width: 100%; height: 1fr; padding: 1 2; }
        Analysis TabbedContent { height: 1fr; }
        Analysis TabPane       { height: 1fr; padding: 0; }
    """

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("1M", id="tab-1m"):
                yield AnalysisContent(PERIODS["1M"])
            with TabPane("3M", id="tab-3m"):
                yield AnalysisContent(PERIODS["3M"])
            with TabPane("6M", id="tab-6m"):
                yield AnalysisContent(PERIODS["6M"])