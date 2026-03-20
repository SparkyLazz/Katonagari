"""
financeService.py
─────────────────
Single source of truth for all finance data and computations.
Backed by  databases/finance.json  —  all widgets import from here.

v2 — Multi-account support
    • Account CRUD (dynamic add/remove/edit)
    • Per-account running balances
    • Inter-account transfers
    • Optional account filter on all queries
    • Auto-migration from v1 schema (single liquid_base)
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev

# ─── Paths ───────────────────────────────────────────────────────────────────

DATA_FILE: Path = Path(__file__).resolve().parent.parent / "databases" / "finance.json"

# ─── Constants ───────────────────────────────────────────────────────────────

CATEGORIES: list[str] = [
    "Food", "Health", "Housing", "Income",
    "Other", "Subscription", "Transport", "Utility",
]

CATEGORY_OPTIONS: list[tuple[str, str]] = [(c, c) for c in CATEGORIES]

EXPENSE_CATEGORIES: list[str] = [c for c in CATEGORIES if c != "Income"]

ACCOUNT_TYPES: list[str] = ["Bank", "E-Wallet", "Cash", "Other"]
ACCOUNT_TYPE_OPTIONS: list[tuple[str, str]] = [(t, t) for t in ACCOUNT_TYPES]

# ─── Models ──────────────────────────────────────────────────────────────────

@dataclass
class Account:
    """One money account (bank, e-wallet, cash, etc.)."""

    id:   str   # slug, e.g. "seabank"
    name: str   # display name, e.g. "SeaBank"
    type: str   # "Bank" | "E-Wallet" | "Cash" | "Other"
    base: int   # starting balance before any transactions

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "type": self.type, "base": self.base}


@dataclass
class Transaction:
    """One ledger entry.  `date` is stored as ISO-8601 (YYYY-MM-DD)."""

    date:    str   # "2024-01-15"
    desc:    str
    cat:     str
    amount:  int   # positive = income, negative = expense
    account: str   # account id, e.g. "seabank"
    balance: int = 0

    # ── Display helpers ───────────────────────────────────────────────────────

    @property
    def display_date(self) -> str:
        """'Jan 15'"""
        return datetime.strptime(self.date, "%Y-%m-%d").strftime("%b %d")

    @property
    def month_key(self) -> str:
        """'Jan 2024'  — used for grouping."""
        return datetime.strptime(self.date, "%Y-%m-%d").strftime("%b %Y")

    @property
    def sort_key(self) -> str:
        return self.date

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "date":    self.date,
            "desc":    self.desc,
            "cat":     self.cat,
            "amount":  self.amount,
            "account": self.account,
        }


@dataclass
class Transfer:
    """Inter-account transfer (does not affect income/expense totals)."""

    date:       str   # "2024-01-15"
    from_acct:  str   # account id
    to_acct:    str   # account id
    amount:     int   # always positive
    desc:       str = ""

    @property
    def display_date(self) -> str:
        return datetime.strptime(self.date, "%Y-%m-%d").strftime("%b %d")

    @property
    def sort_key(self) -> str:
        return self.date

    def to_dict(self) -> dict:
        return {
            "date":   self.date,
            "from":   self.from_acct,
            "to":     self.to_acct,
            "amount": self.amount,
            "desc":   self.desc,
        }


@dataclass
class MonthlySummary:
    month:     str   # "Jan 2024"
    income:    int
    expenses:  int
    net:       int
    net_worth: int
    change:    int   # net-worth change vs previous month


@dataclass(frozen=True)
class PeriodData:
    months:        list[str]                    # short labels, e.g. ["Nov", "Dec", "Jan"]
    income:        list[int]
    category_rows: list[tuple[str, int, int]]   # (cat, this_avg, prev_avg)
    avg_expense:   float


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Generate a safe id from an account name: 'Sea Bank' → 'sea-bank'."""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "account"


def _unique_slug(name: str, existing_ids: set[str]) -> str:
    """Generate a unique slug, appending -2, -3, etc. if needed."""
    base = _slugify(name)
    slug = base
    counter = 2
    while slug in existing_ids:
        slug = f"{base}-{counter}"
        counter += 1
    return slug


# ─── Service ─────────────────────────────────────────────────────────────────

class FinanceService:
    """
    Loads  databases/finance.json, exposes typed transaction list,
    persists mutations, and computes all derived values needed by widgets.
    """

    def __init__(self, data_file: Path = DATA_FILE) -> None:
        self._file = data_file
        self._raw:       dict              = self._load()
        self._accounts:  list[Account]     = []
        self._txs:       list[Transaction] = []
        self._transfers: list[Transfer]    = []
        self._migrate_v1()
        self._rebuild()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._file.exists():
            with open(self._file, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return {
            "meta": {"accounts": [], "investments": 0, "debt": 0},
            "transactions": [],
            "transfers": [],
        }

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file, "w", encoding="utf-8") as fh:
            json.dump(self._raw, fh, indent=2)

    def _migrate_v1(self) -> None:
        """Auto-migrate from v1 schema (single liquid_base, no accounts)."""
        meta = self._raw.get("meta", {})

        # Already v2
        if "accounts" in meta:
            return

        # Migrate: create a default "Cash" account
        liquid_base = meta.get("liquid_base", 0)
        meta["accounts"] = [
            {"id": "cash", "name": "Cash", "type": "Cash", "base": liquid_base}
        ]
        meta.pop("liquid_base", None)
        self._raw["meta"] = meta

        # Tag all existing transactions with account = "cash"
        for tx in self._raw.get("transactions", []):
            if "account" not in tx:
                tx["account"] = "cash"

        # Ensure transfers list exists
        if "transfers" not in self._raw:
            self._raw["transfers"] = []

        self._save()

    def _rebuild(self) -> None:
        """Re-parse accounts, sort transactions, recompute running balances."""
        meta = self._raw.get("meta", {})

        # Build accounts
        self._accounts = [
            Account(
                id   = a["id"],
                name = a["name"],
                type = a.get("type", "Other"),
                base = a.get("base", 0),
            )
            for a in meta.get("accounts", [])
        ]

        # Build per-account running balances
        acct_running: dict[str, int] = {
            a.id: a.base for a in self._accounts
        }

        sorted_raw = sorted(self._raw.get("transactions", []), key=lambda r: r["date"])
        self._txs = []
        for raw in sorted_raw:
            acct_id = raw.get("account", "cash")
            acct_running.setdefault(acct_id, 0)
            acct_running[acct_id] += raw["amount"]
            self._txs.append(Transaction(
                date    = raw["date"],
                desc    = raw["desc"],
                cat     = raw["cat"],
                amount  = raw["amount"],
                account = acct_id,
                balance = acct_running[acct_id],
            ))

        # Apply transfers to running balances (for account_balance accuracy)
        # Transfers are already baked into the per-account base concept;
        # we track them separately for display.
        self._transfers = sorted(
            [
                Transfer(
                    date      = t["date"],
                    from_acct = t["from"],
                    to_acct   = t["to"],
                    amount    = t["amount"],
                    desc      = t.get("desc", ""),
                )
                for t in self._raw.get("transfers", [])
            ],
            key=lambda t: t.sort_key,
        )

    # ── Account CRUD ──────────────────────────────────────────────────────────

    @property
    def accounts(self) -> list[Account]:
        return list(self._accounts)

    def account_by_id(self, acct_id: str) -> Account | None:
        for a in self._accounts:
            if a.id == acct_id:
                return a
        return None

    def account_name(self, acct_id: str) -> str:
        """Get display name for an account id; returns id if not found."""
        a = self.account_by_id(acct_id)
        return a.name if a else acct_id

    def account_options(self) -> list[tuple[str, str]]:
        """For use in Select widgets: [(display_name, id), ...]"""
        return [(a.name, a.id) for a in self._accounts]

    def add_account(self, name: str, acct_type: str = "Other", base: int = 0) -> Account:
        existing_ids = {a.id for a in self._accounts}
        slug = _unique_slug(name, existing_ids)
        acct = Account(id=slug, name=name, type=acct_type, base=base)
        self._raw["meta"]["accounts"].append(acct.to_dict())
        self._rebuild()
        self._save()
        return acct

    def remove_account(self, acct_id: str) -> Account | None:
        """Remove account. Fails silently if transactions still reference it."""
        acct = self.account_by_id(acct_id)
        if acct is None:
            return None
        # Check for remaining transactions
        has_txs = any(tx.account == acct_id for tx in self._txs)
        if has_txs:
            return None
        self._raw["meta"]["accounts"] = [
            a for a in self._raw["meta"]["accounts"] if a["id"] != acct_id
        ]
        self._rebuild()
        self._save()
        return acct

    def edit_account(self, acct_id: str, name: str | None = None,
                     acct_type: str | None = None, base: int | None = None) -> Account | None:
        for raw_acct in self._raw["meta"]["accounts"]:
            if raw_acct["id"] == acct_id:
                if name is not None:
                    raw_acct["name"] = name
                if acct_type is not None:
                    raw_acct["type"] = acct_type
                if base is not None:
                    raw_acct["base"] = base
                self._rebuild()
                self._save()
                return self.account_by_id(acct_id)
        return None

    # ── Transfers ─────────────────────────────────────────────────────────────

    @property
    def transfers(self) -> list[Transfer]:
        return list(self._transfers)

    def add_transfer(self, date: str, from_acct: str, to_acct: str,
                     amount: int, desc: str = "") -> Transfer:
        """Record a transfer. Creates two offsetting transactions internally."""
        transfer = Transfer(date=date, from_acct=from_acct, to_acct=to_acct,
                            amount=amount, desc=desc)
        self._raw["transfers"].append(transfer.to_dict())

        # Create offsetting transactions so balances stay correct
        label = desc or f"Transfer → {self.account_name(to_acct)}"
        label_in = desc or f"Transfer ← {self.account_name(from_acct)}"

        self._raw["transactions"].append({
            "date": date, "desc": label,
            "cat": "Transfer", "amount": -amount, "account": from_acct,
        })
        self._raw["transactions"].append({
            "date": date, "desc": label_in,
            "cat": "Transfer", "amount": amount, "account": to_acct,
        })
        self._rebuild()
        self._save()
        return transfer

    # ── Transactions ──────────────────────────────────────────────────────────

    @property
    def transactions(self) -> list[Transaction]:
        return list(self._txs)

    def transactions_for(self, account: str | None = None) -> list[Transaction]:
        """Return transactions, optionally filtered by account id."""
        if account is None:
            return list(self._txs)
        return [tx for tx in self._txs if tx.account == account]

    def add(self, tx: Transaction) -> None:
        self._raw["transactions"].append(tx.to_dict())
        self._rebuild()
        self._save()

    def remove(self, index: int, account: str | None = None) -> Transaction:
        """Remove by sorted-list index; matches on date + desc + amount + account."""
        txs = self.transactions_for(account)
        removed = txs[index]
        for i, raw in enumerate(self._raw["transactions"]):
            if (raw["date"]    == removed.date   and
                raw["desc"]    == removed.desc   and
                raw["amount"]  == removed.amount and
                raw.get("account", "cash") == removed.account):
                self._raw["transactions"].pop(i)
                break
        self._rebuild()
        self._save()
        return removed

    # ── Meta properties ───────────────────────────────────────────────────────

    def account_balance(self, acct_id: str) -> int:
        """Current balance for a single account."""
        acct = self.account_by_id(acct_id)
        base = acct.base if acct else 0
        total = base
        for tx in self._txs:
            if tx.account == acct_id:
                total = tx.balance  # last running balance for this account
        # If no transactions, return base
        has_txs = any(tx.account == acct_id for tx in self._txs)
        if not has_txs:
            return base
        return total

    @property
    def liquid(self) -> int:
        """Current liquid cash (sum of all account balances)."""
        return sum(self.account_balance(a.id) for a in self._accounts)

    @property
    def investments(self) -> int:
        return self._raw["meta"].get("investments", 0)

    @property
    def debt(self) -> int:
        return self._raw["meta"].get("debt", 0)

    @property
    def net_worth(self) -> int:
        return self.liquid + self.investments - self.debt

    # ── Monthly aggregates ────────────────────────────────────────────────────

    def monthly_summaries(self, account: str | None = None) -> list[MonthlySummary]:
        """Ordered list of per-month summaries (oldest → newest)."""
        txs = self.transactions_for(account)
        groups: dict[str, dict] = {}
        for tx in txs:
            if tx.cat == "Transfer":
                continue  # skip transfers from income/expense totals
            mk = tx.month_key
            if mk not in groups:
                groups[mk] = {"income": 0, "expenses": 0, "sort_key": tx.date[:7]}
            if tx.amount > 0:
                groups[mk]["income"]   += tx.amount
            else:
                groups[mk]["expenses"] += abs(tx.amount)

        # Base net worth for running calc
        if account:
            acct = self.account_by_id(account)
            base_nw = (acct.base if acct else 0)
        else:
            base_nw = (
                sum(a.base for a in self._accounts)
                + self.investments
                - self.debt
            )

        result: list[MonthlySummary] = []
        running_nw = base_nw
        prev_nw    = base_nw

        for month, data in sorted(groups.items(), key=lambda x: x[1]["sort_key"]):
            net        = data["income"] - data["expenses"]
            running_nw += net
            result.append(MonthlySummary(
                month     = month,
                income    = data["income"],
                expenses  = data["expenses"],
                net       = net,
                net_worth = running_nw,
                change    = running_nw - prev_nw,
            ))
            prev_nw = running_nw

        return result

    def category_monthly(self, account: str | None = None) -> dict[str, list[int]]:
        """
        Returns {category: [spend_per_month, ...]} aligned to monthly_summaries().
        Only expense categories; amounts are positive integers.
        """
        summaries   = self.monthly_summaries(account)
        month_order = [s.month for s in summaries]
        txs         = self.transactions_for(account)

        cat_data: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for tx in txs:
            if tx.amount < 0 and tx.cat != "Transfer":
                cat_data[tx.cat][tx.month_key] += abs(tx.amount)

        return {
            cat: [cat_data[cat].get(m, 0) for m in month_order]
            for cat in EXPENSE_CATEGORIES
        }

    # ── Period analysis ───────────────────────────────────────────────────────

    def build_period(self, n: int, account: str | None = None) -> PeriodData:
        """Build a PeriodData for the last *n* months."""
        summaries = self.monthly_summaries(account)
        cat_hist  = self.category_monthly(account)
        n_total   = len(summaries)

        recent  = summaries[-n:]
        months  = [s.month.split()[0] for s in recent]
        income  = [s.income for s in recent]

        cat_rows: list[tuple[str, int, int]] = []
        for cat, history in cat_hist.items():
            curr = history[-n:]
            prev = history[max(0, n_total - 2 * n): n_total - n]
            cat_rows.append((
                cat,
                round(mean(curr)) if curr else 0,
                round(mean(prev)) if prev else (curr[0] if curr else 0),
            ))

        avg_exp = mean(s.expenses for s in recent) if recent else 0.0

        return PeriodData(
            months        = months,
            income        = income,
            category_rows = cat_rows,
            avg_expense   = avg_exp,
        )

    # ── Overview stats ────────────────────────────────────────────────────────

    def current_stats(self, account: str | None = None) -> dict:
        """
        Computed stats for the most-recent month vs the one before it.
        Used by the Overview screen.
        """
        summaries = self.monthly_summaries(account)
        if not summaries:
            return {}

        curr = summaries[-1]
        prev = summaries[-2] if len(summaries) > 1 else None

        if account:
            nw = self.account_balance(account)
        else:
            nw = self.net_worth

        save_rate      = curr.net / curr.income * 100      if curr.income            else 0.0
        prev_save_rate = prev.net / prev.income * 100      if prev and prev.income   else 0.0
        inc_change     = curr.income   - (prev.income      if prev else 0)
        exp_pct        = ((curr.expenses - prev.expenses) / prev.expenses * 100
                         if prev and prev.expenses else 0.0)
        nw_pct         = (curr.change / prev.net_worth * 100
                         if prev and prev.net_worth else 0.0)

        return {
            "net_worth":        nw,
            "income":           curr.income,
            "expenses":         curr.expenses,
            "net_savings":      curr.net,
            "save_rate":        save_rate,
            "save_rate_change": save_rate - prev_save_rate,
            "income_change":    inc_change,
            "expenses_pct":     exp_pct,
            "nw_change_pct":    nw_pct,
            "investments":      self.investments,
            "debt":             self.debt,
            "liquid":           self.liquid if not account else self.account_balance(account),
            "current_month":    curr.month,
        }


# ─── Formatting helpers (shared across all widgets) ───────────────────────────

def fmt_amount(n: int, sign: bool = True) -> str:
    """Rich-markup coloured amount: '[green]+RP1,500[/]'"""
    prefix = ("+" if n > 0 else "") if sign else ""
    color  = "green" if n >= 0 else "red"
    return f"[{color}]{prefix}RP{abs(n):,}[/]"


def fmt_change(n: int) -> str:
    """Rich-markup net-worth change: '[green]+RP700[/]' or '[dim]─[/]'"""
    if n == 0: return "[dim]─[/]"
    if n > 0:  return f"[green]+RP{n:,}[/]"
    return f"[red]-RP{abs(n):,}[/]"


def fmt_pct(pct: float, invert: bool = False) -> str:
    """
    Signed percentage string with colour.
    `invert=True` flips the colour logic (e.g. for expenses: up = bad).
    """
    sign  = "+" if pct >= 0 else ""
    if invert:
        color = "red" if pct > 0 else "green" if pct < 0 else "dim"
    else:
        color = "green" if pct > 0 else "red" if pct < 0 else "dim"
    return f"[{color}]{sign}{pct:.1f}%[/]"


def verdict(months: float) -> tuple[str, str]:
    """Emergency-fund runway verdict: (label, colour)"""
    if months < 3:  return "⚠ CRITICAL — build emergency fund", "red"
    if months < 6:  return "▲ FAIR — aim for 6+ months",        "yellow"
    if months < 12: return "✓ GOOD",                             "cyan"
    return "✓ EXCELLENT — 12+ months covered",                   "green"


def volatility(data: list[int]) -> tuple[str, str]:
    """Income-volatility label: (label, colour)"""
    if len(data) < 2: return "N/A", "dim"
    cv = stdev(data) / mean(data)
    if cv < 0.06: return "LOW",    "green"
    if cv < 0.15: return "MEDIUM", "yellow"
    return "HIGH", "red"


def color_delta(delta: int) -> str:
    """Colour for a spending delta (increase = red, decrease = green)."""
    if delta > 0: return "red"
    if delta < 0: return "green"
    return "dim"


def trend_symbol(delta: int) -> str:
    """Rich-markup arrow for a spending delta."""
    if delta > 0: return "[red]▲[/]"
    if delta < 0: return "[green]▼[/]"
    return "[dim]─[/]"