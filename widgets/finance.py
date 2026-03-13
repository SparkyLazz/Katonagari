"""
finance.py — Finance tab for Katonagari.

Layout:
  Finance (vertical, 1fr)
  ├── #fin-body (horizontal, 1fr)
  │   ├── FinanceSidebar   (width:28)
  │   └── TabbedContent #fin-tabs (1fr)
  │       ├── TabPane "Transactions"
  │       │   └── #tx-pane (vertical, 1fr)
  │       │       ├── #filter-bar  (height:3)
  │       │       ├── #info-bar    (height:1)
  │       │       └── DataTable / #no-txs (1fr)
  │       └── TabPane "Analysis"
  │           └── ScrollableContainer
  │               └── AnalysisPanel
  └── #key-hints (height:1)
"""
from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button, DataTable, Input, Label, ProgressBar, Rule,
    Select, Static, TabbedContent, TabPane,
)

from databases.financeData import (
    ACCOUNTS, ACCOUNT_COLOR, ACCOUNT_ICON,
    EXPENSE_CATEGORIES, INCOME_CATEGORIES,
    CATEGORY_COLOR, CATEGORY_ICON,
    TYPE_COLOR, TYPE_LABEL,
    add_transaction, delete_transaction, update_transaction,
    get_last_n_months, get_monthly_summary,
    load_data, fmt_rp, fmt_rp_short,
)

# ─────────────────────────────────────────────────────────────────────────────
# Rich color helpers
# DataTable markup cannot use CSS variables — map semantic names to Rich colors.
# ─────────────────────────────────────────────────────────────────────────────
_RICH: dict[str, str] = {
    "$error":      "red",
    "$warning":    "yellow",
    "$primary":    "blue",
    "$success":    "green",
    "$accent":     "cyan",
    "$text-muted": "dim white",
}
_ACC_RICH: dict[str, str] = {
    "GoPay":   "blue",
    "SeaBank": "green",
    "NeoBank": "cyan",
    "Cash":    "yellow",
}
_TYPE_PILL: dict[str, str] = {
    "expense":  "[bold red]EXP[/]",
    "income":   "[bold green]INC[/]",
    "transfer": "[bold cyan]TRF[/]",
}

def _rc(css_var: str) -> str:
    return _RICH.get(css_var, "white")


# ─────────────────────────────────────────────────────────────────────────────
# Shared widget helpers
# ─────────────────────────────────────────────────────────────────────────────
_MODAL_RULE_CSS = "Rule { color: $surface-lighten-2; margin: 0 1; height: 1; }"

_TYPE_OPTS    = [("↓ Expense", "expense"), ("↑ Income", "income"), ("⇆ Transfer", "transfer")]
_ACC_OPTS     = [(f"{ACCOUNT_ICON[a]} {a}", a) for a in ACCOUNTS]
_EXP_CAT_OPTS = [(f"{CATEGORY_ICON.get(c, '[?]')} {c}", c) for c in EXPENSE_CATEGORIES]
_INC_CAT_OPTS = [(f"{CATEGORY_ICON.get(c, '[?]')} {c}", c) for c in INCOME_CATEGORIES]
_MONTH_NAMES  = ["Jan","Feb","Mar","Apr","May","Jun",
                 "Jul","Aug","Sep","Oct","Nov","Dec"]
_FILTER_KEYS  = ["all", "expense", "income", "transfer"]
_FILTER_NAMES = {"all": "All", "expense": "Expense",
                 "income": "Income", "transfer": "Transfer"}


# ══════════════════════════════════════════════════════════════════════════════
# Modals
# ══════════════════════════════════════════════════════════════════════════════

class TxDetailModal(ModalScreen):
    BINDINGS = [("escape,enter,q", "dismiss_modal", "Close")]

    DEFAULT_CSS = f"""
    TxDetailModal {{ align: center middle; }}
    #det-box {{
        width: 60; height: auto; max-height: 90%;
        border: round $primary; background: $background;
        padding: 0 0 1 0; overflow: hidden auto;
    }}
    #det-title {{
        height: 1;
        background: $surface-lighten-1; color: $primary;
        text-style: bold; padding: 0 2;
        border-bottom: solid $surface-lighten-2;
        margin-bottom: 1;
    }}
    .dr  {{ height: 1; layout: horizontal; padding: 0 2; }}
    .dl  {{ width: 12; color: $text-muted; }}
    .dv  {{ width: 1fr; overflow: hidden hidden; }}
    .df  {{ color: $text-muted; text-align: center; margin-top: 1; padding: 0 2; }}
    {_MODAL_RULE_CSS}
    """

    def __init__(self, tx: dict) -> None:
        super().__init__()
        self._tx = tx

    def compose(self) -> ComposeResult:
        tx   = self._tx
        kind = tx["type"]
        with Vertical(id="det-box"):
            yield Label(" ◆ Transaction Detail", id="det-title")
            with Horizontal(classes="dr"):
                yield Label("Type",    classes="dl")
                col = _rc(TYPE_COLOR[kind])
                yield Label(f"[{col}]{TYPE_LABEL[kind]} — {kind.title()}[/]",
                            markup=True, classes="dv")
            with Horizontal(classes="dr"):
                yield Label("Amount",  classes="dl")
                col  = "red"   if kind == "expense" else "green" if kind == "income" else "cyan"
                sign = "-"     if kind == "expense" else "+"     if kind == "income"  else "⇆"
                yield Label(f"[{col} bold]{sign}{fmt_rp(tx['amount'])}[/]",
                            markup=True, classes="dv")
            with Horizontal(classes="dr"):
                yield Label("Date",    classes="dl")
                yield Label(tx["date"].strftime("%A, %d %B %Y"), classes="dv")
            with Horizontal(classes="dr"):
                yield Label("Account", classes="dl")
                ac = _ACC_RICH.get(tx["account"], "white")
                al = f"{ACCOUNT_ICON.get(tx['account'], '[?]')} {tx['account']}"
                if kind == "transfer":
                    to = tx.get("to_account", "?")
                    tc = _ACC_RICH.get(to, "white")
                    ti = ACCOUNT_ICON.get(to, "[?]")
                    yield Label(f"[{ac}]{al}[/] → [{tc}]{ti} {to}[/]",
                                markup=True, classes="dv")
                else:
                    yield Label(f"[{ac}]{al}[/]", markup=True, classes="dv")
            if kind != "transfer" and tx.get("category"):
                cat = tx["category"]
                cc  = _rc(CATEGORY_COLOR.get(cat, "$text-muted"))
                ci  = CATEGORY_ICON.get(cat, "[?]")
                with Horizontal(classes="dr"):
                    yield Label("Category", classes="dl")
                    yield Label(f"[{cc}]{ci} {cat}[/]", markup=True, classes="dv")
            if tx.get("notes"):
                yield Rule()
                with Horizontal(classes="dr"):
                    yield Label("Notes", classes="dl")
                    yield Label(tx["notes"], classes="dv")
            yield Rule()
            yield Label("Enter / Esc  ·  Close", classes="df")

    def action_dismiss_modal(self) -> None:
        self.dismiss()


class ConfirmModal(ModalScreen):
    BINDINGS = [("y,enter", "yes", "Yes"), ("n,escape", "no", "No")]

    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    #cb {
        width: 50; height: 7;
        border: round $error; background: $background;
        padding: 1 2; align: center middle;
        layout: vertical; overflow: hidden hidden;
    }
    #cm { text-align: center; color: $text; margin-bottom: 1; }
    #ch { text-align: center; color: $text-muted; }
    """

    def __init__(self, msg: str) -> None:
        super().__init__()
        self._msg = msg

    def compose(self) -> ComposeResult:
        with Vertical(id="cb"):
            yield Label(self._msg, id="cm")
            yield Label("[ y / Enter ]  Yes    [ n / Esc ]  No", id="ch")

    def action_yes(self) -> None: self.dismiss(True)
    def action_no(self)  -> None: self.dismiss(False)


class TxFormModal(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel"), ("ctrl+s", "confirm", "Save")]

    DEFAULT_CSS = f"""
    TxFormModal {{ align: center middle; }}
    #form-box {{
        width: 60; height: auto; max-height: 90%;
        border: round $primary; background: $background;
        padding: 0 0 1 0; overflow: hidden auto;
    }}
    #form-title {{
        height: 1;
        background: $surface-lighten-1; color: $primary;
        text-style: bold; padding: 0 2;
        border-bottom: solid $surface-lighten-2;
        margin-bottom: 1;
    }}
    .fr  {{ height: 3; layout: horizontal; padding: 0 2; }}
    .fl  {{ width: 14; content-align: left middle; color: $text-muted; }}
    .fi  {{ width: 1fr; }}
    #form-err  {{ color: $error; height: 1; text-align: center; padding: 0 2; }}
    #form-hint {{ color: $text-muted; text-align: center; padding: 0 2; margin-top: 1; }}
    #form-btns {{ layout: horizontal; height: 3; padding: 0 2; margin-top: 1; }}
    #btn-save {{
        width: 1fr; margin-right: 1;
        background: $surface-lighten-1; border: round $primary;
        color: $primary; text-style: bold;
    }}
    #btn-save:hover  {{ background: $surface-lighten-2; }}
    #btn-cancel {{
        width: 1fr; background: transparent;
        border: round $surface-lighten-2; color: $text-muted;
    }}
    #btn-cancel:hover {{ background: $surface-lighten-1; color: $text; }}
    {_MODAL_RULE_CSS}
    """

    def __init__(self, tx: dict | None = None,
                 default_date: date | None = None) -> None:
        super().__init__()
        self._tx    = tx
        self._ddate = default_date or date.today()
        self._mode  = "Edit" if tx else "Add"

    def compose(self) -> ComposeResult:
        tx   = self._tx or {}
        kind = tx.get("type", "expense")
        cat_opts = _EXP_CAT_OPTS if kind != "income" else _INC_CAT_OPTS
        cat_val  = tx.get(
            "category",
            EXPENSE_CATEGORIES[0] if kind != "income" else INCOME_CATEGORIES[0],
        )
        with Vertical(id="form-box"):
            yield Label(f" ◆ {self._mode} Transaction", id="form-title")
            with Horizontal(classes="fr"):
                yield Label("Type",        classes="fl")
                yield Select(_TYPE_OPTS, value=kind, id="i-type", classes="fi")
            with Horizontal(classes="fr"):
                yield Label("Account",     classes="fl", id="lbl-account")
                yield Select(_ACC_OPTS, value=tx.get("account", ACCOUNTS[0]),
                             id="i-account", classes="fi")
            with Horizontal(classes="fr", id="row-to"):
                yield Label("To Account",  classes="fl")
                yield Select(_ACC_OPTS,
                             value=tx.get("to_account", ACCOUNTS[1]),
                             id="i-to", classes="fi")
            with Horizontal(classes="fr"):
                yield Label("Amount (Rp)", classes="fl")
                yield Input(
                    value=str(int(tx["amount"])) if tx.get("amount") else "",
                    placeholder="e.g. 150000",
                    id="i-amount", classes="fi")
            with Horizontal(classes="fr", id="row-cat"):
                yield Label("Category",    classes="fl")
                yield Select(cat_opts, value=cat_val, id="i-cat", classes="fi")
            with Horizontal(classes="fr"):
                yield Label("Date",        classes="fl")
                yield Input(
                    value=(tx["date"].isoformat()
                           if tx.get("date") else self._ddate.isoformat()),
                    placeholder="YYYY-MM-DD",
                    id="i-date", classes="fi")
            with Horizontal(classes="fr"):
                yield Label("Notes",       classes="fl")
                yield Input(value=tx.get("notes") or "",
                            placeholder="Optional",
                            id="i-notes", classes="fi")
            yield Label("", id="form-err")
            yield Rule()
            with Horizontal(id="form-btns"):
                yield Button("◆ Save",   id="btn-save",   variant="primary")
                yield Button("✕ Cancel", id="btn-cancel")
            yield Label("Ctrl+S  Save   ·   Esc  Cancel", id="form-hint")

    def on_mount(self) -> None:
        self._sync(self._tx.get("type", "expense") if self._tx else "expense")

    def on_select_changed(self, ev: Select.Changed) -> None:
        if ev.select.id == "i-type":
            self._sync(str(ev.value))

    def _sync(self, kind: str) -> None:
        self.query_one("#row-to",      Horizontal).display = (kind == "transfer")
        self.query_one("#row-cat",     Horizontal).display = (kind != "transfer")
        self.query_one("#lbl-account", Label).update(
            "From Account" if kind == "transfer" else "Account")
        self.query_one("#i-cat", Select).set_options(
            _INC_CAT_OPTS if kind == "income" else _EXP_CAT_OPTS)

    def action_confirm(self) -> None: self._save()
    def action_cancel(self)  -> None: self.dismiss(None)

    def on_button_pressed(self, ev: Button.Pressed) -> None:
        if   ev.button.id == "btn-save":   self._save()
        elif ev.button.id == "btn-cancel": self.dismiss(None)

    def _save(self) -> None:
        err = self.query_one("#form-err", Label)
        try:
            from textual.widgets._select import BLANK
        except ImportError:
            BLANK = None

        kind    = self.query_one("#i-type",    Select).value
        account = self.query_one("#i-account", Select).value
        amt_raw = self.query_one("#i-amount",  Input).value.strip()
        dt_raw  = self.query_one("#i-date",    Input).value.strip()
        notes   = self.query_one("#i-notes",   Input).value.strip() or None

        if BLANK is not None:
            if kind    is BLANK: err.update("Select a type.");     return
            if account is BLANK: err.update("Select an account."); return

        try:
            amount = float(amt_raw.replace(",", "").replace(".", ""))
            if amount <= 0: raise ValueError
        except ValueError:
            err.update("Enter a valid positive amount."); return

        try:
            tx_date = date.fromisoformat(dt_raw)
        except ValueError:
            err.update("Invalid date — use YYYY-MM-DD."); return

        result: dict = {
            "type": str(kind), "account": str(account),
            "amount": amount, "date": tx_date, "notes": notes,
        }
        if str(kind) == "transfer":
            to = self.query_one("#i-to", Select).value
            if BLANK is not None and to is BLANK:
                err.update("Select a destination account."); return
            if str(to) == str(account):
                err.update("From and To must differ."); return
            result["to_account"] = str(to)
            result["category"]   = None
        else:
            cat = self.query_one("#i-cat", Select).value
            if BLANK is not None and cat is BLANK:
                err.update("Select a category."); return
            result["category"]   = str(cat)
            result["to_account"] = None
        self.dismiss(result)


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════

class FinanceSidebar(Widget):
    """Left sidebar: account balances + this-month summary."""

    DEFAULT_CSS = """
    FinanceSidebar {
        width: 28;
        height: 1fr;
        layout: vertical;
        overflow: hidden hidden;
        padding: 0 1 0 0;
    }

    .sb-box {
        width: 100%;
        height: auto;
        border: round $surface-lighten-2;
        padding: 0 1 1 1;
        margin-bottom: 1;
        overflow: hidden hidden;
    }

    .sb-row { height: 1; layout: horizontal; width: 100%; }
    .sb-lbl { width: 1fr; overflow: hidden hidden; color: $text-muted; }
    .sb-val { width: 9; text-align: right; text-style: bold; }
    .sb-sep { height: 1; color: $surface-lighten-2; }

    .acc-gopay   { color: $primary; }
    .acc-seabank { color: $success; }
    .acc-neobank { color: $accent;  }
    .acc-cash    { color: $warning; }
    """

    _ACC_CLS = {
        "GoPay":   "acc-gopay",
        "SeaBank": "acc-seabank",
        "NeoBank": "acc-neobank",
        "Cash":    "acc-cash",
    }

    def compose(self) -> ComposeResult:
        with Vertical(classes="sb-box") as b:
            b.border_title = "Accounts"
            for acc in ACCOUNTS:
                with Horizontal(classes="sb-row"):
                    yield Label(
                        f"● {ACCOUNT_ICON[acc]} {acc}",
                        classes=f"sb-lbl {self._ACC_CLS[acc]}")
                    yield Label("", id=f"bal-{acc.lower()}", classes="sb-val")
            yield Label("─" * 22, classes="sb-sep")
            with Horizontal(classes="sb-row"):
                yield Label("Total", classes="sb-lbl")
                yield Label("", id="bal-total", classes="sb-val")

        with Vertical(classes="sb-box") as b2:
            b2.border_title = "This Month"
            with Horizontal(classes="sb-row"):
                yield Label("↑ Income",  classes="sb-lbl")
                yield Label("", id="mon-inc", classes="sb-val")
            with Horizontal(classes="sb-row"):
                yield Label("↓ Expense", classes="sb-lbl")
                yield Label("", id="mon-exp", classes="sb-val")
            yield Label("─" * 22, classes="sb-sep")
            with Horizontal(classes="sb-row"):
                yield Label("= Net", classes="sb-lbl")
                yield Label("", id="mon-net", classes="sb-val")

    def refresh_data(self, data: dict) -> None:
        accounts = data.get("accounts", {})
        total    = 0.0
        for acc in ACCOUNTS:
            bal    = accounts.get(acc, 0)
            total += bal
            color  = "green" if bal >= 0 else "red"
            self.query_one(f"#bal-{acc.lower()}", Label).update(
                f"[{color}]{fmt_rp_short(bal)}[/]")
        tc = "green" if total >= 0 else "red"
        self.query_one("#bal-total", Label).update(
            f"[{tc} bold]{fmt_rp_short(total)}[/]")

        today = date.today()
        ms    = get_monthly_summary(data["transactions"], today.year, today.month)
        self.query_one("#mon-inc", Label).update(
            f"[green]{fmt_rp_short(ms['income'])}[/]")
        self.query_one("#mon-exp", Label).update(
            f"[red]{fmt_rp_short(ms['expense'])}[/]")
        nc = "green" if ms["net"] >= 0 else "red"
        self.query_one("#mon-net", Label).update(
            f"[{nc}]{fmt_rp_short(ms['net'])}[/]")


# ══════════════════════════════════════════════════════════════════════════════
# Analysis panel
# ══════════════════════════════════════════════════════════════════════════════

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
        height: 1;
        layout: horizontal;
        margin-bottom: 1;
    }
    .an-period-lbl {
        width: auto; height: 1;
        color: $text-muted; content-align: left middle; padding: 0 1;
    }
    .an-period-btn {
        width: auto; height: 1;
        background: transparent; border: none;
        color: $text-muted; padding: 0 1; margin-right: 1;
    }
    .an-period-btn.active { color: $primary; text-style: bold underline; border: none; }
    .an-period-btn:hover  { color: $text; border: none; }
    .an-period-btn:focus  { border: none; }

    /* ── chart area ──────────────────────────────────── */
    #an-chart { width: 100%; height: auto; layout: vertical; }

    /* per-month card */
    .an-card {
        width: 100%;
        height: auto;
        border: round $surface-lighten-2;
        padding: 0 1 1 1;
        margin-bottom: 1;
        layout: vertical;
    }
    .an-card-now { border: round $primary; }

    /* rows inside a card */
    .an-row { height: 1; layout: horizontal; width: 100%; }
    .an-lbl { width: 5; color: $text-muted; content-align: left middle; }
    .an-amt { width: 12; text-align: right; content-align: right middle; }
    .an-net { height: 1; color: $text-muted; }

    /* progress bars — colour the filled portion per type */
    .an-inc-bar { width: 1fr; margin-bottom: 1; }
    .an-exp-bar { width: 1fr; margin-bottom: 1; }
    .an-inc-bar > .bar--bar { color: $success; }
    .an-exp-bar > .bar--bar { color: $error;   }
    .an-inc-bar > .bar--complete { color: $success; }
    .an-exp-bar > .bar--complete { color: $error;   }

    /* ── summary box ─────────────────────────────────── */
    #an-sum {
        width: 100%; height: auto;
        border: round $surface-lighten-2;
        padding: 0 1 1 1;
        margin-top: 1;
    }
    .an-sum-head { height: 1; color: $primary; text-style: bold; }
    .an-sum-row  { height: 1; layout: horizontal; width: 100%; }
    .an-sum-lbl  { width: 1fr; color: $text-muted; }
    .an-sum-val  { width: 16; text-align: right; }
    """

    _period: reactive[int] = reactive(6)

    def compose(self) -> ComposeResult:
        with Horizontal(id="an-period-row"):
            yield Label("Period:", classes="an-period-lbl")
            for lbl, n in self._PERIODS:
                yield Button(lbl, id=f"an-p-{n}",
                             classes="an-period-btn" + (" active" if n == 6 else ""))
        yield Vertical(id="an-chart")
        with Vertical(id="an-sum"):
            yield Label("Summary", classes="an-sum-head")
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
                    self.query_one(f"#an-p-{m}", Button).set_class(m == n, "active")
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

            # card container — border changes colour for current month
            card_cls = "an-card an-card-now" if is_now else "an-card"
            card = Vertical(classes=card_cls)
            if is_now:
                card.border_title = f"{name}  ◂ current"
            else:
                card.border_title = name
            chart.mount(card)

            # INC header row
            inc_hdr = Horizontal(classes="an-row")
            card.mount(inc_hdr)
            inc_hdr.mount(Label("INC", classes="an-lbl"))
            inc_hdr.mount(Label(
                f"[green]{fmt_rp_short(m['income'])}[/]",
                markup=True, classes="an-amt"))

            # INC progress bar
            card.mount(ProgressBar(
                total=max_val, id=f"an-inc-{i}",
                show_eta=False, classes="an-inc-bar"))

            # EXP header row
            exp_hdr = Horizontal(classes="an-row")
            card.mount(exp_hdr)
            exp_hdr.mount(Label("EXP", classes="an-lbl"))
            exp_hdr.mount(Label(
                f"[red]{fmt_rp_short(m['expense'])}[/]",
                markup=True, classes="an-amt"))

            # EXP progress bar
            card.mount(ProgressBar(
                total=max_val, id=f"an-exp-{i}",
                show_eta=False, classes="an-exp-bar"))

            # net line
            card.mount(Label(
                f"[{nc}]{ns}[/] net",
                markup=True, classes="an-net"))

        # Set progress values after all widgets are mounted
        for i, m in enumerate(months):
            self.query_one(f"#an-inc-{i}", ProgressBar).progress = m["income"]
            self.query_one(f"#an-exp-{i}", ProgressBar).progress = m["expense"]

        # Update summary
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


# ══════════════════════════════════════════════════════════════════════════════
# Finance — root widget
# ══════════════════════════════════════════════════════════════════════════════

class Finance(Widget):

    BINDINGS = [
        Binding("a",     "add",    "Add",    show=False),
        Binding("e",     "edit",   "Edit",   show=False),
        Binding("d",     "delete", "Delete", show=False),
        Binding("enter", "detail", "Detail", show=False),
        Binding("f",     "filter", "Filter", show=False),
        Binding("r",     "reload", "Reload", show=False),
    ]

    DEFAULT_CSS = """
    Finance {
        layout: vertical;
        height: 1fr;
        width: 100%;
        background: $background;
    }

    /* body row ─────────────────────────────────────── */
    #fin-body {
        layout: horizontal;
        height: 1fr;
        width: 100%;
        padding: 1 1 0 1;
    }

    /* tabbed area ──────────────────────────────────── */
    #fin-tabs {
        width: 1fr;
        height: 100%;
    }
    #fin-tabs > TabbedContent > TabPane {
        padding: 0;
        height: 1fr;
    }

    /* transactions pane ────────────────────────────── */
    #tx-pane {
        layout: vertical;
        height: 1fr;
        width: 100%;
        padding: 1 1 0 1;
    }

    /* round border box — mirrors the analysis ScrollableContainer */
    #tx-box {
        layout: vertical;
        height: 1fr;
        width: 100%;
        border: round $surface-lighten-2;
        padding: 0 1;
        overflow: hidden hidden;
    }

    /* filter bar */
    #filter-bar {
        height: 3;
        layout: horizontal;
        margin-bottom: 1;
    }
    .flt-btn {
        width: auto;
        min-width: 12;
        height: 3;
        background: transparent;
        border: round $surface-lighten-2;
        color: $text-muted;
        padding: 0 2;
    }
    .flt-btn:hover {
        color: $text;
        border: round $surface-lighten-3;
    }
    .flt-btn:focus {
        border: round $surface-lighten-2;
    }
    .flt-btn.active {
        color: $primary;
        text-style: bold;
        border: round $primary;
    }

    /* info row */
    #info-bar {
        height: 1;
        layout: horizontal;
        margin-bottom: 1;
    }
    #lbl-title { width: 1fr; color: $primary; text-style: bold; }
    #lbl-count { color: $text-muted; text-style: italic; }

    /* table */
    #tx-table {
        height: 1fr;
        width: 100%;
        background: transparent;
    }
    #no-txs {
        height: 1fr;
        width: 100%;
        color: $text-muted;
        text-style: italic;
        content-align: center middle;
    }

    /* analysis pane ────────────────────────────────── */
    #an-scroll {
        height: 1fr;
        width: 100%;
    }

    /* footer ───────────────────────────────────────── */
    #key-hints {
        height: 1;
        width: 100%;
        background: $surface;
        border-top: solid $surface-lighten-1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    _filter: reactive[str] = reactive("all")

    def __init__(self) -> None:
        super().__init__()
        self._data:    dict       = {"accounts": {}, "transactions": []}
        self._vis_txs: list[dict] = []

    # ── compose ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal(id="fin-body"):
            yield FinanceSidebar(id="fin-sidebar")
            with TabbedContent(id="fin-tabs"):
                with TabPane("Transactions", id="tab-tx"):
                    with Vertical(id="tx-pane"):
                        with Vertical(id="tx-box"):
                            with Horizontal(id="filter-bar"):
                                for key in _FILTER_KEYS:
                                    yield Button(
                                        _FILTER_NAMES[key],
                                        id=f"flt-{key}",
                                        classes="flt-btn" + (" active" if key == "all" else ""),
                                    )
                            with Horizontal(id="info-bar"):
                                yield Label("", id="lbl-title")
                                yield Label("", id="lbl-count")
                            yield DataTable(
                                id="tx-table",
                                show_header=True,
                                cursor_type="row",
                                zebra_stripes=False,
                            )
                            yield Label(
                                "No transactions  ·  press [a] to add one",
                                id="no-txs",
                            )
                with TabPane("Analysis", id="tab-an"):
                    with ScrollableContainer(id="an-scroll"):
                        yield AnalysisPanel(id="analysis")

        yield Static(
            " [a] Add  [e] Edit  [d] Del  [↵] Detail  [f] Filter  [r] Reload",
            id="key-hints",
        )

    def on_mount(self) -> None:
        self._data = load_data()
        tbl = self.query_one("#tx-table", DataTable)
        tbl.add_columns("DATE", "TYPE", "ACCOUNT", "CATEGORY", "AMOUNT", "NOTES")
        self._refresh()

    # ── tab switch ────────────────────────────────────────────────────────────

    def on_tabbed_content_tab_activated(
        self, ev: TabbedContent.TabActivated
    ) -> None:
        if ev.tab.id == "tab-an":
            self.query_one("#analysis", AnalysisPanel).rebuild(
                self._data["transactions"])

    # ── filter buttons ────────────────────────────────────────────────────────

    def on_button_pressed(self, ev: Button.Pressed) -> None:
        bid = ev.button.id or ""
        if bid.startswith("flt-"):
            key = bid[4:]
            if key in _FILTER_KEYS:
                self._filter = key
                for k in _FILTER_KEYS:
                    self.query_one(f"#flt-{k}", Button).set_class(k == key, "active")
                self._rebuild_table()
            ev.stop()

    def action_filter(self) -> None:
        idx = _FILTER_KEYS.index(self._filter)
        nxt = _FILTER_KEYS[(idx + 1) % len(_FILTER_KEYS)]
        self.query_one(f"#flt-{nxt}", Button).press()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def action_add(self) -> None:
        def cb(r: dict | None) -> None:
            if r:
                add_transaction(self._data, r)
                self._refresh()
        self.app.push_screen(TxFormModal(default_date=date.today()), cb)

    def action_edit(self) -> None:
        tx = self._cursor()
        if not tx: return
        def cb(r: dict | None) -> None:
            if r:
                update_transaction(self._data, tx["id"], r)
                self._refresh()
        self.app.push_screen(TxFormModal(tx=tx), cb)

    def action_delete(self) -> None:
        tx = self._cursor()
        if not tx: return
        def cb(ok: bool) -> None:
            if ok:
                delete_transaction(self._data, tx["id"])
                self._refresh()
        self.app.push_screen(ConfirmModal("Delete this transaction?"), cb)

    def action_detail(self) -> None:
        tx = self._cursor()
        if tx:
            self.app.push_screen(TxDetailModal(tx))

    def action_reload(self) -> None:
        self._data = load_data()
        self._refresh()

    # ── internals ─────────────────────────────────────────────────────────────

    def _cursor(self) -> dict | None:
        if not self._vis_txs: return None
        idx = self.query_one("#tx-table", DataTable).cursor_row
        return self._vis_txs[idx] if 0 <= idx < len(self._vis_txs) else None

    def _refresh(self) -> None:
        self.query_one("#fin-sidebar", FinanceSidebar).refresh_data(self._data)
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        txs = sorted(
            self._data["transactions"],
            key=lambda t: (t["date"], t.get("id", 0)),
            reverse=True,
        )
        if self._filter != "all":
            txs = [t for t in txs if t["type"] == self._filter]
        self._vis_txs = txs

        table  = self.query_one("#tx-table", DataTable)
        no_txs = self.query_one("#no-txs",   Label)

        self.query_one("#lbl-title", Label).update(
            f"◆ {_FILTER_NAMES[self._filter]} Transactions")
        self.query_one("#lbl-count", Label).update(
            f"{len(txs)} record{'s' if len(txs) != 1 else ''}" if txs else "")

        table.clear(columns=True)
        table.add_columns("DATE", "TYPE", "ACCOUNT", "CATEGORY", "AMOUNT", "NOTES")

        if not txs:
            table.display  = False
            no_txs.display = True
            return

        table.display  = True
        no_txs.display = False

        today = date.today()
        for tx in txs:
            kind, d = tx["type"], tx["date"]
            ago = (today - d).days

            # date
            if   d == today: date_c = "[yellow bold]Today[/]"
            elif ago == 1:   date_c = "[dim white]Yesterday[/]"
            elif ago <= 7:   date_c = f"[dim white]{d.strftime('%a %d')}[/]"
            else:            date_c = f"[dim]{d.strftime('%b %d')}[/]"

            # type
            type_c = _TYPE_PILL.get(kind, kind)

            # account
            acc = tx["account"]
            ac  = _ACC_RICH.get(acc, "white")
            ai  = ACCOUNT_ICON.get(acc, "[?]")
            if kind == "transfer":
                to  = tx.get("to_account", "?")
                tc  = _ACC_RICH.get(to, "white")
                ti  = ACCOUNT_ICON.get(to, "[?]")
                acc_c = f"[{ac}]● {ai} {acc}[/] [dim]→[/] [{tc}]{ti} {to}[/]"
            else:
                acc_c = f"[{ac}]● {ai} {acc}[/]"

            # category
            if kind == "transfer":
                cat_c = "[dim]──[/]"
            else:
                cat   = tx.get("category", "Other")
                cc    = _rc(CATEGORY_COLOR.get(cat, "$text-muted"))
                ci    = CATEGORY_ICON.get(cat, "[?]")
                cat_c = f"[{cc}]{ci} {cat}[/]"

            # amount
            amt = tx["amount"]
            if   kind == "expense":  amt_c = f"[red bold]-{fmt_rp(amt)}[/]"
            elif kind == "income":   amt_c = f"[green bold]+{fmt_rp(amt)}[/]"
            else:                    amt_c = f"[cyan]{fmt_rp(amt)}[/]"

            table.add_row(
                date_c, type_c, acc_c, cat_c, amt_c,
                f"[dim]{tx.get('notes') or ''}[/]",
                key=str(tx["id"]),
            )