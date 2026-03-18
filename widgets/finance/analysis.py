from __future__ import annotations

from statistics import mean, stdev

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Label, ProgressBar, Static, TabbedContent, TabPane

from services.financeService import (
    FinanceService,
    PeriodData,
    color_delta,
    trend_symbol,
    verdict,
    volatility,
)
from widgets.finance.log import TransactionLog


# ─── BurnRate ─────────────────────────────────────────────────────────────────

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

    def __init__(self, period: PeriodData, liquid: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._period = period
        self._liquid = liquid

    def compose(self) -> ComposeResult:
        self.border_title = "Burn Rate"
        runway = self._liquid / self._period.avg_expense if self._period.avg_expense else 0.0
        verdict_text, verdict_color = verdict(runway)
        yield Label(f"{runway:.1f} months of runway", id="runway")
        yield ProgressBar(total=12, show_eta=False, show_percentage=False)
        yield Label(
            f"avg burn [bold]${self._period.avg_expense:,.0f}/mo[/]  ·  "
            f"liquid [bold]${self._liquid:,}[/]",
            id="meta", markup=True,
        )
        yield Label(f"[{verdict_color}]{verdict_text}[/]", id="verdict", markup=True)

    def on_mount(self) -> None:
        runway = self._liquid / self._period.avg_expense if self._period.avg_expense else 0.0
        self.query_one(ProgressBar).progress = min(runway, 12)


# ─── IncomeStability ──────────────────────────────────────────────────────────

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

        if not income:
            yield Label("[dim]No data[/]", markup=True)
            return

        vol_label, vol_color = volatility(income)
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
        if not self._period.income:
            return
        max_inc = max(self._period.income)
        for bar, value in zip(self.query(ProgressBar), self._period.income):
            bar.progress = value


# ─── SpendingByCategory ───────────────────────────────────────────────────────

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
        months = self._period.months
        self.border_title    = "Spending by Category"
        self.border_subtitle = f"{months[0]} – {months[-1]}" if months else ""
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        self._fill()

    def _fill(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Category", "This Period", "Prev Period", "Trend")
        for cat, this, prev in sorted(self._period.category_rows):
            table.add_row(cat, f"${this:,}", f"${prev:,}", trend_symbol(this - prev))


# ─── BiggestMovers ────────────────────────────────────────────────────────────

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
        months = self._period.months
        self.border_title    = "Biggest Movers"
        self.border_subtitle = f"{months[0]} – {months[-1]}" if months else ""
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        self._fill()

    def _fill(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Category", "Δ ($)", "Δ (%)", "Dir")
        rows = sorted(
            (
                (cat, this - prev, (this - prev) / prev * 100 if prev else 0.0)
                for cat, this, prev in self._period.category_rows
            ),
            key=lambda r: abs(r[2]),
            reverse=True,
        )
        for cat, delta, pct in rows:
            clr  = color_delta(delta)
            sign = "+" if delta > 0 else ""
            table.add_row(
                cat,
                f"[{clr}]{sign}{delta:,}[/]",
                f"[{clr}]{sign}{pct:.1f}%[/]",
                trend_symbol(delta),
            )


# ─── AnalysisContent ──────────────────────────────────────────────────────────

class AnalysisContent(Widget):
    DEFAULT_CSS = """
        AnalysisContent { width: 100%; height: 1fr; }
        AnalysisContent .main-row  { width: 100%; height: 1fr; }
        AnalysisContent .left-col  { width: 1fr; height: 1fr; }
        AnalysisContent .right-col { width: 1fr; height: 1fr; }
    """

    def __init__(self, period: PeriodData, liquid: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._period = period
        self._liquid = liquid

    def compose(self) -> ComposeResult:
        with Horizontal(classes="main-row"):
            with Vertical(classes="left-col"):
                yield BurnRate(self._period, self._liquid)
                yield IncomeStability(self._period)
            with Vertical(classes="right-col"):
                yield SpendingByCategory(self._period)
                yield BiggestMovers(self._period)


# ─── Analysis ─────────────────────────────────────────────────────────────────

class Analysis(Widget):
    DEFAULT_CSS = """
        Analysis { width: 100%; height: 1fr; padding: 1 2; }
        Analysis TabbedContent { height: 1fr; }
        Analysis TabPane       { height: 1fr; padding: 0; }
    """

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        liquid = self._svc.liquid
        with TabbedContent():
            with TabPane("1M", id="tab-1m"):
                yield AnalysisContent(self._svc.build_period(1), liquid, id="ac-1m")
            with TabPane("3M", id="tab-3m"):
                yield AnalysisContent(self._svc.build_period(3), liquid, id="ac-3m")
            with TabPane("6M", id="tab-6m"):
                yield AnalysisContent(self._svc.build_period(6), liquid, id="ac-6m")

    def refresh_data(self) -> None:
        """Replace each AnalysisContent with freshly computed period data."""
        liquid = self._svc.liquid

        def _swap(n: int, ac_id: str, pane_id: str) -> None:
            pane = self.query_one(f"#{pane_id}", TabPane)

            async def _do() -> None:
                try:
                    old = self.query_one(f"#{ac_id}", AnalysisContent)
                    await old.remove()
                except Exception:
                    pass
                await pane.mount(
                    AnalysisContent(self._svc.build_period(n), liquid, id=ac_id)
                )

            self.app.call_later(_do)

        _swap(1, "ac-1m", "tab-1m")
        _swap(3, "ac-3m", "tab-3m")
        _swap(6, "ac-6m", "tab-6m")