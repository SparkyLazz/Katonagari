from __future__ import annotations
from datetime import date

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button, Input, Label, Rule, Select,
)

from databases.financeData import (
    ACCOUNTS, ACCOUNT_ICON,
    EXPENSE_CATEGORIES, INCOME_CATEGORIES,
    CATEGORY_COLOR, CATEGORY_ICON,
    TYPE_COLOR, TYPE_LABEL,
    fmt_rp,
)
from .constants import (
    _rc, _ACC_RICH, _MODAL_RULE_CSS,
    _TYPE_OPTS, _ACC_OPTS, _EXP_CAT_OPTS, _INC_CAT_OPTS
)

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
