"""
financeData.py — JSON-backed CRUD store for Katonagari finance.
Data lives in  databases/finance.json  (created on first run).

Supported transaction types: expense | income | transfer
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

DATA_FILE = Path(__file__).parent / "finance.json"

# ── Accounts ──────────────────────────────────────────────────────────────────

ACCOUNTS: list[str] = ["GoPay", "SeaBank", "NeoBank", "Cash"]

ACCOUNT_COLOR: dict[str, str] = {
    "GoPay":   "$primary",
    "SeaBank":  "$success",
    "NeoBank":  "$accent",
    "Cash":     "$warning",
}

ACCOUNT_ICON: dict[str, str] = {
    "GoPay":   "[G]",
    "SeaBank":  "[S]",
    "NeoBank":  "[N]",
    "Cash":     "[C]",
}

# ── Categories ────────────────────────────────────────────────────────────────

EXPENSE_CATEGORIES: list[str] = [
    "Food & Drinks",
    "Transport",
    "Bills & Utilities",
    "Entertainment",
    "Other",
]

INCOME_CATEGORIES: list[str] = [
    "Salary",
    "Investment",
    "Gift / Transfer In",
    "Other",
]

CATEGORY_ICON: dict[str, str] = {
    "Food & Drinks":      "[F]",
    "Transport":          "[T]",
    "Bills & Utilities":  "[B]",
    "Entertainment":      "[E]",
    "Other":              "[?]",
    "Salary":             "[S]",
    "Investment":         "[I]",
    "Gift / Transfer In": "[G]",
}

CATEGORY_COLOR: dict[str, str] = {
    "Food & Drinks":      "$warning",
    "Transport":          "$primary",
    "Bills & Utilities":  "$error",
    "Entertainment":      "$accent",
    "Other":              "$text-muted",
    "Salary":             "$success",
    "Investment":         "$primary",
    "Gift / Transfer In": "$accent",
}

# ── Type styling ──────────────────────────────────────────────────────────────

TYPE_COLOR: dict[str, str] = {
    "expense":  "$error",
    "income":   "$success",
    "transfer": "$accent",
}

TYPE_LABEL: dict[str, str] = {
    "expense":  "EXP",
    "income":   "INC",
    "transfer": "TRF",
}

# ── Currency helpers ──────────────────────────────────────────────────────────

def fmt_rp(amount: float, sign: bool = False) -> str:
    """Format as Indonesian Rupiah. e.g. Rp 1.500.000"""
    s      = f"{int(abs(amount)):,}".replace(",", ".")
    prefix = "Rp "
    if sign:
        prefix = "+Rp " if amount >= 0 else "-Rp "
    elif amount < 0:
        prefix = "-Rp "
    return f"{prefix}{s}"

def fmt_rp_short(amount: float) -> str:
    """Compact form for charts: 1.5M, 250K, etc."""
    a = abs(amount)
    sign = "-" if amount < 0 else ""
    if a >= 1_000_000:
        return f"{sign}{a / 1_000_000:.1f}M"
    if a >= 1_000:
        return f"{sign}{a / 1_000:.0f}K"
    return f"{sign}{int(a)}"

# ── Serialization ─────────────────────────────────────────────────────────────

def _to_str(d: date | None) -> str | None:
    return d.isoformat() if isinstance(d, date) else d

def _to_date(s: str | None) -> date | None:
    return date.fromisoformat(s) if isinstance(s, str) else s

def _serialize(data: dict) -> dict:
    return {
        "accounts": data["accounts"],
        "transactions": [
            {**t, "date": _to_str(t["date"])}
            for t in data["transactions"]
        ],
    }

def _deserialize(raw: dict) -> dict:
    return {
        "accounts": raw.get("accounts", {acc: 0 for acc in ACCOUNTS}),
        "transactions": [
            {**t, "date": _to_date(t["date"])}
            for t in raw.get("transactions", [])
        ],
    }

# ── Persistence ───────────────────────────────────────────────────────────────

def _default_data() -> dict:
    return {
        "accounts":     {acc: 0 for acc in ACCOUNTS},
        "transactions": [],
    }

def load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return _deserialize(json.load(f))
    data = _default_data()
    save_data(data)
    return data

def save_data(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(_serialize(data), f, indent=2, ensure_ascii=False)

# ── Balance helpers ───────────────────────────────────────────────────────────

def _apply_balance(accounts: dict, tx: dict, sign: int) -> None:
    """Apply or reverse a transaction's effect on account balances."""
    amt = tx["amount"]
    if tx["type"] == "income":
        accounts[tx["account"]] = accounts.get(tx["account"], 0) + sign * amt
    elif tx["type"] == "expense":
        accounts[tx["account"]] = accounts.get(tx["account"], 0) - sign * amt
    elif tx["type"] == "transfer":
        accounts[tx["account"]]        = accounts.get(tx["account"], 0)        - sign * amt
        accounts[tx["to_account"]]     = accounts.get(tx["to_account"], 0)     + sign * amt

# ── CRUD ──────────────────────────────────────────────────────────────────────

def _next_id(transactions: list) -> int:
    return max((t["id"] for t in transactions), default=0) + 1

def add_transaction(data: dict, tx: dict) -> dict:
    tx["id"] = _next_id(data["transactions"])
    data["transactions"].append(tx)
    _apply_balance(data["accounts"], tx, sign=+1)
    save_data(data)
    return tx

def update_transaction(data: dict, tx_id: int, updates: dict) -> None:
    for i, tx in enumerate(data["transactions"]):
        if tx["id"] == tx_id:
            _apply_balance(data["accounts"], tx, sign=-1)       # reverse old
            new_tx = {**tx, **updates, "id": tx_id}
            data["transactions"][i] = new_tx
            _apply_balance(data["accounts"], new_tx, sign=+1)   # apply new
            break
    save_data(data)

def delete_transaction(data: dict, tx_id: int) -> None:
    for tx in data["transactions"]:
        if tx["id"] == tx_id:
            _apply_balance(data["accounts"], tx, sign=-1)
            break
    data["transactions"] = [t for t in data["transactions"] if t["id"] != tx_id]
    save_data(data)

# ── Aggregations ──────────────────────────────────────────────────────────────

def get_monthly_summary(transactions: list, year: int, month: int) -> dict:
    """Return {income, expense, net, transactions} for a given year/month."""
    monthly  = [t for t in transactions
                if t["date"].year == year and t["date"].month == month]
    income   = sum(t["amount"] for t in monthly if t["type"] == "income")
    expense  = sum(t["amount"] for t in monthly if t["type"] == "expense")
    return {
        "year": year, "month": month,
        "income": income, "expense": expense,
        "net": income - expense,
        "count": len([t for t in monthly if t["type"] != "transfer"]),
    }

def get_last_n_months(transactions: list, n: int = 12) -> list[dict]:
    """Return monthly summaries for the last *n* months (oldest first)."""
    today  = date.today()
    result = []
    for i in range(n - 1, -1, -1):
        month = today.month - i
        year  = today.year
        while month <= 0:
            month += 12
            year  -= 1
        result.append(get_monthly_summary(transactions, year, month))
    return result

def get_category_breakdown(transactions: list, year: int, month: int) -> dict[str, float]:
    """Return expense totals by category for a given month."""
    monthly = [t for t in transactions
               if t["date"].year == year and t["date"].month == month
               and t["type"] == "expense"]
    breakdown: dict[str, float] = {}
    for t in monthly:
        breakdown[t["category"]] = breakdown.get(t["category"], 0) + t["amount"]
    return breakdown