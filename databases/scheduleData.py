from datetime import date, timedelta

today = date.today()
monday = today - timedelta(days=today.weekday())

# Priority levels and their display colors (Textual color names)
PRIORITY = {
    "critical": ("$error",   "CRIT"),
    "high":     ("$warning", "HIGH"),
    "medium":   ("$primary", "MED "),
    "low":      ("$success", "LOW "),
}

# Category icons (ASCII-safe for terminals)
CATEGORY_ICON = {
    "class":      "[C]",
    "assignment": "[A]",
    "work":       "[W]",
    "meeting":    "[M]",
    "personal":   "[P]",
}

CATEGORY_COLOR = {
    "class":      "$primary",
    "assignment": "$error",
    "work":       "$accent",
    "meeting":    "$warning",
    "personal":   "$success",
}

def _day(offset: int) -> date:
    return today + timedelta(days=offset)

EVENTS: list[dict] = [
    # ── TODAY ──────────────────────────────────────────────────────────────
    {
        "id": 1,
        "title": "Linear Algebra Lecture",
        "category": "class",
        "priority": "high",
        "date": _day(0),
        "time": "08:00",
        "end_time": "09:30",
        "location": "Room B204",
        "deadline": None,
        "notes": "Midterm coverage: Ch 4-7. Bring printed formula sheet.",
    },
    {
        "id": 2,
        "title": "Algorithm Design Assignment",
        "category": "assignment",
        "priority": "critical",
        "date": _day(0),
        "time": "10:00",
        "end_time": None,
        "location": None,
        "deadline": _day(0),
        "notes": "Graph traversal + DP problem set. Submit on LMS by 23:59.",
    },
    {
        "id": 3,
        "title": "Sprint Standup — Backend Team",
        "category": "meeting",
        "priority": "medium",
        "date": _day(0),
        "time": "13:00",
        "end_time": "13:30",
        "location": "Google Meet",
        "deadline": None,
        "notes": "Update Jira tickets before call. Block for 30 min.",
    },
    {
        "id": 4,
        "title": "Operating Systems Lab",
        "category": "class",
        "priority": "high",
        "date": _day(0),
        "time": "15:00",
        "end_time": "17:00",
        "location": "Lab 3 — CS Building",
        "deadline": None,
        "notes": "Shell scripting session. Bring USB with live Linux.",
    },
    {
        "id": 5,
        "title": "Side Project — API Refactor",
        "category": "work",
        "priority": "medium",
        "date": _day(0),
        "time": "20:00",
        "end_time": "22:00",
        "location": "Home",
        "deadline": _day(3),
        "notes": "Migrate auth service to FastAPI. Review PR #42 first.",
    },

    # ── TOMORROW ──────────────────────────────────────────────────────────
    {
        "id": 6,
        "title": "Data Structures Midterm",
        "category": "class",
        "priority": "critical",
        "date": _day(1),
        "time": "09:00",
        "end_time": "11:00",
        "location": "Hall A",
        "deadline": None,
        "notes": "Trees, heaps, hash tables. No open book.",
    },
    {
        "id": 7,
        "title": "Code Review — Feature Branch",
        "category": "work",
        "priority": "high",
        "date": _day(1),
        "time": "14:00",
        "end_time": "15:00",
        "location": "Slack Huddle",
        "deadline": _day(1),
        "notes": "Review auth middleware refactor before merge to main.",
    },
    {
        "id": 8,
        "title": "Research Paper Draft",
        "category": "assignment",
        "priority": "high",
        "date": _day(1),
        "time": "19:00",
        "end_time": None,
        "location": None,
        "deadline": _day(4),
        "notes": "Section 3 & 4 — System Design. Target 1500 words.",
    },

    # ── DAY +2 ────────────────────────────────────────────────────────────
    {
        "id": 9,
        "title": "Networking Lecture",
        "category": "class",
        "priority": "medium",
        "date": _day(2),
        "time": "10:00",
        "end_time": "11:30",
        "location": "Room C101",
        "deadline": None,
        "notes": "TCP/IP deep dive. Quiz at end of class.",
    },
    {
        "id": 10,
        "title": "1:1 with Tech Lead",
        "category": "meeting",
        "priority": "high",
        "date": _day(2),
        "time": "16:00",
        "end_time": "16:30",
        "location": "Zoom",
        "deadline": None,
        "notes": "Discuss Q2 roadmap + internship extension terms.",
    },
    {
        "id": 11,
        "title": "Study Group — Algo Prep",
        "category": "personal",
        "priority": "low",
        "date": _day(2),
        "time": "18:00",
        "end_time": "20:00",
        "location": "Library Floor 4",
        "deadline": None,
        "notes": "LeetCode hard set. Bring snacks.",
    },

    # ── DAY +3 ────────────────────────────────────────────────────────────
    {
        "id": 12,
        "title": "Cloud Architecture Quiz",
        "category": "class",
        "priority": "critical",
        "date": _day(3),
        "time": "08:00",
        "end_time": "09:00",
        "location": "Online — LMS",
        "deadline": _day(3),
        "notes": "AWS/GCP concepts. Timed 60 min — no retake.",
    },
    {
        "id": 13,
        "title": "Deploy v2.3 to Staging",
        "category": "work",
        "priority": "high",
        "date": _day(3),
        "time": "11:00",
        "end_time": "13:00",
        "location": "Remote",
        "deadline": _day(3),
        "notes": "Run smoke tests. Rollback plan in runbook doc.",
    },

    # ── DAY +4 ────────────────────────────────────────────────────────────
    {
        "id": 14,
        "title": "Research Paper Submission",
        "category": "assignment",
        "priority": "critical",
        "date": _day(4),
        "time": "23:59",
        "end_time": None,
        "location": None,
        "deadline": _day(4),
        "notes": "Final submission via IEEE portal. PDF format only.",
    },
    {
        "id": 15,
        "title": "Hackathon Kickoff",
        "category": "personal",
        "priority": "medium",
        "date": _day(4),
        "time": "18:00",
        "end_time": "20:00",
        "location": "Innovation Hub",
        "deadline": None,
        "notes": "Team of 3. Focus on ML + infra track.",
    },

    # ── DAY +5 ────────────────────────────────────────────────────────────
    {
        "id": 16,
        "title": "Hackathon — Build Day",
        "category": "work",
        "priority": "high",
        "date": _day(5),
        "time": "09:00",
        "end_time": "23:00",
        "location": "Innovation Hub",
        "deadline": _day(6),
        "notes": "Full sprint. Bring chargers, laptop, headphones.",
    },

    # ── DAY +6 ────────────────────────────────────────────────────────────
    {
        "id": 17,
        "title": "Hackathon — Demo & Judging",
        "category": "work",
        "priority": "critical",
        "date": _day(6),
        "time": "13:00",
        "end_time": "17:00",
        "location": "Innovation Hub",
        "deadline": None,
        "notes": "5-min demo slot. Prepare slides + live demo fallback.",
    },
]

def get_events_for_date(d: date) -> list[dict]:
    return sorted(
        [e for e in EVENTS if e["date"] == d],
        key=lambda e: e["time"],
    )

def get_week_dates() -> list[date]:
    """Return 7 days starting from today."""
    return [today + timedelta(days=i) for i in range(7)]