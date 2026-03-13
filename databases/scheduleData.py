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
    return [
        {"id":  1, "title": "Linear Algebra Lecture",      "category": "class",      "priority": "high",     "date": d(0), "time": "08:00", "end_time": "09:30", "location": "Room B204",      "deadline": None, "notes": "Midterm coverage Ch 4-7."},
        {"id":  2, "title": "Algorithm Design Assignment",  "category": "assignment", "priority": "critical", "date": d(0), "time": "10:00", "end_time": None,    "location": None,             "deadline": d(0), "notes": "Graph traversal + DP. Submit LMS by 23:59."},
        {"id":  3, "title": "Sprint Standup",               "category": "meeting",    "priority": "medium",   "date": d(0), "time": "13:00", "end_time": "13:30", "location": "Google Meet",    "deadline": None, "notes": "Update Jira before call."},
        {"id":  4, "title": "Operating Systems Lab",        "category": "class",      "priority": "high",     "date": d(0), "time": "15:00", "end_time": "17:00", "location": "Lab 3 CS Bldg",  "deadline": None, "notes": "Shell scripting. Bring USB with live Linux."},
        {"id":  5, "title": "Side Project — API Refactor",  "category": "work",       "priority": "medium",   "date": d(0), "time": "20:00", "end_time": "22:00", "location": "Home",           "deadline": d(3), "notes": "Migrate auth service to FastAPI."},
        {"id":  6, "title": "Data Structures Midterm",      "category": "class",      "priority": "critical", "date": d(1), "time": "09:00", "end_time": "11:00", "location": "Hall A",         "deadline": None, "notes": "Trees, heaps, hash tables. No open book."},
        {"id":  7, "title": "Code Review — Feature Branch", "category": "work",       "priority": "high",     "date": d(1), "time": "14:00", "end_time": "15:00", "location": "Slack Huddle",   "deadline": d(1), "notes": "Review auth middleware before merge."},
        {"id":  8, "title": "Research Paper Draft",         "category": "assignment", "priority": "high",     "date": d(1), "time": "19:00", "end_time": None,    "location": None,             "deadline": d(4), "notes": "Sections 3 & 4. Target 1500 words."},
        {"id":  9, "title": "Networking Lecture",           "category": "class",      "priority": "medium",   "date": d(2), "time": "10:00", "end_time": "11:30", "location": "Room C101",      "deadline": None, "notes": "TCP/IP deep dive. Quiz at end."},
        {"id": 10, "title": "1:1 with Tech Lead",           "category": "meeting",    "priority": "high",     "date": d(2), "time": "16:00", "end_time": "16:30", "location": "Zoom",           "deadline": None, "notes": "Q2 roadmap + internship extension."},
        {"id": 11, "title": "Cloud Architecture Quiz",      "category": "class",      "priority": "critical", "date": d(3), "time": "08:00", "end_time": "09:00", "location": "Online LMS",     "deadline": d(3), "notes": "AWS/GCP. Timed 60 min — no retake."},
        {"id": 12, "title": "Deploy v2.3 to Staging",       "category": "work",       "priority": "high",     "date": d(3), "time": "11:00", "end_time": "13:00", "location": "Remote",         "deadline": d(3), "notes": "Run smoke tests. Rollback plan in runbook."},
        {"id": 13, "title": "Research Paper Submission",    "category": "assignment", "priority": "critical", "date": d(4), "time": "23:59", "end_time": None,    "location": None,             "deadline": d(4), "notes": "Final via IEEE portal. PDF only."},
        {"id": 14, "title": "Hackathon Kickoff",            "category": "personal",   "priority": "medium",   "date": d(4), "time": "18:00", "end_time": "20:00", "location": "Innovation Hub", "deadline": None, "notes": "Team of 3. ML + infra track."},
        {"id": 15, "title": "Hackathon — Demo Day",         "category": "work",       "priority": "critical", "date": d(5), "time": "13:00", "end_time": "17:00", "location": "Innovation Hub", "deadline": None, "notes": "5-min demo. Slides + live fallback."},
    ]