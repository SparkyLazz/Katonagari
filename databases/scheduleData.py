"""
schedule_data.py — JSON-backed CRUD store for Katonagari schedule events.
Data lives in  data/schedule.json  (created on first run with sample data).
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

DATA_FILE = Path(__file__).parent / "schedule.json"

# ─── Constants ────────────────────────────────────────────────────────────────

PRIORITY: dict[str, tuple[str, str]] = {
    "critical": ("$error",   "CRIT"),
    "high":     ("$warning", "HIGH"),
    "medium":   ("$primary", "MED "),
    "low":      ("$success", "LOW "),
}
PRIORITIES  = list(PRIORITY.keys())
CATEGORIES  = ["class", "assignment", "work", "meeting", "personal"]

CATEGORY_ICON: dict[str, str] = {
    "class":      "[C]",
    "assignment": "[A]",
    "work":       "[W]",
    "meeting":    "[M]",
    "personal":   "[P]",
}
CATEGORY_COLOR: dict[str, str] = {
    "class":      "$primary",
    "assignment": "$error",
    "work":       "$accent",
    "meeting":    "$warning",
    "personal":   "$success",
}

# ─── Serialization ────────────────────────────────────────────────────────────

def _to_str(d):
    return d.isoformat() if isinstance(d, date) else d

def _to_date(s):
    return date.fromisoformat(s) if isinstance(s, str) else s

def _serialize(events):
    return [
        {**e, "date": _to_str(e["date"]), "deadline": _to_str(e.get("deadline"))}
        for e in events
    ]

def _deserialize(events):
    return [
        {**e, "date": _to_date(e["date"]), "deadline": _to_date(e.get("deadline"))}
        for e in events
    ]

# ─── Persistence ──────────────────────────────────────────────────────────────

def load_events():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return _deserialize(json.load(f))
    events = _default_events()
    save_events(events)
    return events

def save_events(events):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(_serialize(events), f, indent=2, ensure_ascii=False)

# ─── CRUD ─────────────────────────────────────────────────────────────────────

def _next_id(events):
    return max((e["id"] for e in events), default=0) + 1

def add_event(events, data):
    data["id"] = _next_id(events)
    events.append(data)
    save_events(events)
    return data

def update_event(events, event_id, updates):
    for i, ev in enumerate(events):
        if ev["id"] == event_id:
            events[i] = {**ev, **updates, "id": event_id}
            break
    save_events(events)

def delete_event(events, event_id):
    events[:] = [e for e in events if e["id"] != event_id]
    save_events(events)

def get_events_for_date(events, d):
    return sorted([e for e in events if e["date"] == d], key=lambda e: e["time"])

def get_week_dates():
    today = date.today()
    return [today + timedelta(days=i) for i in range(7)]

# ─── Default seed data ────────────────────────────────────────────────────────

def _default_events():
    t = date.today()
    def d(n): return t + timedelta(days=n)
    return []