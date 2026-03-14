from __future__ import annotations
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Button, DataTable, Label, Static, TabbedContent, TabPane,
)

from databases.financeData import (
    add_transaction, delete_transaction, update_transaction,
    load_data, ACCOUNT_ICON, CATEGORY_COLOR, CATEGORY_ICON,
    fmt_rp,
)
from .constants import (
    _rc, _ACC_RICH, _TYPE_PILL, _FILTER_KEYS, _FILTER_NAMES
)
from .modals import TxDetailModal, ConfirmModal, TxFormModal
from .sidebar import FinanceSidebar
from .analysis import AnalysisPanel

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

    #fin-body {
        layout: horizontal;
        height: 1fr;
        width: 100%;
        padding: 1 1 0 1;
    }

    #fin-tabs {
        width: 1fr;
        height: 100%;
    }
    #fin-tabs > TabbedContent > TabPane {
        padding: 0;
        height: 1fr;
    }

    #tx-pane {
        layout: vertical;
        height: 1fr;
        width: 100%;
        padding: 1 1 0 1;
    }

    #tx-box {
        layout: vertical;
        height: 1fr;
        width: 100%;
        background: $surface;
        padding: 0 1;
        overflow: hidden hidden;
        border: round $primary;
        border-title-align: left;
        border-title-color: $primary;
        border-title-style: bold;
        margin: 0 1 1 1;
    }

    #filter-bar {
        height: 3;
        layout: horizontal;
        margin-bottom: 1;
    }

    #info-bar {
        height: 1;
        layout: horizontal;
        margin-bottom: 1;
    }
    #lbl-title { width: 1fr; color: $primary; text-style: bold; }
    #lbl-count { color: $text-muted; text-style: italic; }

    #tx-table {
        height: 1fr;
        width: 100%;
        background: transparent;
    }
    #tx-table .datatable--header {
        padding: 10 10;
    }
    #no-txs {
        height: 1fr;
        width: 100%;
        color: $text-muted;
        text-style: italic;
        content-align: center middle;
    }

    #an-scroll {
        height: 1fr;
        width: 100%;
    }

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

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
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
                                        variant="primary" if key == "all" else "default",
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
        self.query_one("#tx-box").border_title = "💰 TRANSACTIONS"
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
                    self.query_one(f"#flt-{k}", Button).variant = (
                        "primary" if k == key else "default"
                    )
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

            if   d == today: date_c = "[yellow bold]Today[/]"
            elif ago == 1:   date_c = "[dim white]Yesterday[/]"
            elif ago <= 7:   date_c = f"[dim white]{d.strftime('%a %d')}[/]"
            else:            date_c = f"[dim]{d.strftime('%b %d')}[/]"

            type_c = _TYPE_PILL.get(kind, kind)

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
