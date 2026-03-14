from __future__ import annotations
from datetime import date

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, ProgressBar

from databases.financeData import (
    get_last_n_months, fmt_rp, fmt_rp_short,
)
from .constants import _MONTH_NAMES

class AnalysisPanel(Widget):
    """Income vs Expense per-month cards with ProgressBars and round borders."""

    _PERIODS = [("3M", 3), ("6M", 6), ("12M", 12)]

    DEFAULT_CSS = """
    AnalysisPanel {
        width: 100%;
        height: auto;
        layout: vertical;
        padding: 0 1 1 1;
    }

    /* ── period selector ─────────────────────────────── */
    #an-period-row {
        height: 3;
        layout: horizontal;
        margin-bottom: 1;
    }
    .an-period-lbl {
        width: auto; height: 3;
        color: $text-muted; content-align: left middle; padding: 0 1;
    }

    /* ── chart area ──────────────────────────────────── */
    #an-chart { width: 100%; height: auto; layout: vertical; }

    /* per-month card */
    .an-card {
        width: 100%;
        height: auto;
        background: $surface;
        border: round;
        padding: 0 1;
        margin-bottom: 1;
        layout: vertical;
        border-title-align: left;
        border-title-style: bold;
    }
    .an-card-now { border: round $primary 80%; border-title-color: $primary; }

    /* rows inside a card */
    .an-row { height: 1; layout: horizontal; width: 100%; margin-top: 1; }
    .an-lbl { width: 5; color: $text-muted; content-align: left middle; }
    .an-amt { width: 12; text-align: right; content-align: right middle; }
    .an-net { height: 1; color: $text-muted; margin: 1 0; }

    /* progress bars */
    .an-inc-bar { width: 1fr; margin-bottom: 0; }
    .an-exp-bar { width: 1fr; margin-bottom: 0; }
    .an-inc-bar > .bar--bar { color: $success; }
    .an-exp-bar > .bar--bar { color: $error;   }
    .an-inc-bar > .bar--complete { color: $success; }
    .an-exp-bar > .bar--complete { color: $error;   }

    /* ── summary box ─────────────────────────────────── */
    #an-sum {
        width: 100%; height: auto;
        background: $surface;
        border: round $primary;
        padding: 0 1 1 1;
        margin: 1 0;
        border-title-align: left;
        border-title-color: $primary;
        border-title-style: bold;
    }
    .an-sum-row  { height: 1; layout: horizontal; width: 100%; margin-top: 1; }
    .an-sum-lbl  { width: 1fr; color: $text-muted; }
    .an-sum-val  { width: 16; text-align: right; }
    """

    _period: reactive[int] = reactive(6)

    def compose(self) -> ComposeResult:
        with Horizontal(id="an-period-row"):
            yield Label("Period:", classes="an-period-lbl")
            for lbl, n in self._PERIODS:
                yield Button(lbl, id=f"an-p-{n}",
                             variant="primary" if n == 6 else "default")
        yield Vertical(id="an-chart")
        with Vertical(id="an-sum") as v:
            v.border_title = "📊 SUMMARY"
            with Horizontal(classes="an-sum-row"):
                yield Label("Total Income",  classes="an-sum-lbl")
                yield Label("", id="an-s-inc", classes="an-sum-val")
            with Horizontal(classes="an-sum-row"):
                yield Label("Total Expense", classes="an-sum-lbl")
                yield Label("", id="an-s-exp", classes="an-sum-val")
            with Horizontal(classes="an-sum-row"):
                yield Label("Net Savings",   classes="an-sum-lbl")
                yield Label("", id="an-s-net", classes="an-sum-val")
            with Horizontal(classes="an-sum-row"):
                yield Label("Savings Rate",  classes="an-sum-lbl")
                yield Label("", id="an-s-rate", classes="an-sum-val")

    def on_mount(self) -> None:
        self.rebuild([])

    def on_button_pressed(self, ev: Button.Pressed) -> None:
        for _, n in self._PERIODS:
            if ev.button.id == f"an-p-{n}":
                self._period = n
                for _, m in self._PERIODS:
                    self.query_one(f"#an-p-{m}", Button).variant = (
                        "primary" if m == n else "default"
                    )
                ev.stop()
                self.rebuild(self._last_txs)
                return

    def rebuild(self, transactions: list) -> None:
        self._last_txs = transactions
        months  = get_last_n_months(transactions, self._period)
        chart   = self.query_one("#an-chart", Vertical)
        for child in list(chart.children):
            child.remove()

        max_val = max(
            max((m["income"]  for m in months), default=1),
            max((m["expense"] for m in months), default=1),
            1,
        )

        today = date.today()
        for i, m in enumerate(months):
            name   = f"{_MONTH_NAMES[m['month'] - 1]} '{str(m['year'])[2:]}"
            is_now = m["year"] == today.year and m["month"] == today.month
            net    = m["net"]
            nc     = "green" if net >= 0 else "red"
            ns     = ("+" if net >= 0 else "") + fmt_rp_short(net)

            card_cls = "an-card an-card-now" if is_now else "an-card"
            card = Vertical(classes=card_cls)
            if is_now:
                card.border_title = f"{name}  ◂ current"
            else:
                card.border_title = name
            chart.mount(card)

            inc_hdr = Horizontal(classes="an-row")
            card.mount(inc_hdr)
            inc_hdr.mount(Label("INC", classes="an-lbl"))
            inc_hdr.mount(Label(
                f"[green]{fmt_rp_short(m['income'])}[/]",
                markup=True, classes="an-amt"))

            card.mount(ProgressBar(
                total=max_val, id=f"an-inc-{i}",
                show_eta=False, classes="an-inc-bar"))

            exp_hdr = Horizontal(classes="an-row")
            card.mount(exp_hdr)
            exp_hdr.mount(Label("EXP", classes="an-lbl"))
            exp_hdr.mount(Label(
                f"[red]{fmt_rp_short(m['expense'])}[/]",
                markup=True, classes="an-amt"))

            card.mount(ProgressBar(
                total=max_val, id=f"an-exp-{i}",
                show_eta=False, classes="an-exp-bar"))

            card.mount(Label(
                f"[{nc}]{ns}[/] net",
                markup=True, classes="an-net"))

        for i, m in enumerate(months):
            self.query_one(f"#an-inc-{i}", ProgressBar).progress = m["income"]
            self.query_one(f"#an-exp-{i}", ProgressBar).progress = m["expense"]

        total_inc = sum(m["income"]  for m in months)
        total_exp = sum(m["expense"] for m in months)
        total_net = total_inc - total_exp
        rate      = total_net / total_inc * 100 if total_inc > 0 else 0.0
        nc   = "green" if total_net >= 0 else "red"
        rc   = "green" if rate >= 20 else "yellow" if rate >= 0 else "red"
        sign = "+" if total_net >= 0 else ""
        self.query_one("#an-s-inc",  Label).update(f"[green]{fmt_rp(total_inc)}[/]")
        self.query_one("#an-s-exp",  Label).update(f"[red]{fmt_rp(total_exp)}[/]")
        self.query_one("#an-s-net",  Label).update(
            f"[{nc}]{sign}{fmt_rp(total_net)}[/]")
        self.query_one("#an-s-rate", Label).update(f"[{rc}]{rate:.1f}%[/]")
