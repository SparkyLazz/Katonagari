"""
widgets/finance/analysis.py — Burn rate, income stability, spending.
Consolidated 1M/3M/6M tabs.
"""
from __future__ import annotations
from statistics import mean, stdev
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Label, ProgressBar, Static, TabbedContent, TabPane
from services.financeService import (FinanceService, PeriodData, color_delta, trend_symbol, verdict, volatility)

class BurnRate(Widget):
    DEFAULT_CSS = """
    BurnRate             { border: round $warning; width: 1fr; height: 10; padding: 1 2; }
    BurnRate #runway     { text-style: bold; color: $warning; }
    BurnRate #meta       { color: $text-muted; margin-top: 1; }
    BurnRate #verdict    { text-style: bold; margin-top: 1; }
    BurnRate ProgressBar { width: 100%; margin-top: 1; }
    """
    def __init__(self, p: PeriodData, liq: int, **kw) -> None:
        super().__init__(**kw); self._p, self._l = p, liq
    def compose(self) -> ComposeResult:
        self.border_title = "Burn Rate"
        r = self._l / self._p.avg_expense if self._p.avg_expense else 0.0
        vt, vc = verdict(r)
        yield Label(f"{r:.1f} months of runway", id="runway")
        yield ProgressBar(total=12, show_eta=False, show_percentage=False)
        yield Label(f"avg burn [bold]RP{self._p.avg_expense:,.0f}/mo[/]  ·  liquid [bold]RP{self._l:,}[/]", id="meta", markup=True)
        yield Label(f"[{vc}]{vt}[/]", id="verdict", markup=True)
    def on_mount(self) -> None:
        r = self._l / self._p.avg_expense if self._p.avg_expense else 0.0
        self.query_one(ProgressBar).progress = min(r, 12)

class IncomeStability(Widget):
    DEFAULT_CSS = """
    IncomeStability               { border: round $success; width: 1fr; height: 1fr; }
    IncomeStability VerticalScroll{ padding: 1 2; }
    IncomeStability #vr           { height: 1; margin-bottom: 1; }
    IncomeStability #vl           { color: $text-muted; width: 13; }
    IncomeStability .br           { height: 1; margin-bottom: 1; }
    IncomeStability .bm           { color: $text-muted; width: 5; }
    IncomeStability .bv           { color: $text-muted; width: 8; text-align: right; }
    IncomeStability ProgressBar   { width: 1fr; }
    IncomeStability .rl           { color: $text-muted; width: 14; }
    IncomeStability .rv           { text-style: bold; }
    """
    def __init__(self, p: PeriodData, **kw) -> None:
        super().__init__(**kw); self._p = p
    def compose(self) -> ComposeResult:
        self.border_title = "Income Stability"
        inc, mos = self._p.income, self._p.months
        if not inc: yield Label("[dim]No data[/]", markup=True); return
        vl,vc = volatility(inc); mx,avg,mn = max(inc),mean(inc),min(inc)
        sd = stdev(inc) if len(inc)>1 else 0
        with VerticalScroll():
            with Horizontal(id="vr"):
                yield Label("volatility: ", id="vl")
                yield Label(f"[{vc}][bold]{vl}[/][/]", markup=True)
                yield Label(f"  [dim]σ = RP{sd:,.0f}[/]", markup=True)
            for m,v in zip(mos,inc):
                last = m==mos[-1]
                with Horizontal(classes="br"):
                    yield Label(f"[yellow]{m}[/]" if last else m, markup=True, classes="bm")
                    yield ProgressBar(total=mx, show_eta=False, show_percentage=False)
                    yield Label(f"[yellow]RP{v:,}[/]" if last else f"[dim]RP{v:,}[/]", markup=True, classes="bv")
            with Horizontal():
                yield Label("avg income", classes="rl"); yield Static(f"RP{avg:,.0f}", classes="rv success")
            with Horizontal():
                yield Label("min / max", classes="rl"); yield Static(f"RP{mn:,} / RP{mx:,}", classes="rv")
            with Horizontal():
                yield Label("range spread", classes="rl"); yield Static(f"RP{mx-mn:,}", classes="rv accent")
    def on_mount(self) -> None:
        if not self._p.income: return
        for bar,v in zip(self.query(ProgressBar), self._p.income): bar.progress = v

class SpendingByCategory(Widget):
    DEFAULT_CSS = """
    SpendingByCategory           { border: round $primary; width: 1fr; height: 1fr; }
    SpendingByCategory DataTable { height: 1fr; background: transparent; }
    """
    def __init__(self, p: PeriodData, **kw) -> None:
        super().__init__(**kw); self._p = p
    def compose(self) -> ComposeResult:
        m = self._p.months
        self.border_title = "Spending by Category"
        self.border_subtitle = f"{m[0]} – {m[-1]}" if m else ""
        yield DataTable(zebra_stripes=True)
    def on_mount(self) -> None:
        t = self.query_one(DataTable)
        t.add_columns("Category","This Period","Prev Period","Trend")
        for cat,this,prev in sorted(self._p.category_rows):
            t.add_row(cat, f"RP{this:,}", f"RP{prev:,}", trend_symbol(this-prev))

class BiggestMovers(Widget):
    DEFAULT_CSS = """
    BiggestMovers           { border: round $error; width: 1fr; height: 1fr; }
    BiggestMovers DataTable { height: 1fr; background: transparent; }
    """
    def __init__(self, p: PeriodData, **kw) -> None:
        super().__init__(**kw); self._p = p
    def compose(self) -> ComposeResult:
        m = self._p.months
        self.border_title = "Biggest Movers"
        self.border_subtitle = f"{m[0]} – {m[-1]}" if m else ""
        yield DataTable(zebra_stripes=True)
    def on_mount(self) -> None:
        t = self.query_one(DataTable)
        t.add_columns("Category","Δ (RP)","Δ (%)","Dir")
        rows = sorted(((c,th-pr,(th-pr)/pr*100 if pr else 0.0) for c,th,pr in self._p.category_rows),
                       key=lambda r: abs(r[2]), reverse=True)
        for cat,d,pct in rows:
            c=color_delta(d); s="+"if d>0 else""
            t.add_row(cat, f"[{c}]{s}{d:,}[/]", f"[{c}]{s}{pct:.1f}%[/]", trend_symbol(d))

class AnalysisContent(Widget):
    DEFAULT_CSS = """
    AnalysisContent        { width: 100%; height: 1fr; }
    AnalysisContent .main  { width: 100%; height: 1fr; }
    AnalysisContent .left  { width: 1fr; height: 1fr; }
    AnalysisContent .right { width: 1fr; height: 1fr; }
    """
    def __init__(self, p: PeriodData, liq: int, **kw) -> None:
        super().__init__(**kw); self._p, self._l = p, liq
    def compose(self) -> ComposeResult:
        with Horizontal(classes="main"):
            with Vertical(classes="left"):
                yield BurnRate(self._p, self._l)
                yield IncomeStability(self._p)
            with Vertical(classes="right"):
                yield SpendingByCategory(self._p)
                yield BiggestMovers(self._p)

class Analysis(Widget):
    DEFAULT_CSS = """
    Analysis               { width: 100%; height: 1fr; padding: 1 2; }
    Analysis TabbedContent { height: 1fr; }
    Analysis TabPane       { height: 1fr; padding: 0; }
    """
    def __init__(self, *, service: FinanceService, **kw) -> None:
        super().__init__(**kw); self._svc = service
    def compose(self) -> ComposeResult:
        liq = self._svc.liquid
        with TabbedContent():
            for n,label in [(1,"1M"),(3,"3M"),(6,"6M")]:
                with TabPane(label, id=f"tab-{label}"):
                    yield AnalysisContent(self._svc.build_period(n), liq, id=f"ac-{label}")
    def refresh_data(self) -> None:
        liq = self._svc.liquid
        for n,label in [(1,"1M"),(3,"3M"),(6,"6M")]:
            pane = self.query_one(f"#tab-{label}", TabPane)
            async def _do(pane=pane, n=n, label=label, liq=liq) -> None:
                try: old = self.query_one(f"#ac-{label}",AnalysisContent); await old.remove()
                except Exception: pass
                await pane.mount(AnalysisContent(self._svc.build_period(n), liq, id=f"ac-{label}"))
            self.app.call_later(_do)