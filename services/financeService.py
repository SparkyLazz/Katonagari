"""
financeService.py
─────────────────
Single source of truth for all finance data and computations.
Backed by  data/finance.json  —  all widgets import from here.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev

# ─── Paths ───────────────────────────────────────────────────────────────────

DATA_FILE: Path = Path(__file__).resolve().parent.parent / "databases" / "finance.json"
print(f"[FinanceService] DATA_FILE → {DATA_FILE}")

# ─── Constants ───────────────────────────────────────────────────────────────

CATEGORIES: list[str] = [
    "Food", "Health", "Housing", "Income",
    "Other", "Subscription", "Transport", "Utility",
]

CATEGORY_OPTIONS: list[tuple[str, str]] = [(c, c) for c in CATEGORIES]

EXPENSE_CATEGORIES: list[str] = [c for c in CATEGORIES if c != "Income"]

# ─── Models ──────────────────────────────────────────────────────────────────

@dataclass
class Transaction:
    """One ledger entry.  `date` is stored as ISO-8601 (YYYY-MM-DD)."""

    date:    str   # "2024-01-15"
    desc:    str
    cat:     str
    amount:  int   # positive = income, negative = expense
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
            "date":   self.date,
            "desc":   self.desc,
            "cat":    self.cat,
            "amount": self.amount,
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


# ─── Service ─────────────────────────────────────────────────────────────────

class FinanceService:
    """
    Loads  data/finance.json, exposes typed transaction list,
    persists mutations, and computes all derived values needed by widgets.
    """

    def __init__(self, data_file: Path = DATA_FILE) -> None:
        self._file = data_file
        self._raw:  dict              = self._load()
        self._txs:  list[Transaction] = []
        self._rebuild()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._file.exists():
            with open(self._file, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return {
            "meta":         {"liquid_base": 0, "investments": 0, "debt": 0},
            "transactions": [],
        }

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file, "w", encoding="utf-8") as fh:
            json.dump(self._raw, fh, indent=2)

    def _rebuild(self) -> None:
        """Re-sort raw list by date and recompute running balances."""
        running = self._raw["meta"].get("liquid_base", 0)
        self._txs = []
        for raw in sorted(self._raw["transactions"], key=lambda r: r["date"]):
            running += raw["amount"]
            self._txs.append(Transaction(
                date    = raw["date"],
                desc    = raw["desc"],
                cat     = raw["cat"],
                amount  = raw["amount"],
                balance = running,
            ))

    # ── Transactions ──────────────────────────────────────────────────────────

    @property
    def transactions(self) -> list[Transaction]:
        return list(self._txs)

    def add(self, tx: Transaction) -> None:
        self._raw["transactions"].append(tx.to_dict())
        self._rebuild()
        self._save()

    def remove(self, index: int) -> Transaction:
        """Remove by sorted-list index; matches on date + desc + amount."""
        removed = self._txs[index]
        for i, raw in enumerate(self._raw["transactions"]):
            if (raw["date"]   == removed.date   and
                raw["desc"]   == removed.desc   and
                raw["amount"] == removed.amount):
                self._raw["transactions"].pop(i)
                break
        self._rebuild()
        self._save()
        return removed

    # ── Meta properties ───────────────────────────────────────────────────────

    @property
    def liquid(self) -> int:
        """Current liquid cash (last running balance)."""
        return self._txs[-1].balance if self._txs else self._raw["meta"].get("liquid_base", 0)

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

    def monthly_summaries(self) -> list[MonthlySummary]:
        """Ordered list of per-month summaries (oldest → newest)."""
        groups: dict[str, dict] = {}
        for tx in self._txs:
            mk = tx.month_key
            if mk not in groups:
                groups[mk] = {"income": 0, "expenses": 0, "sort_key": tx.date[:7]}
            if tx.amount > 0:
                groups[mk]["income"]   += tx.amount
            else:
                groups[mk]["expenses"] += abs(tx.amount)

        result: list[MonthlySummary] = []
        running_nw = (
            self._raw["meta"].get("liquid_base", 0)
            + self.investments
            - self.debt
        )
        prev_nw = running_nw

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

    def category_monthly(self) -> dict[str, list[int]]:
        """
        Returns {category: [spend_per_month, ...]} aligned to monthly_summaries().
        Only expense categories; amounts are positive integers.
        """
        summaries   = self.monthly_summaries()
        month_order = [s.month for s in summaries]

        cat_data: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for tx in self._txs:
            if tx.amount < 0:
                cat_data[tx.cat][tx.month_key] += abs(tx.amount)

        return {
            cat: [cat_data[cat].get(m, 0) for m in month_order]
            for cat in EXPENSE_CATEGORIES
        }

    # ── Period analysis ───────────────────────────────────────────────────────

    def build_period(self, n: int) -> PeriodData:
        """Build a PeriodData for the last *n* months."""
        summaries = self.monthly_summaries()
        cat_hist  = self.category_monthly()
        n_total   = len(summaries)

        recent  = summaries[-n:]
        months  = [s.month.split()[0] for s in recent]   # "Jan 2024" → "Jan"
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

    def current_stats(self) -> dict:
        """
        Computed stats for the most-recent month vs the one before it.
        Used by the Overview screen.
        """
        summaries = self.monthly_summaries()
        if not summaries:
            return {}

        curr = summaries[-1]
        prev = summaries[-2] if len(summaries) > 1 else None

        save_rate      = curr.net / curr.income * 100      if curr.income            else 0.0
        prev_save_rate = prev.net / prev.income * 100      if prev and prev.income   else 0.0
        inc_change     = curr.income   - (prev.income      if prev else 0)
        exp_pct        = ((curr.expenses - prev.expenses) / prev.expenses * 100
                         if prev and prev.expenses else 0.0)
        nw_pct         = (curr.change / prev.net_worth * 100
                         if prev and prev.net_worth else 0.0)

        return {
            "net_worth":        self.net_worth,
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
            "liquid":           self.liquid,
            "current_month":    curr.month,
        }


# ─── Formatting helpers (shared across all widgets) ───────────────────────────

def fmt_amount(n: int, sign: bool = True) -> str:
    """Rich-markup coloured amount: '[green]+$1,500[/]'"""
    prefix = ("+" if n > 0 else "") if sign else ""
    color  = "green" if n >= 0 else "red"
    return f"[{color}]{prefix}${abs(n):,}[/]"


def fmt_change(n: int) -> str:
    """Rich-markup net-worth change: '[green]+$700[/]' or '[dim]─[/]'"""
    if n == 0: return "[dim]─[/]"
    if n > 0:  return f"[green]+${n:,}[/]"
    return f"[red]-${abs(n):,}[/]"


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