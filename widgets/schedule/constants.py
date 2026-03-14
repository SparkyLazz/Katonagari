from __future__ import annotations

# ── Rich color map for DataTable markup ───────────────────────────────────────
_RICH: dict[str, str] = {
    "$error":      "red",
    "$warning":    "yellow",
    "$primary":    "blue",
    "$success":    "green",
    "$accent":     "cyan",
    "$text-muted": "dim white",
}
def _rc(var: str) -> str:
    return _RICH.get(var, "white")


# ── Select options ─────────────────────────────────────────────────────────────
_PRI_OPTS = [
    ("● Critical", "critical"),
    ("● High",     "high"),
    ("○ Medium",   "medium"),
    ("○ Low",      "low"),
]
_CAT_OPTS = [
    ("[C] Class",       "class"),
    ("[A] Assignment",  "assignment"),
    ("[W] Work",        "work"),
    ("[M] Meeting",     "meeting"),
    ("[P] Personal",    "personal"),
]


# ── Shared Rule style injected into each modal's DEFAULT_CSS ──────────────────
_MODAL_RULE_CSS = """
    Rule {
        color: $surface-lighten-2;
        margin: 0 1;
        height: 1;
    }
"""
