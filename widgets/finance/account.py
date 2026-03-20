"""
widgets/finance/accounts.py
────────────────────────────
Accounts management tab.

Layout:
┌──────────────────────────────────────────────────┐
│  [SeaBank: RP1,200] [GoPay: RP500] [Cash: RP300] │  ← AccountCards
├──────────────────────────────────────────────────┤
│              Transfer History table               │
└──────────────────────────────────────────────────┘

Keybindings: n = new account, t = transfer, x = delete account
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.validation import Length, Number
from textual.widget import Widget
from textual.widgets import DataTable, Input, Label, Static

from services.financeService import (
    ACCOUNT_TYPES,
    Account,
    FinanceService,
    fmt_amount,
)


# ─── Account Card ─────────────────────────────────────────────────────────────

class AccountCard(Widget):
    DEFAULT_CSS = """
    AccountCard {
        border: round $primary;
        padding: 0 1;
        width: 1fr;
        height: 9;
        min-width: 20;
    }
    AccountCard .acct-balance { text-style: bold; color: $success; }
    AccountCard .acct-type    { color: $text-muted; }
    AccountCard .acct-base    { color: $text-muted; }
    AccountCard.bank    { border: round $accent; }
    AccountCard.ewallet { border: round $warning; }
    AccountCard.cash    { border: round $success; }
    AccountCard.bank    .acct-balance { color: $accent; }
    AccountCard.ewallet .acct-balance { color: $warning; }
    AccountCard.cash    .acct-balance { color: $success; }
    """

    def __init__(self, acct: Account, balance: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._acct    = acct
        self._balance = balance

    def on_mount(self) -> None:
        self.border_title = self._acct.name
        type_class = self._acct.type.lower().replace("-", "").replace(" ", "")
        if type_class in ("bank", "ewallet", "cash"):
            self.add_class(type_class)

    def compose(self) -> ComposeResult:
        type_icons = {"Bank": "🏦", "E-Wallet": "📱", "Cash": "💵", "Other": "💰"}
        icon = type_icons.get(self._acct.type, "💰")
        with Vertical():
            yield Static(f"RP{self._balance:,}", classes="acct-balance")
            yield Label(f"{icon} {self._acct.type}", classes="acct-type")
            yield Label(f"[dim]base: RP{self._acct.base:,}[/]", classes="acct-base", markup=True)


# ─── Add Account Modal ───────────────────────────────────────────────────────

class AddAccountScreen(ModalScreen[Account | None]):
    DEFAULT_CSS = """
    AddAccountScreen { align: center middle; background: transparent; }
    AddAccountScreen #dialog {
        width: 50; height: auto;
        border: round $primary; background: transparent; padding: 1 2;
    }
    AddAccountScreen #title       { text-style: bold; color: $warning; margin-bottom: 1; }
    AddAccountScreen .field-label { color: $text-muted; margin-top: 1; height: 1; }
    AddAccountScreen Input        { width: 100%; }
    AddAccountScreen #error       { color: $error; height: 1; margin-top: 1; }
    AddAccountScreen #hint        { color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "submit", "Save"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("▸ ADD ACCOUNT", id="title")
            yield Label("Account name", classes="field-label")
            yield Input(placeholder="SeaBank", id="inp-name", validators=[Length(minimum=1)])
            yield Label(f"Type  ({' / '.join(ACCOUNT_TYPES)})", classes="field-label")
            yield Input(placeholder="Bank", id="inp-type")
            yield Label("Starting balance", classes="field-label")
            yield Input(placeholder="0", id="inp-base", validators=[Number()])
            yield Static("", id="error")
            yield Label("[dim]ctrl+s save · esc cancel[/]", id="hint", markup=True)

    def _save(self) -> None:
        name_val = self.query_one("#inp-name", Input).value.strip()
        type_val = self.query_one("#inp-type", Input).value.strip()
        base_val = self.query_one("#inp-base", Input).value.strip()
        if not name_val:
            self.query_one("#error", Static).update("⚠ Account name is required.")
            return
        if type_val not in ACCOUNT_TYPES:
            self.query_one("#error", Static).update(f"⚠ Type must be: {', '.join(ACCOUNT_TYPES)}")
            return
        try:
            base = int(base_val) if base_val else 0
        except ValueError:
            self.query_one("#error", Static).update("⚠ Balance must be a whole number.")
            return
        self.dismiss(Account(id="", name=name_val, type=type_val, base=base))

    def action_cancel(self) -> None: self.dismiss(None)
    def action_submit(self) -> None: self._save()


# ─── Transfer Modal ───────────────────────────────────────────────────────────

class TransferScreen(ModalScreen[dict | None]):
    DEFAULT_CSS = """
    TransferScreen { align: center middle; background: transparent; }
    TransferScreen #dialog {
        width: 52; height: auto;
        border: round $accent; background: transparent; padding: 1 2;
    }
    TransferScreen #title       { text-style: bold; color: $accent; margin-bottom: 1; }
    TransferScreen .field-label { color: $text-muted; margin-top: 1; height: 1; }
    TransferScreen Input        { width: 100%; }
    TransferScreen #acct-list   { color: $text-muted; }
    TransferScreen #error       { color: $error; height: 1; margin-top: 1; }
    TransferScreen #hint        { color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "submit", "Save"),
    ]

    def __init__(self, account_options: list[tuple[str, str]], **kwargs) -> None:
        super().__init__(**kwargs)
        self._options = account_options

    def compose(self) -> ComposeResult:
        acct_list = ", ".join(f"{name} ({aid})" for name, aid in self._options)
        with Vertical(id="dialog"):
            yield Static("▸ TRANSFER BETWEEN ACCOUNTS", id="title")
            yield Label(f"[dim]{acct_list}[/]", id="acct-list", markup=True)
            yield Label("Date  (YYYY-MM-DD)", classes="field-label")
            yield Input(placeholder="2026-03-20", id="inp-date", validators=[Length(minimum=10, maximum=10)])
            yield Label("From  (name or id)", classes="field-label")
            yield Input(placeholder="seabank", id="inp-from")
            yield Label("To  (name or id)", classes="field-label")
            yield Input(placeholder="gopay", id="inp-to")
            yield Label("Amount", classes="field-label")
            yield Input(placeholder="50000", id="inp-amount", validators=[Number()])
            yield Label("Description (optional)", classes="field-label")
            yield Input(placeholder="Top up GoPay", id="inp-desc")
            yield Static("", id="error")
            yield Label("[dim]ctrl+s save · esc cancel[/]", id="hint", markup=True)

    def _resolve(self, val: str) -> str | None:
        v = val.strip().lower()
        for name, aid in self._options:
            if aid.lower() == v or name.lower() == v:
                return aid
        return None

    def _save(self) -> None:
        from datetime import datetime
        date_val   = self.query_one("#inp-date",   Input).value.strip()
        from_val   = self.query_one("#inp-from",   Input).value.strip()
        to_val     = self.query_one("#inp-to",     Input).value.strip()
        amount_val = self.query_one("#inp-amount",  Input).value.strip()
        desc_val   = self.query_one("#inp-desc",    Input).value.strip()
        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            self.query_one("#error", Static).update("⚠ Date must be YYYY-MM-DD.")
            return
        from_id = self._resolve(from_val)
        to_id   = self._resolve(to_val)
        if not from_id:
            self.query_one("#error", Static).update(f"⚠ Unknown account: {from_val}")
            return
        if not to_id:
            self.query_one("#error", Static).update(f"⚠ Unknown account: {to_val}")
            return
        if from_id == to_id:
            self.query_one("#error", Static).update("⚠ From and To must differ.")
            return
        try:
            amount = int(amount_val)
            if amount <= 0: raise ValueError
        except ValueError:
            self.query_one("#error", Static).update("⚠ Amount must be a positive number.")
            return
        self.dismiss({"date": date_val, "from": from_id, "to": to_id, "amount": amount, "desc": desc_val})

    def action_cancel(self) -> None: self.dismiss(None)
    def action_submit(self) -> None: self._save()


# ─── Confirm Delete ───────────────────────────────────────────────────────────

class ConfirmDeleteAccountScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmDeleteAccountScreen { align: center middle; }
    ConfirmDeleteAccountScreen #dialog {
        width: 46; height: auto;
        border: round $error; background: $surface; padding: 1 2;
    }
    ConfirmDeleteAccountScreen #title { text-style: bold; color: $error; margin-bottom: 1; }
    ConfirmDeleteAccountScreen #desc  { color: $text-muted; margin-bottom: 1; }
    ConfirmDeleteAccountScreen #hint  { color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel"), Binding("y", "confirm", "Yes")]

    def __init__(self, acct: Account, **kwargs) -> None:
        super().__init__(**kwargs)
        self._acct = acct

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("▸ DELETE ACCOUNT", id="title")
            yield Static(
                f"[dim]Delete[/] [bold]{self._acct.name}[/] [dim]({self._acct.type})?[/]\n"
                f"[dim]Only works if no transactions reference it.[/]",
                id="desc", markup=True,
            )
            yield Label("[dim]y confirm · esc cancel[/]", id="hint", markup=True)

    def action_cancel(self)  -> None: self.dismiss(False)
    def action_confirm(self) -> None: self.dismiss(True)


# ─── Transfer History ─────────────────────────────────────────────────────────

class TransferHistory(Widget):
    DEFAULT_CSS = """
    TransferHistory {
        border: round $accent; width: 100%; height: 1fr;
    }
    TransferHistory DataTable { height: 1fr; background: transparent; }
    """

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        self.border_title = "Transfer History"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Date", "From", "To", "Amount", "Description")
        table.cursor_type = "row"
        self._fill()

    def _fill(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for t in reversed(self._svc.transfers):
            table.add_row(
                f"[dim]{t.display_date}[/]",
                self._svc.account_name(t.from_acct),
                self._svc.account_name(t.to_acct),
                f"[cyan]RP{t.amount:,}[/]",
                t.desc or "[dim]—[/]",
            )
        count = len(self._svc.transfers)
        self.border_subtitle = f"{count} transfer{'s' if count != 1 else ''}"

    def refresh_data(self) -> None:
        self._fill()


# ─── Accounts (composite) ────────────────────────────────────────────────────

class Accounts(Widget):
    class DataChanged(Message):
        pass

    DEFAULT_CSS = """
    Accounts { width: 100%; height: 1fr; padding: 1 2; }
    .acct-cards { height: auto; min-height: 9; width: 100%; }
    """

    BINDINGS = [
        Binding("n", "add_account",    "New Account", show=True),
        Binding("t", "transfer",       "Transfer",    show=True),
        Binding("x", "delete_account", "Delete Acct", show=True),
    ]

    def __init__(self, *, service: FinanceService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        with Horizontal(classes="acct-cards", id="card-row"):
            for acct in self._svc.accounts:
                bal = self._svc.account_balance(acct.id)
                yield AccountCard(acct, bal, id=f"card-{acct.id}")
        yield TransferHistory(service=self._svc, id="transfer-history")

    def _rebuild_cards(self) -> None:
        card_row = self.query_one("#card-row", Horizontal)
        async def _do() -> None:
            for old in card_row.query(AccountCard):
                await old.remove()
            for acct in self._svc.accounts:
                bal = self._svc.account_balance(acct.id)
                await card_row.mount(AccountCard(acct, bal, id=f"card-{acct.id}"))
        self.app.call_later(_do)

    def action_add_account(self) -> None:
        def _on_result(result: Account | None) -> None:
            if result is None: return
            self._svc.add_account(result.name, result.type, result.base)
            self._rebuild_cards()
            self.post_message(Accounts.DataChanged())
        self.app.push_screen(AddAccountScreen(), _on_result)

    def action_transfer(self) -> None:
        options = self._svc.account_options()
        if len(options) < 2: return
        def _on_result(result: dict | None) -> None:
            if result is None: return
            self._svc.add_transfer(
                date=result["date"], from_acct=result["from"],
                to_acct=result["to"], amount=result["amount"], desc=result["desc"],
            )
            self._rebuild_cards()
            self.query_one("#transfer-history", TransferHistory).refresh_data()
            self.post_message(Accounts.DataChanged())
        self.app.push_screen(TransferScreen(options), _on_result)

    def action_delete_account(self) -> None:
        accounts = self._svc.accounts
        if not accounts: return
        target = None
        for acct in reversed(accounts):
            has_txs = any(tx.account == acct.id for tx in self._svc.transactions)
            if not has_txs:
                target = acct
                break
        if target is None:
            target = accounts[-1]
        def _on_result(confirmed: bool) -> None:
            if not confirmed: return
            removed = self._svc.remove_account(target.id)
            if removed:
                self._rebuild_cards()
                self.post_message(Accounts.DataChanged())
        self.app.push_screen(ConfirmDeleteAccountScreen(target), _on_result)

    def refresh_data(self) -> None:
        self._rebuild_cards()
        self.query_one("#transfer-history", TransferHistory).refresh_data()