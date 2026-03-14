from __future__ import annotations
from databases.financeData import (
    ACCOUNTS, ACCOUNT_ICON,
    EXPENSE_CATEGORIES, INCOME_CATEGORIES,
    CATEGORY_ICON,
)

# ─────────────────────────────────────────────────────────────────────────────
# Rich color helpers
# DataTable markup cannot use CSS variables — map semantic names to Rich colors.
# ─────────────────────────────────────────────────────────────────────────────
_RICH: dict[str, str] = {
    "$error":      "red",
    "$warning":    "yellow",
    "$primary":    "blue",
    "$success":    "green",
    "$accent":     "cyan",
    "$text-muted": "dim white",
}
_ACC_RICH: dict[str, str] = {
    "GoPay":   "blue",
    "SeaBank": "green",
    "NeoBank": "cyan",
    "Cash":    "yellow",
}
_TYPE_PILL: dict[str, str] = {
    "expense":  "[bold red]EXP[/]",
    "income":   "[bold green]INC[/]",
    "transfer": "[bold cyan]TRF[/]",
}

def _rc(css_var: str) -> str:
    return _RICH.get(css_var, "white")


# ─────────────────────────────────────────────────────────────────────────────
# Shared widget helpers
# ─────────────────────────────────────────────────────────────────────────────
_MODAL_RULE_CSS = "Rule { color: $surface-lighten-2; margin: 0 1; height: 1; }"

_TYPE_OPTS    = [("↓ Expense", "expense"), ("↑ Income", "income"), ("⇆ Transfer", "transfer")]
_ACC_OPTS     = [(f"{ACCOUNT_ICON[a]} {a}", a) for a in ACCOUNTS]
_EXP_CAT_OPTS = [(f"{CATEGORY_ICON.get(c, '[?]')} {c}", c) for c in EXPENSE_CATEGORIES]
_INC_CAT_OPTS = [(f"{CATEGORY_ICON.get(c, '[?]')} {c}", c) for c in INCOME_CATEGORIES]
_MONTH_NAMES  = ["Jan","Feb","Mar","Apr","May","Jun",
                 "Jul","Aug","Sep","Oct","Nov","Dec"]
_FILTER_KEYS  = ["all", "expense", "income", "transfer"]
_FILTER_NAMES = {"all": "All", "expense": "Expense",
                 "income": "Income", "transfer": "Transfer"}
