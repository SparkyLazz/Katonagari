"""
finance.py — Finance tab for Katonagari.

Screen tree (every node has explicit size):

  Finance                          layout:vertical  height:1fr  width:100%
  ├── Horizontal #fin-body         layout:horizontal  height:1fr
  │   ├── Vertical #fin-sidebar    width:26  height:100%
  │   │   ├── SidebarBox Accounts
  │   │   └── SidebarBox This Month
  │   └── TabbedContent #fin-tabs  width:1fr  height:100%
  │       ├── TabPane Transactions  height:1fr  padding:0
  │       │   └── Vertical #tx-pane  height:1fr
  │       │       ├── Horizontal #filter-bar   height:3
  │       │       ├── Horizontal #count-bar    height:1
  │       │       └── DataTable / Label        height:1fr
  │       └── TabPane Analysis      height:1fr  padding:0
  │           └── ScrollableContainer #an-scroll  height:1fr
  │               └── AnalysisPanel
  └── Static #key-hints             height:1
"""
from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button, DataTable, Input, Label, Rule, Select, Static,
    TabbedContent, TabPane,
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


# ── helpers ───────────────────────────────────────────────────────────────────

_RICH: dict[str, str] = {
    "$error":      "red",
    "$warning":    "yellow",
    "$primary":    "blue",
    "$success":    "green",
    "$accent":     "cyan",
    "$text-muted": "dim white",
}
def _rc(css_var: str) -> str:
    return _RICH.get(css_var, "white")


_MODAL_RULE = "Rule { color: $surface-lighten-2; margin: 0 1; height: 1; }"

_TYPE_OPTS    = [("↓ Expense","expense"),("↑ Income","income"),("⇆ Transfer","transfer")]
_ACC_OPTS     = [(f"{ACCOUNT_ICON[a]} {a}", a) for a in ACCOUNTS]
_EXP_CAT_OPTS = [(f"{CATEGORY_ICON.get(c,'[?]')} {c}", c) for c in EXPENSE_CATEGORIES]
_INC_CAT_OPTS = [(f"{CATEGORY_ICON.get(c,'[?]')} {c}", c) for c in INCOME_CATEGORIES]
_MONTH_NAMES  = ["Jan","Feb","Mar","Apr","May","Jun",
                 "Jul","Aug","Sep","Oct","Nov","Dec"]

_FILTER_KEYS  = ["all","expense","income","transfer"]
_FILTER_NAMES = {"all":"All","expense":"Expense","income":"Income","transfer":"Transfer"}


# ══════════════════════════════════════════════════════════════════════════════
# Modals
# ══════════════════════════════════════════════════════════════════════════════

class TxDetailModal(ModalScreen):
    BINDINGS = [("escape,enter,q","dismiss_modal","Close")]
    DEFAULT_CSS = f"""
    TxDetailModal {{ align: center middle; }}
    #det-box {{
        width: 60; height: auto; max-height: 90%;
        border: round $surface-lighten-2; background: $background;
        padding: 0 0 1 0; overflow: hidden auto;
    }}
    #det-title {{
        height: 1; background: $primary 15%; color: $primary;
        text-style: bold; padding: 0 2;
        border-bottom: solid $surface-lighten-1; margin-bottom: 1;
    }}
    .dr {{ height:1; layout:horizontal; padding:0 2; }}
    .dl {{ width:12; color:$text-muted; }}
    .dv {{ width:1fr; overflow:hidden hidden; }}
    .df {{ color:$text-muted; text-align:center; margin-top:1; padding:0 2; }}
    {_MODAL_RULE}
    """
    def __init__(self, tx: dict) -> None:
        super().__init__(); self._tx = tx

    def compose(self) -> ComposeResult:
        tx = self._tx; kind = tx["type"]
        with Vertical(id="det-box"):
            yield Label(" ◆ Transaction Detail", id="det-title")
            with Horizontal(classes="dr"):
                yield Label("Type",    classes="dl")
                yield Label(f"[{_rc(TYPE_COLOR[kind])}]{TYPE_LABEL[kind]} – {kind.title()}[/]",
                            classes="dv", markup=True)
            with Horizontal(classes="dr"):
                yield Label("Amount",  classes="dl")
                col  = "red" if kind=="expense" else "green" if kind=="income" else "cyan"
                sign = "-"   if kind=="expense" else "+"    if kind=="income"  else "⇆"
                yield Label(f"[{col} bold]{sign}{fmt_rp(tx['amount'])}[/]",
                            classes="dv", markup=True)
            with Horizontal(classes="dr"):
                yield Label("Date",    classes="dl")
                yield Label(tx["date"].strftime("%A, %d %B %Y"), classes="dv")
            with Horizontal(classes="dr"):
                yield Label("Account", classes="dl")
                ac = _rc(ACCOUNT_COLOR.get(tx["account"],"$text-muted"))
                al = f"{ACCOUNT_ICON.get(tx['account'],'[?]')} {tx['account']}"
                if kind == "transfer":
                    to = tx.get("to_account","?")
                    tc = _rc(ACCOUNT_COLOR.get(to,"$text-muted"))
                    ti = ACCOUNT_ICON.get(to,"[?]")
                    yield Label(f"[{ac}]{al}[/] → [{tc}]{ti} {to}[/]",
                                classes="dv", markup=True)
                else:
                    yield Label(f"[{ac}]{al}[/]", classes="dv", markup=True)
            if kind != "transfer" and tx.get("category"):
                cat = tx["category"]
                with Horizontal(classes="dr"):
                    yield Label("Category", classes="dl")
                    yield Label(
                        f"[{_rc(CATEGORY_COLOR.get(cat,'$text-muted'))}]"
                        f"{CATEGORY_ICON.get(cat,'[?]')} {cat}[/]",
                        classes="dv", markup=True)
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
    BINDINGS = [("y,enter","yes","Yes"),("n,escape","no","No")]
    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    #cb {
        width: 50; height: 7; border: round $error; background: $background;
        padding: 1 2; align: center middle; layout: vertical; overflow: hidden hidden;
    }
    #cm { text-align: center; color: $text; margin-bottom: 1; }
    #ch { text-align: center; color: $text-muted; }
    """
    def __init__(self, msg: str) -> None:
        super().__init__(); self._msg = msg
    def compose(self) -> ComposeResult:
        with Vertical(id="cb"):
            yield Label(self._msg, id="cm")
            yield Label("[ y / Enter ]  Yes    [ n / Esc ]  No", id="ch")
    def action_yes(self) -> None: self.dismiss(True)
    def action_no(self)  -> None: self.dismiss(False)


class TxFormModal(ModalScreen):
    BINDINGS = [("escape","cancel","Cancel"),("ctrl+s","confirm","Save")]
    DEFAULT_CSS = f"""
    TxFormModal {{ align: center middle; }}
    #form-box {{
        width: 60; height: auto; max-height: 90%;
        border: round $surface-lighten-2; background: $background;
        padding: 0 0 1 0; overflow: hidden auto;
    }}
    #form-title {{
        height: 1; background: $primary 15%; color: $primary;
        text-style: bold; padding: 0 2;
        border-bottom: solid $surface-lighten-1; margin-bottom: 1;
    }}
    .fr {{ height: 3; layout: horizontal; padding: 0 2; }}
    .fl {{ width: 14; content-align: left middle; color: $text-muted; }}
    .fi {{ width: 1fr; }}
    #form-err  {{ color: $error; height: 1; text-align: center; padding: 0 2; }}
    #form-hint {{ color: $text-muted; text-align: center; padding: 0 2; margin-top: 1; }}
    #form-btns {{ layout: horizontal; height: 3; padding: 0 2; margin-top: 1; }}
    #btn-save {{
        width: 1fr; margin-right: 1;
        background: $primary 12%; border: round $primary;
        color: $primary; text-style: bold;
    }}
    #btn-save:hover {{ background: $primary 22%; }}
    #btn-save:focus {{ background: $primary 18%; text-style: bold; }}
    #btn-cancel {{
        width: 1fr; background: transparent;
        border: round $surface-lighten-3; color: $text-muted;
    }}
    #btn-cancel:hover {{ background: $surface 30%; color: $text; }}
    {_MODAL_RULE}
    """

    def __init__(self, tx: dict | None = None,
                 default_date: date | None = None) -> None:
        super().__init__()
        self._tx    = tx
        self._ddate = default_date or date.today()
        self._mode  = "Edit" if tx else "Add"

    def compose(self) -> ComposeResult:
        tx   = self._tx or {}
        kind = tx.get("type","expense")
        cat_opts  = _EXP_CAT_OPTS if kind != "income" else _INC_CAT_OPTS
        cat_val   = tx.get("category",
                           EXPENSE_CATEGORIES[0] if kind != "income"
                           else INCOME_CATEGORIES[0])
        with Vertical(id="form-box"):
            yield Label(f" ◆ {self._mode} Transaction", id="form-title")
            with Horizontal(classes="fr"):
                yield Label("Type",         classes="fl")
                yield Select(_TYPE_OPTS, value=kind, id="i-type", classes="fi")
            with Horizontal(classes="fr"):
                yield Label("Account",      classes="fl", id="lbl-account")
                yield Select(_ACC_OPTS, value=tx.get("account",ACCOUNTS[0]),
                             id="i-account", classes="fi")
            with Horizontal(classes="fr", id="row-to"):
                yield Label("To Account",   classes="fl")
                yield Select(_ACC_OPTS, value=tx.get("to_account",ACCOUNTS[1]),
                             id="i-to", classes="fi")
            with Horizontal(classes="fr"):
                yield Label("Amount (Rp)",  classes="fl")
                yield Input(value=str(int(tx["amount"])) if tx.get("amount") else "",
                            placeholder="e.g. 150000",
                            id="i-amount", classes="fi")
            with Horizontal(classes="fr", id="row-cat"):
                yield Label("Category",     classes="fl")
                yield Select(cat_opts, value=cat_val, id="i-cat", classes="fi")
            with Horizontal(classes="fr"):
                yield Label("Date",         classes="fl")
                yield Input(
                    value=(tx["date"].isoformat() if tx.get("date")
                           else self._ddate.isoformat()),
                    placeholder="YYYY-MM-DD", id="i-date", classes="fi")
            with Horizontal(classes="fr"):
                yield Label("Notes",        classes="fl")
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
        self._sync(self._tx.get("type","expense") if self._tx else "expense")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "i-type":
            self._sync(str(event.value))

    def _sync(self, kind: str) -> None:
        self.query_one("#row-to",    Horizontal).display = (kind == "transfer")
        self.query_one("#row-cat",   Horizontal).display = (kind != "transfer")
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
            if kind    is BLANK: err.update("Select a type."); return
            if account is BLANK: err.update("Select an account."); return

        try:
            amount = float(amt_raw.replace(",","").replace(".",""))
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
# Sidebar (shared between both tabs)
# ══════════════════════════════════════════════════════════════════════════════

class FinanceSidebar(Widget):
    """Left sidebar: account balances + this-month summary."""

    DEFAULT_CSS = """
    FinanceSidebar {
        width: 26;
        height: 100%;
        layout: vertical;
        overflow: hidden hidden;
        padding: 0 1 1 0;
    }

    /* Section boxes */
    .sec-box {
        width: 100%;
        height: auto;
        border: round $surface-lighten-2;
        background: $surface 25%;
        padding: 0 1 1 1;
        margin-bottom: 1;
        overflow: hidden hidden;
    }

    /* Row inside a section */
    .s-row { height: 1; layout: horizontal; width: 100%; }
    .s-lbl { width: 1fr; color: $text-muted; overflow: hidden hidden; }
    .s-val { width: 9; text-align: right; text-style: bold; overflow: hidden hidden; }

    /* Divider */
    .s-div { height: 1; color: $surface-lighten-2; margin: 0; }

    /* Account colors */
    .col-gopay   { color: $primary; }
    .col-seabank { color: $success; }
    .col-neobank { color: $accent;  }
    .col-cash    { color: $warning; }
    """

    def compose(self) -> ComposeResult:
        # ── Accounts ──────────────────────────────────────────────────────────
        with Vertical(classes="sec-box") as box:
            box.border_title = "Accounts"
            for acc in ACCOUNTS:
                with Horizontal(classes="s-row"):
                    yield Label(
                        f"{ACCOUNT_ICON[acc]} {acc}",
                        classes=f"s-lbl col-{acc.lower()}")
                    yield Label("", id=f"bal-{acc.lower()}", classes="s-val")
            yield Label("──────────────────────", classes="s-div")
            with Horizontal(classes="s-row"):
                yield Label("Total", classes="s-lbl")
                yield Label("", id="bal-total", classes="s-val")

        # ── This Month ────────────────────────────────────────────────────────
        with Vertical(classes="sec-box") as box2:
            box2.border_title = "This Month"
            with Horizontal(classes="s-row"):
                yield Label("↑ Income",  classes="s-lbl")
                yield Label("", id="mon-inc", classes="s-val")
            with Horizontal(classes="s-row"):
                yield Label("↓ Expense", classes="s-lbl")
                yield Label("", id="mon-exp", classes="s-val")
            yield Label("──────────────────────", classes="s-div")
            with Horizontal(classes="s-row"):
                yield Label("= Net", classes="s-lbl")
                yield Label("", id="mon-net", classes="s-val")

    def refresh_data(self, data: dict) -> None:
        accounts = data.get("accounts", {})
        total    = 0.0
        for acc in ACCOUNTS:
            bal   = accounts.get(acc, 0)
            total += bal
            color = "green" if bal >= 0 else "red"
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
    """Income vs Expense ASCII bar chart with period selector."""

    _PERIODS = [("3M",3), ("6M",6), ("12M",12)]
    _BAR_W   = 16

    DEFAULT_CSS = """
    AnalysisPanel {
        width: 100%;
        height: auto;
        layout: vertical;
        background: transparent;
        padding: 0 1 1 1;
    }

    /* Period selector */
    #period-row {
        height: 1;
        layout: horizontal;
        margin-bottom: 2;
    }
    .p-btn {
        width: auto;
        height: 1;
        background: transparent;
        border: none;
        color: $text-muted;
        padding: 0 1;
        margin-right: 1;
        text-style: none;
    }
    .p-btn.active {
        color: $primary;
        text-style: bold underline;
        background: transparent;
        border: none;
    }
    .p-btn:hover { color: $text; background: transparent; border: none; }
    .p-btn:focus { background: transparent; border: none; }

    /* Chart rows */
    #chart-area {
        width: 100%;
        height: auto;
        layout: vertical;
    }
    .c-head  { height: 1; color: $text; text-style: bold; margin-top: 1; }
    .c-row   { height: 1; layout: horizontal; width: 100%; }
    .c-label { width: 5; color: $text-muted; }
    .c-bar   { width: 1fr; overflow: hidden hidden; }
    .c-amt   { width: 10; text-align: right; }
    .c-net   { height: 1; color: $text-muted; padding-left: 6; }
    .c-sep   { height: 1; }

    /* Summary box */
    #sum-box {
        width: 100%;
        height: auto;
        border: round $surface-lighten-2;
        background: $surface 20%;
        padding: 0 1 1 1;
        margin-top: 2;
    }
    .sum-head { height: 1; color: $primary; text-style: bold; }
    .sum-row  { height: 1; layout: horizontal; width: 100%; }
    .sum-lbl  { width: 1fr; color: $text-muted; }
    .sum-val  { width: 16; text-align: right; }
    """

    _period: reactive[int] = reactive(6)

    def compose(self) -> ComposeResult:
        with Horizontal(id="period-row"):
            yield Label("Period: ", classes="c-label")
            for label, n in self._PERIODS:
                yield Button(label, id=f"p-{n}",
                             classes="p-btn" + (" active" if n == 6 else ""))

        yield Vertical(id="chart-area")

        with Vertical(id="sum-box"):
            yield Label("── Summary ─────────────────────────", classes="sum-head")
            with Horizontal(classes="sum-row"):
                yield Label("Total Income",  classes="sum-lbl")
                yield Label("", id="s-inc",  classes="sum-val")
            with Horizontal(classes="sum-row"):
                yield Label("Total Expense", classes="sum-lbl")
                yield Label("", id="s-exp",  classes="sum-val")
            with Horizontal(classes="sum-row"):
                yield Label("Net Savings",   classes="sum-lbl")
                yield Label("", id="s-net",  classes="sum-val")
            with Horizontal(classes="sum-row"):
                yield Label("Savings Rate",  classes="sum-lbl")
                yield Label("", id="s-rate", classes="sum-val")

    def on_mount(self) -> None:
        self.rebuild([])

    def on_button_pressed(self, ev: Button.Pressed) -> None:
        for _, n in self._PERIODS:
            if ev.button.id == f"p-{n}":
                self._period = n
                for _, m in self._PERIODS:
                    self.query_one(f"#p-{m}", Button).set_class(m == n, "active")
                ev.stop()
                # rebuild with whatever was last passed
                self.rebuild(self._last_txs)
                return

    def rebuild(self, transactions: list) -> None:
        self._last_txs = transactions
        months  = get_last_n_months(transactions, self._period)
        chart   = self.query_one("#chart-area", Vertical)
        for child in list(chart.children):
            child.remove()

        max_val = max(
            max((m["income"]  for m in months), default=1),
            max((m["expense"] for m in months), default=1),
            1)

        def _bar(val: float, color: str) -> str:
            filled = max(1, int(val / max_val * self._BAR_W)) if val > 0 else 0
            empty  = self._BAR_W - filled
            return f"[{color}]{'█' * filled}[/][dim]{'░' * empty}[/]"

        today = date.today()
        for i, m in enumerate(months):
            name = f"{_MONTH_NAMES[m['month']-1]} '{str(m['year'])[2:]}"
            now  = (m["year"] == today.year and m["month"] == today.month)
            head = (f"[yellow bold]{name}  ◂ current[/]" if now
                    else f"[dim white]{name}[/]")

            chart.mount(Label(head, classes="c-head", markup=True))

            ir = Horizontal(classes="c-row"); chart.mount(ir)
            ir.mount(Label("INC  ", classes="c-label"))
            ir.mount(Label(_bar(m["income"], "green"), classes="c-bar", markup=True))
            ir.mount(Label(f"[green]{fmt_rp_short(m['income'])}[/]",
                           classes="c-amt", markup=True))

            er = Horizontal(classes="c-row"); chart.mount(er)
            er.mount(Label("EXP  ", classes="c-label"))
            er.mount(Label(_bar(m["expense"], "red"), classes="c-bar", markup=True))
            er.mount(Label(f"[red]{fmt_rp_short(m['expense'])}[/]",
                           classes="c-amt", markup=True))

            net = m["net"]
            nc  = "green" if net >= 0 else "red"
            ns  = ("+" if net >= 0 else "") + fmt_rp_short(net)
            chart.mount(Label(f"[{nc}]{ns}[/] net", classes="c-net", markup=True))

            if i < len(months) - 1:
                chart.mount(Label("", classes="c-sep"))

        total_inc = sum(m["income"]  for m in months)
        total_exp = sum(m["expense"] for m in months)
        total_net = total_inc - total_exp
        rate      = total_net / total_inc * 100 if total_inc > 0 else 0.0

        nc   = "green" if total_net >= 0 else "red"
        rc   = "green" if rate >= 20 else "yellow" if rate >= 0 else "red"
        sign = "+" if total_net >= 0 else ""

        self.query_one("#s-inc",  Label).update(f"[green]{fmt_rp(total_inc)}[/]")
        self.query_one("#s-exp",  Label).update(f"[red]{fmt_rp(total_exp)}[/]")
        self.query_one("#s-net",  Label).update(f"[{nc}]{sign}{fmt_rp(total_net)}[/]")
        self.query_one("#s-rate", Label).update(f"[{rc}]{rate:.1f}%[/]")


# ══════════════════════════════════════════════════════════════════════════════
# Finance — main widget
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
    /* ── Root ───────────────────────────────────────────────────────────── */
    Finance {
        layout: vertical;
        height: 1fr;
        width: 100%;
        background: $background;
    }

    /* ── Body row ───────────────────────────────────────────────────────── */
    #fin-body {
        layout: horizontal;
        height: 1fr;
        width: 100%;
        padding: 1 1 0 1;
    }

    /* ── TabbedContent fills remaining width ─────────────────────────────── */
    #fin-tabs {
        width: 1fr;
        height: 100%;
    }

    /* Make every TabPane fill the pane area, no extra padding */
    #fin-tabs > TabbedContent > TabPane {
        padding: 0;
        height: 1fr;
    }

    /* ── Transactions pane ───────────────────────────────────────────────── */
    #tx-pane {
        layout: vertical;
        height: 1fr;
        width: 100%;
        padding: 1 1 0 1;
    }

    /* Filter bar — plain text underline style */
    #filter-bar {
        height: 1;
        layout: horizontal;
        margin-bottom: 1;
    }
    .flt-btn {
        width: auto;
        height: 1;
        background: transparent;
        border: none;
        color: $text-muted;
        padding: 0 2;
        text-style: none;
    }
    .flt-btn:hover  { color: $text; background: transparent; border: none; }
    .flt-btn:focus  { background: transparent; border: none; }
    .flt-btn.active {
        color: $primary;
        text-style: bold underline;
        background: transparent;
        border: none;
    }

    /* Info row: title + count */
    #info-bar {
        height: 1;
        layout: horizontal;
        margin-bottom: 1;
    }
    #lbl-title { width: 1fr; color: $primary; text-style: bold; }
    #lbl-count { color: $text-muted; text-style: italic; }

    /* DataTable — fills remaining height */
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

    /* ── Analysis pane ───────────────────────────────────────────────────── */
    #an-scroll {
        height: 1fr;
        width: 100%;
        padding: 0;
    }

    /* ── Footer ──────────────────────────────────────────────────────────── */
    #key-hints {
        height: 1;
        width: 100%;
        background: $surface 25%;
        border-top: solid $surface-lighten-1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    _filter: reactive[str] = reactive("all")

    def __init__(self) -> None:
        super().__init__()
        self._data:    dict = {"accounts": {}, "transactions": []}
        self._vis_txs: list = []

    # ── compose ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal(id="fin-body"):
            yield FinanceSidebar(id="fin-sidebar")

            with TabbedContent(id="fin-tabs"):

                with TabPane("Transactions", id="tab-tx"):
                    with Vertical(id="tx-pane"):
                        with Horizontal(id="filter-bar"):
                            for key in _FILTER_KEYS:
                                yield Button(
                                    _FILTER_NAMES[key], id=f"flt-{key}",
                                    classes="flt-btn" + (" active" if key == "all" else ""))
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
        def cb(r):
            if r:
                add_transaction(self._data, r)
                self._refresh()
        self.app.push_screen(TxFormModal(default_date=date.today()), cb)

    def action_edit(self) -> None:
        tx = self._cursor()
        if not tx: return
        def cb(r):
            if r:
                update_transaction(self._data, tx["id"], r)
                self._refresh()
        self.app.push_screen(TxFormModal(tx=tx), cb)

    def action_delete(self) -> None:
        tx = self._cursor()
        if not tx: return
        def cb(ok):
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
        txs = sorted(self._data["transactions"],
                     key=lambda t: (t["date"], t.get("id", 0)),
                     reverse=True)
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

            if   d == today: date_c = "[yellow bold]Today[/]"
            elif ago == 1:   date_c = "[dim]Yesterday[/]"
            elif ago <= 7:   date_c = f"[dim white]{d.strftime('%a %d')}[/]"
            else:            date_c = f"[dim]{d.strftime('%b %d')}[/]"

            type_c = f"[{_rc(TYPE_COLOR[kind])}]{TYPE_LABEL[kind]}[/]"

            acc = tx["account"]
            ac  = _rc(ACCOUNT_COLOR.get(acc, "$text-muted"))
            ai  = ACCOUNT_ICON.get(acc, "[?]")
            if kind == "transfer":
                to   = tx.get("to_account", "?")
                tc   = _rc(ACCOUNT_COLOR.get(to, "$text-muted"))
                ti   = ACCOUNT_ICON.get(to, "[?]")
                acc_c = f"[{ac}]{ai} {acc}[/] → [{tc}]{ti} {to}[/]"
            else:
                acc_c = f"[{ac}]{ai} {acc}[/]"

            if kind == "transfer":
                cat_c = "[dim]──[/]"
            else:
                cat   = tx.get("category", "Other")
                cc    = _rc(CATEGORY_COLOR.get(cat, "$text-muted"))
                ci    = CATEGORY_ICON.get(cat, "[?]")
                cat_c = f"[{cc}]{ci} {cat}[/]"

            amt = tx["amount"]
            if   kind == "expense":  amt_c = f"[red bold]-{fmt_rp(amt)}[/]"
            elif kind == "income":   amt_c = f"[green bold]+{fmt_rp(amt)}[/]"
            else:                    amt_c = f"[cyan]{fmt_rp(amt)}[/]"

            table.add_row(
                date_c, type_c, acc_c, cat_c, amt_c,
                f"[dim]{tx.get('notes') or ''}[/]",
                key=str(tx["id"]),
            )