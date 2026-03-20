"""
widgets/finance/overview.py — Dashboard overview. Single consolidated view.
"""
from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static
from services.financeService import FinanceService, fmt
from widgets.finance.log import TransactionLog

class StatCard(Widget):
    DEFAULT_CSS = """
    StatCard         { border: round; padding: 0 1; width: 1fr; height: 1fr; }
    StatCard .val    { text-style: bold; }
    StatCard .diff   { color: $text-muted; }
    StatCard.success { border: round $success; } StatCard.success .val { color: $success; }
    StatCard.error   { border: round $error;   } StatCard.error   .val { color: $error;   }
    StatCard.accent  { border: round $accent;  } StatCard.accent  .val { color: $accent;  }
    """
    def __init__(self, label: str, value: str, diff: str, color: str, **kw) -> None:
        super().__init__(**kw)
        self._label, self._value, self._diff, self._color = label, value, diff, color
    def on_mount(self) -> None:
        self.border_title = self._label; self.add_class(self._color)
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._value, classes="val", id=f"v-{self.id}")
            yield Label(self._diff, classes="diff", id=f"d-{self.id}")
    def set(self, value: str, diff: str) -> None:
        self.query_one(f"#v-{self.id}",Static).update(value)
        self.query_one(f"#d-{self.id}",Label).update(diff)

class SummaryPanel(Widget):
    DEFAULT_CSS = """
    SummaryPanel { border: round $primary; width: 28; height: 1fr; padding: 1 2; }
    .big  { text-style: bold; color: $success; }
    .div  { color: $primary; }
    .rl   { color: $text-muted; width: 12; }
    .rv   { text-style: bold; }
    """
    def __init__(self, *, service: FinanceService, **kw) -> None:
        super().__init__(**kw); self._svc = service
    def compose(self) -> ComposeResult:
        self.border_title = "Summary"
        s = self._svc.current_stats()
        yield Static(f"RP{s.get('net_worth',0):,}", classes="big", id="snw")
        yield Static("─"*20, classes="div")
        for key,label,cls in [("income","Income","rv success"),("expenses","Expenses","rv error"),
                               ("net_savings","Savings","rv accent")]:
            with Horizontal():
                yield Label(label, classes="rl")
                yield Static(f"RP{s.get(key,0):,}", classes=cls, id=f"s-{key[:3]}")
        yield Static("─"*20, classes="div")
        with Horizontal():
            yield Label("Investments", classes="rl")
            yield Static(f"RP{s.get('investments',0):,}", classes="rv", id="s-inv")
        with Horizontal():
            yield Label("Debt", classes="rl")
            yield Static(f"-RP{s.get('debt',0):,}", classes="rv error", id="s-dbt")
        yield Static("─"*20, classes="div")
        sr,sr_ch = s.get("save_rate",0.0), s.get("save_rate_change",0.0)
        with Horizontal():
            yield Label("Save rate", classes="rl")
            yield Static(f"{sr:.1f}%", classes="rv accent", id="s-sr")
        with Horizontal():
            yield Label("vs last mo.", classes="rl")
            yield Static(f"{'+'if sr_ch>=0 else''}{sr_ch:.1f}%",
                         classes=f"rv {'success'if sr_ch>=0 else'error'}", id="s-src")
    def refresh_data(self) -> None:
        s = self._svc.current_stats()
        self.query_one("#snw",Static).update(f"RP{s.get('net_worth',0):,}")
        self.query_one("#s-inc",Static).update(f"RP{s.get('income',0):,}")
        self.query_one("#s-exp",Static).update(f"RP{s.get('expenses',0):,}")
        self.query_one("#s-net",Static).update(f"RP{s.get('net_savings',0):,}")
        self.query_one("#s-inv",Static).update(f"RP{s.get('investments',0):,}")
        self.query_one("#s-dbt",Static).update(f"-RP{s.get('debt',0):,}")
        sr,sr_ch = s.get("save_rate",0.0), s.get("save_rate_change",0.0)
        self.query_one("#s-sr",Static).update(f"{sr:.1f}%")
        src = self.query_one("#s-src",Static)
        src.update(f"{'+'if sr_ch>=0 else''}{sr_ch:.1f}%")
        src.remove_class("success","error"); src.add_class("success"if sr_ch>=0 else"error")

class TransactionTable(Widget):
    DEFAULT_CSS = """
    TransactionTable           { width: 1fr; height: 1fr; border: round $accent; }
    TransactionTable DataTable { height: 1fr; background: transparent; }
    """
    def __init__(self, *, service: FinanceService, **kw) -> None:
        super().__init__(**kw); self._svc = service
    def compose(self) -> ComposeResult:
        self.border_title = "Recent Transactions"
        t = DataTable(zebra_stripes=True)
        t.add_columns("Date","Description","Account","Category","Amount"); yield t
    def on_mount(self) -> None: self._fill()
    def _fill(self) -> None:
        t = self.query_one(DataTable); t.clear()
        for tx in self._svc.transactions[-10:]:
            t.add_row(f"[dim]{tx.display_date}[/]", tx.desc,
                       f"[dim]{self._svc.account_name(tx.account)}[/]",
                       f"[dim]{tx.cat}[/]", fmt(tx.amount))
        s = self._svc.current_stats()
        self.border_subtitle = s.get("current_month","")
    def refresh_data(self) -> None: self._fill()

class Overview(Widget):
    DEFAULT_CSS = """
    Overview    { width: 100%; height: 1fr; padding: 1 2; }
    .stat-row   { height: 7; }
    .bottom-row { width: 100%; height: 1fr; }
    """
    def __init__(self, *, service: FinanceService, **kw) -> None:
        super().__init__(**kw); self._svc = service
    def _v(self) -> dict:
        s = self._svc.current_stats()
        return dict(nw=s.get("net_worth",0),inc=s.get("income",0),exp=s.get("expenses",0),
                    sav=s.get("net_savings",0),sr=s.get("save_rate",0.0),
                    nw_pct=s.get("nw_change_pct",0.0),inc_ch=s.get("income_change",0),
                    exp_pct=s.get("expenses_pct",0.0))
    def compose(self) -> ComposeResult:
        v = self._v()
        with Horizontal(classes="stat-row"):
            yield StatCard("Total Balance",f"RP{v['nw']:,}",
                           f"{'+'if v['nw_pct']>=0 else''}{v['nw_pct']:.1f}% this month","success",id="cb")
            yield StatCard("Monthly Income",f"RP{v['inc']:,}",
                           f"{'+'if v['inc_ch']>=0 else''}RP{abs(v['inc_ch']):,} vs last","success",id="ci")
            yield StatCard("Expenses",f"RP{v['exp']:,}",
                           f"{'+'if v['exp_pct']>=0 else''}{v['exp_pct']:.1f}% vs last","error",id="ce")
            yield StatCard("Net Savings",f"RP{v['sav']:,}",
                           f"{v['sr']:.1f}% save rate","accent",id="cs")
        with Horizontal(classes="bottom-row"):
            yield SummaryPanel(service=self._svc,id="sp")
            yield TransactionTable(service=self._svc,id="tt")
    def refresh_data(self) -> None:
        v = self._v()
        self.query_one("#cb",StatCard).set(f"RP{v['nw']:,}",f"{'+'if v['nw_pct']>=0 else''}{v['nw_pct']:.1f}% this month")
        self.query_one("#ci",StatCard).set(f"RP{v['inc']:,}",f"{'+'if v['inc_ch']>=0 else''}RP{abs(v['inc_ch']):,} vs last")
        self.query_one("#ce",StatCard).set(f"RP{v['exp']:,}",f"{'+'if v['exp_pct']>=0 else''}{v['exp_pct']:.1f}% vs last")
        self.query_one("#cs",StatCard).set(f"RP{v['sav']:,}",f"{v['sr']:.1f}% save rate")
        self.query_one("#sp",SummaryPanel).refresh_data()
        self.query_one("#tt",TransactionTable).refresh_data()
    def on_transaction_log_data_changed(self, _: TransactionLog.DataChanged) -> None:
        self.refresh_data()