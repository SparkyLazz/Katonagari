"""
financeService.py — single source of truth for all finance data.
Backed by databases/finance.json.

Data model:
  - Account.amount = current live balance (updated on every tx add/remove/transfer)
  - Transactions are a log; they don't need to be replayed to know the balance
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev

DATA_FILE: Path = Path(__file__).resolve().parent.parent / "databases" / "finance.json"

CATEGORIES: list[str] = [
    "Food", "Health", "Housing", "Income",
    "Other", "Subscription", "Transport", "Utility",
]
CATEGORY_OPTIONS: list[tuple[str, str]] = [(c, c) for c in CATEGORIES]
EXPENSE_CATEGORIES: list[str] = [c for c in CATEGORIES if c != "Income"]
ACCOUNT_TYPES: list[str] = ["Bank", "E-Wallet", "Cash", "Other"]


# ─── Models ──────────────────────────────────────────────────────────────────

@dataclass
class Account:
    id:     str
    name:   str
    type:   str
    amount: int  # live balance — always up to date

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "type": self.type, "amount": self.amount}


@dataclass
class Transaction:
    date:    str
    desc:    str
    cat:     str
    amount:  int
    account: str

    @property
    def display_date(self) -> str:
        return datetime.strptime(self.date, "%Y-%m-%d").strftime("%b %d")

    @property
    def month_key(self) -> str:
        return datetime.strptime(self.date, "%Y-%m-%d").strftime("%b %Y")

    def to_dict(self) -> dict:
        return {"date": self.date, "desc": self.desc, "cat": self.cat,
                "amount": self.amount, "account": self.account}


@dataclass
class Transfer:
    date: str; from_acct: str; to_acct: str; amount: int; desc: str = ""

    @property
    def display_date(self) -> str:
        return datetime.strptime(self.date, "%Y-%m-%d").strftime("%b %d")

    def to_dict(self) -> dict:
        return {"date": self.date, "from": self.from_acct, "to": self.to_acct,
                "amount": self.amount, "desc": self.desc}


@dataclass
class MonthlySummary:
    month: str; income: int; expenses: int; net: int


@dataclass(frozen=True)
class PeriodData:
    months: list[str]; income: list[int]
    category_rows: list[tuple[str, int, int]]; avg_expense: float


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "account"

def _unique_slug(name: str, existing: set[str]) -> str:
    base = slug = _slugify(name)
    n = 2
    while slug in existing: slug = f"{base}-{n}"; n += 1
    return slug


# ─── Service ─────────────────────────────────────────────────────────────────

class FinanceService:

    def __init__(self, data_file: Path = DATA_FILE) -> None:
        self._file = data_file
        self._raw: dict = self._load()
        self._accounts:  list[Account]     = []
        self._txs:       list[Transaction] = []
        self._transfers: list[Transfer]    = []
        self._rebuild()

    # ── IO ────────────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._file.exists():
            with open(self._file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"meta": {"accounts": [], "investments": 0, "debt": 0},
                "transactions": [], "transfers": []}

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file, "w", encoding="utf-8") as f:
            json.dump(self._raw, f, indent=2)

    def _rebuild(self) -> None:
        """Parse raw JSON into typed objects. No balance computation needed."""
        meta = self._raw.get("meta", {})
        self._accounts = [
            Account(a["id"], a["name"], a.get("type", "Other"), a.get("amount", 0))
            for a in meta.get("accounts", [])
        ]
        self._txs = sorted(
            [Transaction(t["date"], t["desc"], t["cat"], t["amount"], t.get("account", "cash"))
             for t in self._raw.get("transactions", [])],
            key=lambda t: t.date,
        )
        self._transfers = sorted(
            [Transfer(t["date"], t["from"], t["to"], t["amount"], t.get("desc", ""))
             for t in self._raw.get("transfers", [])],
            key=lambda t: t.date,
        )

    def _update_account_amount(self, acct_id: str, delta: int) -> None:
        """Apply delta to account amount in raw JSON and rebuild."""
        for a in self._raw["meta"]["accounts"]:
            if a["id"] == acct_id:
                a["amount"] = a.get("amount", 0) + delta
                break

    # ── Account CRUD ──────────────────────────────────────────────────────────

    @property
    def accounts(self) -> list[Account]:
        return list(self._accounts)

    def account_by_id(self, aid: str) -> Account | None:
        return next((a for a in self._accounts if a.id == aid), None)

    def account_name(self, aid: str) -> str:
        a = self.account_by_id(aid)
        return a.name if a else aid

    def account_options(self) -> list[tuple[str, str]]:
        return [(a.name, a.id) for a in self._accounts]

    def add_account(self, name: str, acct_type: str = "Other", amount: int = 0) -> Account:
        slug = _unique_slug(name, {a.id for a in self._accounts})
        acct = Account(slug, name, acct_type, amount)
        self._raw["meta"]["accounts"].append(acct.to_dict())
        self._rebuild(); self._save()
        return acct

    def remove_account(self, aid: str) -> Account | None:
        acct = self.account_by_id(aid)
        if not acct or any(tx.account == aid for tx in self._txs):
            return None
        self._raw["meta"]["accounts"] = [a for a in self._raw["meta"]["accounts"] if a["id"] != aid]
        self._rebuild(); self._save()
        return acct

    # ── Transactions ──────────────────────────────────────────────────────────

    @property
    def transactions(self) -> list[Transaction]:
        return list(self._txs)

    def transactions_for(self, account: str | None = None) -> list[Transaction]:
        if account is None: return list(self._txs)
        return [tx for tx in self._txs if tx.account == account]

    def add(self, tx: Transaction) -> None:
        self._raw["transactions"].append(tx.to_dict())
        self._update_account_amount(tx.account, tx.amount)
        self._rebuild(); self._save()

    def remove(self, index: int, account: str | None = None) -> Transaction:
        txs = self.transactions_for(account)
        removed = txs[index]
        # Find and remove from raw list
        for i, raw in enumerate(self._raw["transactions"]):
            if (raw["date"] == removed.date and raw["desc"] == removed.desc
                    and raw["amount"] == removed.amount
                    and raw.get("account", "cash") == removed.account):
                self._raw["transactions"].pop(i)
                break
        # Reverse the amount on the account
        self._update_account_amount(removed.account, -removed.amount)
        self._rebuild(); self._save()
        return removed

    # ── Transfers ─────────────────────────────────────────────────────────────

    @property
    def transfers(self) -> list[Transfer]:
        return list(self._transfers)

    def add_transfer(self, date: str, from_acct: str, to_acct: str,
                     amount: int, desc: str = "") -> Transfer:
        t = Transfer(date, from_acct, to_acct, amount, desc)
        self._raw["transfers"].append(t.to_dict())
        # Move money between accounts
        self._update_account_amount(from_acct, -amount)
        self._update_account_amount(to_acct, amount)
        self._rebuild(); self._save()
        return t

    # ── Balances (read directly from account.amount) ──────────────────────────

    @property
    def liquid(self) -> int:
        return sum(a.amount for a in self._accounts)

    @property
    def investments(self) -> int:
        return self._raw["meta"].get("investments", 0)

    @property
    def debt(self) -> int:
        return self._raw["meta"].get("debt", 0)

    @property
    def net_worth(self) -> int:
        return self.liquid + self.investments - self.debt

    # ── Aggregates ────────────────────────────────────────────────────────────

    def monthly_summaries(self, account: str | None = None) -> list[MonthlySummary]:
        txs = self.transactions_for(account)
        groups: dict[str, dict] = {}
        for tx in txs:
            mk = tx.month_key
            if mk not in groups:
                groups[mk] = {"income": 0, "expenses": 0, "sort": tx.date[:7]}
            if tx.amount > 0:
                groups[mk]["income"] += tx.amount
            else:
                groups[mk]["expenses"] += abs(tx.amount)
        return [
            MonthlySummary(month, d["income"], d["expenses"], d["income"] - d["expenses"])
            for month, d in sorted(groups.items(), key=lambda x: x[1]["sort"])
        ]

    def category_monthly(self, account: str | None = None) -> dict[str, list[int]]:
        summaries = self.monthly_summaries(account)
        month_order = [s.month for s in summaries]
        txs = self.transactions_for(account)
        cat_data: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for tx in txs:
            if tx.amount < 0:
                cat_data[tx.cat][tx.month_key] += abs(tx.amount)
        return {cat: [cat_data[cat].get(m, 0) for m in month_order] for cat in EXPENSE_CATEGORIES}

    def build_period(self, n: int, account: str | None = None) -> PeriodData:
        summaries = self.monthly_summaries(account)
        cat_hist = self.category_monthly(account)
        total = len(summaries)
        recent = summaries[-n:]
        cat_rows = []
        for cat, hist in cat_hist.items():
            curr = hist[-n:]
            prev = hist[max(0, total-2*n):total-n]
            cat_rows.append((cat, round(mean(curr)) if curr else 0,
                             round(mean(prev)) if prev else (curr[0] if curr else 0)))
        return PeriodData(
            months=[s.month.split()[0] for s in recent],
            income=[s.income for s in recent],
            category_rows=cat_rows,
            avg_expense=mean(s.expenses for s in recent) if recent else 0.0,
        )

    def current_stats(self, account: str | None = None) -> dict:
        summaries = self.monthly_summaries(account)
        if not summaries: return {}
        curr = summaries[-1]
        prev = summaries[-2] if len(summaries) > 1 else None
        if account:
            acct = self.account_by_id(account)
            nw = acct.amount if acct else 0
        else:
            nw = self.net_worth
        save_rate = curr.net / curr.income * 100 if curr.income else 0.0
        prev_sr   = prev.net / prev.income * 100 if prev and prev.income else 0.0
        inc_ch    = curr.income - (prev.income if prev else 0)
        exp_pct   = ((curr.expenses - prev.expenses) / prev.expenses * 100
                     if prev and prev.expenses else 0.0)
        return {
            "net_worth": nw, "income": curr.income, "expenses": curr.expenses,
            "net_savings": curr.net, "save_rate": save_rate,
            "save_rate_change": save_rate - prev_sr, "income_change": inc_ch,
            "expenses_pct": exp_pct, "investments": self.investments,
            "debt": self.debt, "liquid": acct.amount if account and (acct := self.account_by_id(account)) else self.liquid,
            "current_month": curr.month,
        }


# ─── Formatting ──────────────────────────────────────────────────────────────

def fmt(n: int, sign: bool = True) -> str:
    prefix = ("+" if n > 0 else "") if sign else ""
    return f"[{'green' if n >= 0 else 'red'}]{prefix}RP{abs(n):,}[/]"

def fmt_change(n: int) -> str:
    if n == 0: return "[dim]─[/]"
    return f"[{'green' if n>0 else 'red'}]{'+'if n>0 else'-'}RP{abs(n):,}[/]"

def verdict(months: float) -> tuple[str, str]:
    if months < 3:  return "⚠ CRITICAL", "red"
    if months < 6:  return "▲ FAIR", "yellow"
    if months < 12: return "✓ GOOD", "cyan"
    return "✓ EXCELLENT", "green"

def volatility(data: list[int]) -> tuple[str, str]:
    if len(data) < 2: return "N/A", "dim"
    cv = stdev(data) / mean(data)
    if cv < 0.06: return "LOW", "green"
    if cv < 0.15: return "MEDIUM", "yellow"
    return "HIGH", "red"

def color_delta(d: int) -> str:
    return "red" if d > 0 else "green" if d < 0 else "dim"

def trend_symbol(d: int) -> str:
    if d > 0: return "[red]▲[/]"
    if d < 0: return "[green]▼[/]"
    return "[dim]─[/]"