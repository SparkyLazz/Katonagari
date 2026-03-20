"""
widgets/finance/accounts.py — Account management.
Cards show live account.amount. Keybinds: n=new t=transfer x=delete
"""
from __future__ import annotations
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.validation import Length, Number
from textual.widget import Widget
from textual.widgets import DataTable, Input, Label, Select, Static
from services.financeService import ACCOUNT_TYPES, Account, FinanceService, fmt

ACCOUNT_TYPE_OPTIONS: list[tuple[str, str]] = [(t, t) for t in ACCOUNT_TYPES]


class AccountCard(Widget):
    DEFAULT_CSS = """
    AccountCard         { border: round $primary; padding: 0 1; width: 1fr; height: 7; min-width: 20; }
    AccountCard .val    { text-style: bold; color: $success; }
    AccountCard .typ    { color: $text-muted; }
    AccountCard.bank    { border: round $accent;  } AccountCard.bank    .val { color: $accent; }
    AccountCard.ewallet { border: round $warning; } AccountCard.ewallet .val { color: $warning; }
    AccountCard.cash    { border: round $success; }
    """
    ICONS = {"Bank": "🏦", "E-Wallet": "📱", "Cash": "💵", "Other": "💰"}

    def __init__(self, acct: Account, **kw) -> None:
        super().__init__(**kw); self._acct = acct

    def on_mount(self) -> None:
        self.border_title = self._acct.name
        cls = self._acct.type.lower().replace("-","").replace(" ","")
        if cls in ("bank","ewallet","cash"): self.add_class(cls)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(f"RP{self._acct.amount:,}", classes="val")
            yield Label(f"{self.ICONS.get(self._acct.type,'💰')} {self._acct.type}", classes="typ")


class AddAccountScreen(ModalScreen[Account | None]):
    DEFAULT_CSS = """
    AddAccountScreen         { align: center middle; background: transparent; }
    AddAccountScreen #dialog { width: 50; height: auto; border: round $primary; background: transparent; padding: 1 2; }
    AddAccountScreen #title  { text-style: bold; color: $warning; margin-bottom: 1; }
    AddAccountScreen .fl     { color: $text-muted; margin-top: 1; height: 1; }
    AddAccountScreen Input   { width: 100%; }
    AddAccountScreen Select  { width: 100%; }
    AddAccountScreen #error  { color: $error; height: 1; margin-top: 1; }
    AddAccountScreen #hint   { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [Binding("escape","cancel"), Binding("ctrl+s","submit")]
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("▸ ADD ACCOUNT", id="title")
            yield Label("Account name", classes="fl")
            yield Input(placeholder="SeaBank", id="inp-name", validators=[Length(minimum=1)])
            yield Label("Type", classes="fl")
            yield Select(ACCOUNT_TYPE_OPTIONS, id="inp-type", prompt="Select type")
            yield Label("Starting amount", classes="fl")
            yield Input(placeholder="0", id="inp-amt", validators=[Number()])
            yield Static("", id="error")
            yield Label("[dim]ctrl+s save · esc cancel[/]", id="hint", markup=True)
    def _save(self) -> None:
        name = self.query_one("#inp-name",Input).value.strip()
        type_select = self.query_one("#inp-type", Select)
        typ = type_select.value
        amt = self.query_one("#inp-amt",Input).value.strip()
        if not name: self.query_one("#error",Static).update("⚠ Name required."); return
        if typ is Select.BLANK: self.query_one("#error",Static).update("⚠ Please select an account type."); return
        try: a = int(amt) if amt else 0
        except ValueError: self.query_one("#error",Static).update("⚠ Integer required."); return
        self.dismiss(Account("", name, str(typ), a))
    def action_cancel(self) -> None: self.dismiss(None)
    def action_submit(self) -> None: self._save()


class TransferScreen(ModalScreen[dict | None]):
    DEFAULT_CSS = """
    TransferScreen         { align: center middle; background: transparent; }
    TransferScreen #dialog { width: 52; height: auto; border: round $accent; background: transparent; padding: 1 2; }
    TransferScreen #title  { text-style: bold; color: $accent; margin-bottom: 1; }
    TransferScreen .fl     { color: $text-muted; margin-top: 1; height: 1; }
    TransferScreen Input   { width: 100%; }
    TransferScreen Select  { width: 100%; }
    TransferScreen #info   { color: $text-muted; }
    TransferScreen #error  { color: $error; height: 1; margin-top: 1; }
    TransferScreen #hint   { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [Binding("escape","cancel"), Binding("ctrl+s","submit")]
    def __init__(self, opts: list[tuple[str,str]], **kw) -> None:
        super().__init__(**kw); self._opts = opts
    def compose(self) -> ComposeResult:
        acct_options = [(n, a) for n, a in self._opts]
        with Vertical(id="dialog"):
            yield Static("▸ TRANSFER", id="title")
            yield Label("Date (YYYY-MM-DD)", classes="fl")
            yield Input(placeholder="2026-03-20", id="inp-date")
            yield Label("From", classes="fl")
            yield Select(acct_options, id="inp-from", prompt="Select source account")
            yield Label("To", classes="fl")
            yield Select(acct_options, id="inp-to", prompt="Select destination account")
            yield Label("Amount", classes="fl")
            yield Input(placeholder="50000", id="inp-amt")
            yield Label("Description (optional)", classes="fl")
            yield Input(placeholder="Top up", id="inp-desc")
            yield Static("", id="error")
            yield Label("[dim]ctrl+s save · esc cancel[/]", id="hint", markup=True)
    def _save(self) -> None:
        from datetime import datetime as dt
        date = self.query_one("#inp-date",Input).value.strip()
        err = self.query_one("#error",Static)
        try: dt.strptime(date,"%Y-%m-%d")
        except ValueError: err.update("⚠ YYYY-MM-DD required."); return
        from_select = self.query_one("#inp-from", Select)
        to_select = self.query_one("#inp-to", Select)
        f = from_select.value
        t = to_select.value
        if f is Select.BLANK: err.update("⚠ Please select source account."); return
        if t is Select.BLANK: err.update("⚠ Please select destination account."); return
        if f == t: err.update("⚠ Source and destination must differ."); return
        try:
            amt = int(self.query_one("#inp-amt",Input).value.strip())
            if amt<=0: raise ValueError
        except ValueError: err.update("⚠ Positive integer required."); return
        self.dismiss({"date":date,"from":str(f),"to":str(t),"amount":amt,
                       "desc":self.query_one("#inp-desc",Input).value.strip()})
    def action_cancel(self) -> None: self.dismiss(None)
    def action_submit(self) -> None: self._save()


class ConfirmDeleteAccountScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmDeleteAccountScreen         { align: center middle; }
    ConfirmDeleteAccountScreen #dialog { width: 46; height: auto; border: round $error; background: $surface; padding: 1 2; }
    ConfirmDeleteAccountScreen #title  { text-style: bold; color: $error; margin-bottom: 1; }
    ConfirmDeleteAccountScreen #desc   { color: $text-muted; margin-bottom: 1; }
    ConfirmDeleteAccountScreen #hint   { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [Binding("escape","cancel"), Binding("y","confirm")]
    def __init__(self, acct: Account, **kw) -> None:
        super().__init__(**kw); self._acct = acct
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("▸ DELETE ACCOUNT", id="title")
            yield Static(f"[dim]Delete[/] [bold]{self._acct.name}[/] [dim]({self._acct.type})?[/]\n"
                         f"[dim]Only if no transactions reference it.[/]", id="desc", markup=True)
            yield Label("[dim]y confirm · esc cancel[/]", id="hint", markup=True)
    def action_cancel(self) -> None: self.dismiss(False)
    def action_confirm(self) -> None: self.dismiss(True)


class TransferHistory(Widget):
    DEFAULT_CSS = """
    TransferHistory           { border: round $accent; width: 100%; height: 1fr; }
    TransferHistory DataTable { height: 1fr; background: transparent; }
    """
    def __init__(self, *, service: FinanceService, **kw) -> None:
        super().__init__(**kw); self._svc = service
    def compose(self) -> ComposeResult:
        self.border_title = "Transfer History"
        yield DataTable(zebra_stripes=True)
    def on_mount(self) -> None:
        t = self.query_one(DataTable)
        t.add_columns("Date","From","To","Amount","Desc"); t.cursor_type = "row"
        self._fill()
    def _fill(self) -> None:
        t = self.query_one(DataTable); t.clear()
        for tr in reversed(self._svc.transfers):
            t.add_row(f"[dim]{tr.display_date}[/]", self._svc.account_name(tr.from_acct),
                       self._svc.account_name(tr.to_acct), f"[cyan]RP{tr.amount:,}[/]",
                       tr.desc or "[dim]—[/]")
        self.border_subtitle = f"{len(self._svc.transfers)} transfers"
    def refresh_data(self) -> None: self._fill()


class Accounts(Widget):
    class DataChanged(Message): pass
    DEFAULT_CSS = """
    Accounts    { width: 100%; height: 1fr; padding: 1 2; }
    .acct-cards { height: auto; min-height: 7; width: 100%; }
    """
    BINDINGS = [
        Binding("n","add_account","New Account",show=True),
        Binding("t","transfer","Transfer",show=True),
        Binding("x","delete_account","Delete Acct",show=True),
    ]
    def __init__(self, *, service: FinanceService, **kw) -> None:
        super().__init__(**kw); self._svc = service
    def compose(self) -> ComposeResult:
        yield Horizontal(id="card-row", classes="acct-cards")
        yield TransferHistory(service=self._svc, id="xfer-hist")
    def on_mount(self) -> None: self._mount_cards()
    def _mount_cards(self) -> None:
        row = self.query_one("#card-row", Horizontal)
        async def _do() -> None:
            for old in list(row.query(AccountCard)): await old.remove()
            for a in self._svc.accounts:
                await row.mount(AccountCard(a, id=f"ac-{a.id}"))
        self.app.call_later(_do)
    def action_add_account(self) -> None:
        def cb(r: Account|None) -> None:
            if not r: return
            self._svc.add_account(r.name, r.type, r.amount)
            self._mount_cards(); self.post_message(self.DataChanged())
        self.app.push_screen(AddAccountScreen(), cb)
    def action_transfer(self) -> None:
        opts = self._svc.account_options()
        if len(opts)<2: return
        def cb(r: dict|None) -> None:
            if not r: return
            self._svc.add_transfer(r["date"],r["from"],r["to"],r["amount"],r["desc"])
            self._mount_cards()
            self.query_one("#xfer-hist",TransferHistory).refresh_data()
            self.post_message(self.DataChanged())
        self.app.push_screen(TransferScreen(opts), cb)
    def action_delete_account(self) -> None:
        accts = self._svc.accounts
        if not accts: return
        target = next((a for a in reversed(accts) if not any(tx.account==a.id for tx in self._svc.transactions)), None)
        if not target: target = accts[-1]
        def cb(ok: bool) -> None:
            if ok and self._svc.remove_account(target.id):
                self._mount_cards(); self.post_message(self.DataChanged())
        self.app.push_screen(ConfirmDeleteAccountScreen(target), cb)
    def refresh_data(self) -> None:
        self._mount_cards()
        self.query_one("#xfer-hist",TransferHistory).refresh_data()