"""
pomodoroService.py
──────────────────
Single source of truth for all Pomodoro/study session data.
Backed by  databases/pomodoro.json  —  all widgets import from here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────

DATA_FILE: Path = Path(__file__).resolve().parent.parent / "databases" / "pomodoro.json"

# ─── Constants ───────────────────────────────────────────────────────────────

SESSION_TYPES: list[str]           = ["Focus", "Short Break", "Long Break"]
SUBJECT_OPTIONS: list[tuple[str, str]] = [
    (s, s) for s in ["Coding", "Math", "Physics", "Reading", "Writing", "Language", "Other"]
]

DAYS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ─── Models ──────────────────────────────────────────────────────────────────

@dataclass
class Session:
    """One Pomodoro session record."""

    date:      str   # "2024-01-15"
    start:     str   # "09:30"
    duration:  int   # minutes
    type:      str   # "Focus" | "Short Break" | "Long Break"
    subject:   str   # e.g. "Coding"
    completed: bool  = True
    notes:     str   = ""

    @property
    def display_date(self) -> str:
        return datetime.strptime(self.date, "%Y-%m-%d").strftime("%b %d")

    @property
    def display_duration(self) -> str:
        h, m = divmod(self.duration, 60)
        return f"{h}h {m:02d}m" if h else f"{m}m"

    @property
    def sort_key(self) -> str:
        return f"{self.date} {self.start}"

    def to_dict(self) -> dict:
        return {
            "date":      self.date,
            "start":     self.start,
            "duration":  self.duration,
            "type":      self.type,
            "subject":   self.subject,
            "completed": self.completed,
            "notes":     self.notes,
        }


@dataclass
class DaySummary:
    date:           str
    label:          str   # "Mon", "Tue", …
    focus_minutes:  int
    sessions:       int
    goal_minutes:   int

    @property
    def goal_pct(self) -> float:
        return min(self.focus_minutes / self.goal_minutes, 1.0) if self.goal_minutes else 0.0

    @property
    def display_time(self) -> str:
        h, m = divmod(self.focus_minutes, 60)
        return f"{h}h {m:02d}m" if h else f"{m}m" if m else "─"


@dataclass
class OverviewStats:
    today_focus:     int    # minutes
    today_sessions:  int
    today_goal:      int
    streak:          int    # consecutive days with ≥1 focus session
    week_focus:      int    # minutes this week (Mon–Sun)
    week_sessions:   int
    best_day_label:  str
    best_day_mins:   int
    all_time_mins:   int
    all_time_sessions: int
    week_days:       list[DaySummary]


# ─── Service ─────────────────────────────────────────────────────────────────

class PomodoroService:
    """Loads databases/pomodoro.json, exposes typed session list,
    persists mutations, and computes all derived values needed by widgets."""

    def __init__(self, data_file: Path = DATA_FILE) -> None:
        self._file = data_file
        self._raw:      dict           = self._load()
        self._sessions: list[Session]  = []
        self._rebuild()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._file.exists():
            with open(self._file, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return {
            "meta":     {"daily_goal_minutes": 120, "focus_duration": 25,
                         "short_break": 5, "long_break": 15},
            "sessions": [],
        }

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file, "w", encoding="utf-8") as fh:
            json.dump(self._raw, fh, indent=2)

    def _rebuild(self) -> None:
        self._sessions = sorted(
            [
                Session(
                    date      = s["date"],
                    start     = s["start"],
                    duration  = s["duration"],
                    type      = s["type"],
                    subject   = s["subject"],
                    completed = s.get("completed", True),
                    notes     = s.get("notes", ""),
                )
                for s in self._raw["sessions"]
            ],
            key=lambda s: s.sort_key,
        )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    @property
    def sessions(self) -> list[Session]:
        return list(self._sessions)

    def add(self, s: Session) -> None:
        self._raw["sessions"].append(s.to_dict())
        self._rebuild()
        self._save()

    def remove(self, index: int) -> Session:
        removed = self._sessions[index]
        for i, raw in enumerate(self._raw["sessions"]):
            if (raw["date"] == removed.date and raw["start"] == removed.start
                    and raw["duration"] == removed.duration):
                self._raw["sessions"].pop(i)
                break
        self._rebuild()
        self._save()
        return removed

    # ── Meta ──────────────────────────────────────────────────────────────────

    @property
    def daily_goal(self) -> int:
        return self._raw["meta"].get("daily_goal_minutes", 120)

    @property
    def focus_duration(self) -> int:
        return self._raw["meta"].get("focus_duration", 25)

    # ── Derived: per-date index ────────────────────────────────────────────────

    def _focus_by_date(self) -> dict[str, int]:
        """date_str → total focus minutes"""
        result: dict[str, int] = {}
        for s in self._sessions:
            if s.type == "Focus" and s.completed:
                result[s.date] = result.get(s.date, 0) + s.duration
        return result

    # ── Derived: streak ───────────────────────────────────────────────────────

    def _streak(self) -> int:
        focus_dates = set(self._focus_by_date().keys())
        streak = 0
        day = date.today()
        while day.isoformat() in focus_dates:
            streak += 1
            day -= timedelta(days=1)
        return streak

    # ── Derived: this week ────────────────────────────────────────────────────

    def _week_days(self) -> list[DaySummary]:
        today     = date.today()
        monday    = today - timedelta(days=today.weekday())
        goal      = self.daily_goal
        summaries = []
        for i, label in enumerate(DAYS_SHORT):
            day_date = monday + timedelta(days=i)
            iso      = day_date.isoformat()
            focus_m  = sum(
                s.duration for s in self._sessions
                if s.date == iso and s.type == "Focus" and s.completed
            )
            session_count = sum(
                1 for s in self._sessions
                if s.date == iso and s.type == "Focus" and s.completed
            )
            summaries.append(DaySummary(
                date          = iso,
                label         = label,
                focus_minutes = focus_m,
                sessions      = session_count,
                goal_minutes  = goal,
            ))
        return summaries

    # ── Overview stats ────────────────────────────────────────────────────────

    def overview_stats(self) -> OverviewStats:
        today_iso  = date.today().isoformat()
        week_days  = self._week_days()

        today_sessions = [
            s for s in self._sessions
            if s.date == today_iso and s.type == "Focus" and s.completed
        ]
        today_focus   = sum(s.duration for s in today_sessions)

        week_focus    = sum(d.focus_minutes for d in week_days)
        week_sessions = sum(d.sessions      for d in week_days)

        # Best single day ever
        fbd = self._focus_by_date()
        if fbd:
            best_iso  = max(fbd, key=fbd.__getitem__)
            best_mins = fbd[best_iso]
            best_label = datetime.strptime(best_iso, "%Y-%m-%d").strftime("%b %d")
        else:
            best_label, best_mins = "─", 0

        all_focus = [s for s in self._sessions if s.type == "Focus" and s.completed]

        return OverviewStats(
            today_focus      = today_focus,
            today_sessions   = len(today_sessions),
            today_goal       = self.daily_goal,
            streak           = self._streak(),
            week_focus       = week_focus,
            week_sessions    = week_sessions,
            best_day_label   = best_label,
            best_day_mins    = best_mins,
            all_time_mins    = sum(s.duration for s in all_focus),
            all_time_sessions= len(all_focus),
            week_days        = week_days,
        )

    # ── Recent sessions (for table) ───────────────────────────────────────────

    def recent_focus(self, n: int = 10) -> list[Session]:
        focus = [s for s in self._sessions if s.type == "Focus"]
        return focus[-n:]


# ─── Formatting helpers ───────────────────────────────────────────────────────

def fmt_mins(minutes: int) -> str:
    """'2h 05m' or '45m'"""
    if minutes == 0:
        return "[dim]─[/]"
    h, m = divmod(minutes, 60)
    if h:
        return f"[bold]{h}[/]h [bold]{m:02d}[/]m"
    return f"[bold]{m}[/]m"


def fmt_streak(n: int) -> str:
    if n == 0:  return "[dim]─[/]"
    if n < 3:   return f"[yellow]{n} day{'s' if n > 1 else ''}[/]"
    if n < 7:   return f"[cyan]{n} days 🔥[/]"
    return f"[green]{n} days 🔥🔥[/]"


def goal_bar(pct: float, width: int = 16) -> str:
    """Plain-text progress bar in Rich markup."""
    filled = round(pct * width)
    bar    = "█" * filled + "░" * (width - filled)
    color  = "green" if pct >= 1.0 else "cyan" if pct >= 0.5 else "yellow"
    return f"[{color}]{bar}[/]"