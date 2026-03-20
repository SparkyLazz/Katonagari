"""
pomodoroService.py
──────────────────
Single source of truth for all Pomodoro/study session data.
Backed by  databases/pomodoro.json

New JSON structure:
  settings  — user config (daily goal, durations, subjects)
  db        — internal bookkeeping (version, next_id)
  sessions  — flat array of session records
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────

DATA_FILE: Path = Path(__file__).resolve().parent.parent / "databases" / "pomodoro.json"

# ─── Constants ───────────────────────────────────────────────────────────────

SESSION_TYPES: list[str] = ["Focus", "Short Break", "Long Break"]
DAYS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ─── Models ──────────────────────────────────────────────────────────────────

@dataclass
class Session:
    """One Pomodoro session record — maps 1-to-1 with the JSON schema."""

    id:                int
    date:              str    # "2026-03-20"
    start:             str    # "09:00"
    end:               str    # "09:25"
    duration_planned:  int    # minutes set on timer
    duration_actual:   int    # minutes actually elapsed
    paused_seconds:    int    # total seconds spent paused
    type:              str    # "Focus" | "Short Break" | "Long Break"
    subject:           str    # e.g. "Coding"
    completed:         bool   = True
    notes:             str    = ""

    # ── backward-compat alias ─────────────────────────────────────────────────
    @property
    def duration(self) -> int:
        """Alias for duration_actual — keeps existing widgets working."""
        return self.duration_actual

    # ── display helpers ───────────────────────────────────────────────────────
    @property
    def display_date(self) -> str:
        return datetime.strptime(self.date, "%Y-%m-%d").strftime("%b %d")

    @property
    def display_duration(self) -> str:
        h, m = divmod(self.duration_actual, 60)
        return f"{h}h {m:02d}m" if h else f"{m}m"

    @property
    def focus_efficiency(self) -> float:
        """Ratio of actual focus time to planned time (0.0–1.0)."""
        if self.duration_planned == 0:
            return 0.0
        net_seconds = self.duration_actual * 60 - self.paused_seconds
        return max(0.0, min(1.0, net_seconds / (self.duration_planned * 60)))

    @property
    def sort_key(self) -> str:
        return f"{self.date} {self.start}"

    def to_dict(self) -> dict:
        d = {
            "id":               self.id,
            "date":             self.date,
            "start":            self.start,
            "end":              self.end,
            "duration_planned": self.duration_planned,
            "duration_actual":  self.duration_actual,
            "paused_seconds":   self.paused_seconds,
            "type":             self.type,
            "subject":          self.subject,
            "completed":        self.completed,
        }
        if self.notes:                  # omit empty notes to keep JSON clean
            d["notes"] = self.notes
        return d


@dataclass
class DaySummary:
    date:           str
    label:          str
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
    today_focus:       int
    today_sessions:    int
    today_goal:        int
    streak:            int
    week_focus:        int
    week_sessions:     int
    best_day_label:    str
    best_day_mins:     int
    all_time_mins:     int
    all_time_sessions: int
    week_days:         list[DaySummary]


# ─── Service ─────────────────────────────────────────────────────────────────

class PomodoroService:
    """
    Loads databases/pomodoro.json, exposes typed session list,
    persists mutations, and computes all derived values needed by widgets.
    """

    def __init__(self, data_file: Path = DATA_FILE) -> None:
        self._file = data_file
        self._raw:      dict          = self._load()
        self._sessions: list[Session] = []
        self._rebuild()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._file.exists():
            with open(self._file, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return self._default_structure()

    @staticmethod
    def _default_structure() -> dict:
        return {
            "settings": {
                "daily_goal_minutes": 120,
                "durations": {"focus": 25, "short_break": 5, "long_break": 15},
                "subjects": ["Coding", "Math", "Physics", "Reading", "Writing", "Language", "Other"],
            },
            "db": {
                "version": 1,
                "created": date.today().isoformat(),
                "next_id": 1,
            },
            "sessions": [],
        }

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file, "w", encoding="utf-8") as fh:
            json.dump(self._raw, fh, indent=2)

    def _rebuild(self) -> None:
        """Parse raw JSON into typed Session objects, sorted chronologically."""
        raw_sessions = self._raw.get("sessions", [])
        parsed = []
        for s in raw_sessions:
            # Skip example/comment records
            if "_comment" in s:
                continue
            parsed.append(Session(
                id               = s.get("id", 0),
                date             = s["date"],
                start            = s["start"],
                end              = s.get("end", ""),
                duration_planned = s.get("duration_planned", s.get("duration", 25)),
                duration_actual  = s.get("duration_actual",  s.get("duration", 25)),
                paused_seconds   = s.get("paused_seconds", 0),
                type             = s["type"],
                subject          = s["subject"],
                completed        = s.get("completed", True),
                notes            = s.get("notes", ""),
            ))
        self._sessions = sorted(parsed, key=lambda s: s.sort_key)

    # ── Settings accessors ────────────────────────────────────────────────────

    @property
    def daily_goal(self) -> int:
        return self._raw.get("settings", {}).get("daily_goal_minutes", 120)

    @property
    def focus_duration(self) -> int:
        return self._raw.get("settings", {}).get("durations", {}).get("focus", 25)

    @property
    def subjects(self) -> list[str]:
        return self._raw.get("settings", {}).get(
            "subjects",
            ["Coding", "Math", "Physics", "Reading", "Writing", "Language", "Other"],
        )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    @property
    def sessions(self) -> list[Session]:
        return list(self._sessions)

    def add(self, s: Session) -> Session:
        """Assign a fresh id, append to JSON, persist."""
        db = self._raw.setdefault("db", {"version": 1, "next_id": 1})
        s.id = db.get("next_id", 1)
        db["next_id"] = s.id + 1

        self._raw.setdefault("sessions", []).append(s.to_dict())
        self._rebuild()
        self._save()
        return s

    def remove(self, session_id: int) -> Session | None:
        """Remove by id — safe even if dates/times collide."""
        target = next((s for s in self._sessions if s.id == session_id), None)
        if target is None:
            return None
        self._raw["sessions"] = [
            r for r in self._raw["sessions"] if r.get("id") != session_id
        ]
        self._rebuild()
        self._save()
        return target

    # ── Derived: per-date index ───────────────────────────────────────────────

    def _focus_by_date(self) -> dict[str, int]:
        """date_str → total actual focus minutes."""
        result: dict[str, int] = {}
        for s in self._sessions:
            if s.type == "Focus" and s.completed:
                result[s.date] = result.get(s.date, 0) + s.duration_actual
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
        today  = date.today()
        monday = today - timedelta(days=today.weekday())
        goal   = self.daily_goal

        summaries = []
        for i, label in enumerate(DAYS_SHORT):
            day_date = monday + timedelta(days=i)
            iso      = day_date.isoformat()
            focus_m  = sum(
                s.duration_actual for s in self._sessions
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
        today_focus   = sum(s.duration_actual for s in today_sessions)
        week_focus    = sum(d.focus_minutes for d in week_days)
        week_sessions = sum(d.sessions      for d in week_days)

        fbd = self._focus_by_date()
        if fbd:
            best_iso   = max(fbd, key=fbd.__getitem__)
            best_mins  = fbd[best_iso]
            best_label = datetime.strptime(best_iso, "%Y-%m-%d").strftime("%b %d")
        else:
            best_label, best_mins = "─", 0

        all_focus = [s for s in self._sessions if s.type == "Focus" and s.completed]

        return OverviewStats(
            today_focus       = today_focus,
            today_sessions    = len(today_sessions),
            today_goal        = self.daily_goal,
            streak            = self._streak(),
            week_focus        = week_focus,
            week_sessions     = week_sessions,
            best_day_label    = best_label,
            best_day_mins     = best_mins,
            all_time_mins     = sum(s.duration_actual for s in all_focus),
            all_time_sessions = len(all_focus),
            week_days         = week_days,
        )

    # ── Recent sessions ───────────────────────────────────────────────────────

    def recent_focus(self, n: int = 10) -> list[Session]:
        focus = [s for s in self._sessions if s.type == "Focus"]
        return focus[-n:]

    # ── Analysis helpers (new) ────────────────────────────────────────────────

    def completion_rate(self) -> float:
        """% of Focus sessions that completed fully."""
        focus = [s for s in self._sessions if s.type == "Focus"]
        if not focus:
            return 0.0
        return sum(1 for s in focus if s.completed) / len(focus) * 100

    def avg_efficiency(self) -> float:
        """Average focus efficiency across all completed Focus sessions."""
        focus = [s for s in self._sessions if s.type == "Focus" and s.completed]
        if not focus:
            return 0.0
        return sum(s.focus_efficiency for s in focus) / len(focus) * 100

    def sessions_by_subject(self) -> dict[str, int]:
        """subject → total actual focus minutes."""
        result: dict[str, int] = {}
        for s in self._sessions:
            if s.type == "Focus" and s.completed:
                result[s.subject] = result.get(s.subject, 0) + s.duration_actual
        return result

    def sessions_by_hour(self) -> dict[int, int]:
        """hour (0–23) → total focus minutes, for productivity-by-hour chart."""
        result: dict[int, int] = {}
        for s in self._sessions:
            if s.type == "Focus" and s.completed and s.start:
                try:
                    hour = int(s.start.split(":")[0])
                    result[hour] = result.get(hour, 0) + s.duration_actual
                except ValueError:
                    pass
        return result


# ─── Formatting helpers (unchanged) ──────────────────────────────────────────

def fmt_mins(minutes: int) -> str:
    if minutes == 0:
        return "[dim]─[/]"
    h, m = divmod(minutes, 60)
    if h:
        return f"[bold]{h}[/]h [bold]{m:02d}[/]m"
    return f"[bold]{m}[/]m"


def fmt_streak(n: int) -> str:
    if n == 0: return "[dim]─[/]"
    if n < 3:  return f"[yellow]{n} day{'s' if n > 1 else ''}[/]"
    if n < 7:  return f"[cyan]{n} days 🔥[/]"
    return f"[green]{n} days 🔥🔥[/]"


def goal_bar(pct: float, width: int = 16) -> str:
    filled = round(pct * width)
    bar    = "█" * filled + "░" * (width - filled)
    color  = "green" if pct >= 1.0 else "cyan" if pct >= 0.5 else "yellow"
    return f"[{color}]{bar}[/]"