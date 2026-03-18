"""
widgets/pomodoro/overview.py
─────────────────────────────
Overview panel for the Pomodoro screen.

Layout:
┌──────────────────────────────────────────────────┐
│  [Today Focus] [Sessions] [Streak] [Week Total]  │  ← StatRow (4 cards)
├────────────────────────┬─────────────────────────┤
│   WeeklyHeatmap        │  RecentSessions          │  ← BottomRow
│  (Mon–Sun bars +       │  (DataTable last 10)     │
│   today goal ring)     │                          │
└────────────────────────┴─────────────────────────┘
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable, Label, ProgressBar, Static

from services.pomodoroService import (
    OverviewStats,
    PomodoroService,
    fmt_mins,
    fmt_streak,
    goal_bar,
)


# ─── StatCard ─────────────────────────────────────────────────────────────────

class PomStatCard(Widget):
    """A labelled stat card with a primary value and a secondary diff line."""

    DEFAULT_CSS = """
    PomStatCard {
        border: round;
        padding: 0 1;
        width: 1fr;
        height: 7;
    }
    PomStatCard .card-value { text-style: bold; }
    PomStatCard .card-sub   { color: $text-muted; }
    PomStatCard.focus  { border: round $accent;   }
    PomStatCard.session{ border: round $primary;  }
    PomStatCard.streak { border: round $warning;  }
    PomStatCard.week   { border: round $success;  }
    PomStatCard.focus   .card-value { color: $accent;   }
    PomStatCard.session .card-value { color: $primary;  }
    PomStatCard.streak  .card-value { color: $warning;  }
    PomStatCard.week    .card-value { color: $success;  }
    """

    def __init__(self, label: str, value: str, sub: str,
                 variant: str = "focus", **kwargs) -> None:
        super().__init__(**kwargs)
        self._label   = label
        self._value   = value
        self._sub     = sub
        self._variant = variant

    def on_mount(self) -> None:
        self.border_title = self._label
        self.add_class(self._variant)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._value, classes="card-value", id=f"val-{self.id}", markup=True)
            yield Label(self._sub,    classes="card-sub",   id=f"sub-{self.id}", markup=True)

    def set_content(self, value: str, sub: str) -> None:
        self.query_one(f"#val-{self.id}", Static).update(value)
        self.query_one(f"#sub-{self.id}", Label).update(sub)


# ─── TodayGoalPanel ───────────────────────────────────────────────────────────

class TodayGoalPanel(Widget):
    """Shows today's goal progress bar + goal metadata."""

    DEFAULT_CSS = """
    TodayGoalPanel {
        border: round $accent;
        width: 28;
        height: 1fr;
        padding: 1 2;
    }
    TodayGoalPanel #goal-label   { color: $text-muted; margin-bottom: 1; }
    TodayGoalPanel #goal-value   { text-style: bold; color: $accent; }
    TodayGoalPanel #goal-bar     { margin: 1 0; }
    TodayGoalPanel #goal-pct     { color: $text-muted; }
    TodayGoalPanel .divider      { color: $primary; }
    TodayGoalPanel .row          { height: 1; margin-bottom: 1; }
    TodayGoalPanel .row-label    { color: $text-muted; width: 12; }
    TodayGoalPanel .row-value    { text-style: bold; }
    """

    def __init__(self, *, stats: OverviewStats, **kwargs) -> None:
        super().__init__(**kwargs)
        self._stats = stats

    def compose(self) -> ComposeResult:
        self.border_title = "Today"
        s   = self._stats
        pct = min(s.today_focus / s.today_goal, 1.0) if s.today_goal else 0.0
        h, m = divmod(s.today_focus, 60)

        yield Label("Daily Goal", id="goal-label")
        yield Static(
            f"[bold]{h}h {m:02d}m[/]" if h else f"[bold]{m}m[/]" if m else "[dim]Not started[/]",
            id="goal-value", markup=True,
        )
        yield Static(goal_bar(pct), id="goal-bar", markup=True)
        yield Label(
            f"[dim]{s.today_focus}[/] / [dim]{s.today_goal}[/] min  ({pct*100:.0f}%)",
            id="goal-pct", markup=True,
        )

        yield Static("─" * 20, classes="divider")

        with Horizontal(classes="row"):
            yield Label("Sessions",  classes="row-label")
            yield Static(str(s.today_sessions), classes="row-value accent",  id="td-sessions")
        with Horizontal(classes="row"):
            yield Label("Streak",    classes="row-label")
            yield Static(fmt_streak(s.streak),  classes="row-value warning", id="td-streak",
                         markup=True)
        with Horizontal(classes="row"):
            yield Label("This week", classes="row-label")
            yield Static(fmt_mins(s.week_focus), classes="row-value success", id="td-week",
                         markup=True)

        yield Static("─" * 20, classes="divider")

        with Horizontal(classes="row"):
            yield Label("Best day",  classes="row-label")
            yield Static(
                f"[dim]{s.best_day_label}[/]  [bold]{s.best_day_mins}m[/]",
                classes="row-value", id="td-best", markup=True,
            )
        with Horizontal(classes="row"):
            yield Label("All time",  classes="row-label")
            h2, m2 = divmod(s.all_time_mins, 60)
            yield Static(
                f"[bold]{h2}h {m2:02d}m[/]" if h2 else f"[bold]{m2}m[/]",
                classes="row-value", id="td-alltime", markup=True,
            )

    def refresh_data(self, stats: OverviewStats) -> None:
        self._stats = stats
        s   = stats
        pct = min(s.today_focus / s.today_goal, 1.0) if s.today_goal else 0.0
        h, m = divmod(s.today_focus, 60)

        self.query_one("#goal-value", Static).update(
            f"[bold]{h}h {m:02d}m[/]" if h else f"[bold]{m}m[/]" if m else "[dim]Not started[/]"
        )
        self.query_one("#goal-bar",   Static).update(goal_bar(pct))
        self.query_one("#goal-pct",   Label).update(
            f"[dim]{s.today_focus}[/] / [dim]{s.today_goal}[/] min  ({pct*100:.0f}%)"
        )
        self.query_one("#td-sessions", Static).update(str(s.today_sessions))
        self.query_one("#td-streak",   Static).update(fmt_streak(s.streak))
        self.query_one("#td-week",     Static).update(fmt_mins(s.week_focus))
        h2, m2 = divmod(s.all_time_mins, 60)
        self.query_one("#td-best",    Static).update(
            f"[dim]{s.best_day_label}[/]  [bold]{s.best_day_mins}m[/]"
        )
        self.query_one("#td-alltime", Static).update(
            f"[bold]{h2}h {m2:02d}m[/]" if h2 else f"[bold]{m2}m[/]"
        )


# ─── WeeklyHeatmap ────────────────────────────────────────────────────────────

class WeeklyHeatmap(Widget):
    """Mon–Sun horizontal bar chart showing focus minutes vs. daily goal."""

    DEFAULT_CSS = """
    WeeklyHeatmap {
        border: round $primary;
        width: 1fr;
        height: 1fr;
    }
    WeeklyHeatmap VerticalScroll { padding: 1 2; height: 1fr; }
    WeeklyHeatmap .week-header   { color: $text-muted; margin-bottom: 1; }
    WeeklyHeatmap .day-row       { height: 1; margin-bottom: 1; }
    WeeklyHeatmap .day-label     { width: 5; }
    WeeklyHeatmap .day-time      { width: 8; text-align: right; color: $text-muted; }
    WeeklyHeatmap ProgressBar    { width: 1fr; }
    WeeklyHeatmap .week-footer   { color: $text-muted; margin-top: 1; }
    """

    def __init__(self, *, stats: OverviewStats, **kwargs) -> None:
        super().__init__(**kwargs)
        self._stats = stats

    def compose(self) -> ComposeResult:
        self.border_title    = "This Week"
        self.border_subtitle = f"Goal: {self._stats.today_goal} min/day"
        with VerticalScroll():
            yield Static("[dim]Mon  Tue  Wed  Thu  Fri  Sat  Sun[/]",
                         classes="week-header", markup=True)
            yield self._build_bars()
            yield Static(
                f"[dim]Total:[/] {fmt_mins(self._stats.week_focus)}  "
                f"[dim]Sessions:[/] [bold]{self._stats.week_sessions}[/]",
                classes="week-footer", markup=True,
            )

    def _build_bars(self) -> Widget:
        """Return a Vertical containing one row per day."""
        container = Vertical()
        return container

    def on_mount(self) -> None:
        self._fill_bars()

    def _fill_bars(self) -> None:
        """Populate or refresh the bar rows inside the VerticalScroll."""
        today_iso  = self._stats.week_days[0].date  # recalculate
        from datetime import date as _date
        today_iso  = _date.today().isoformat()

        scroll = self.query_one(VerticalScroll)
        # Remove old bar rows before rebuilding
        for old in scroll.query(".day-row"):
            old.remove()

        goal = self._stats.today_goal or 1
        for ds in self._stats.week_days:
            is_today = ds.date == today_iso
            pct      = ds.goal_pct

            day_widget = Horizontal(classes="day-row")
            day_lbl    = Label(
                f"[yellow][bold]{ds.label}[/bold][/]" if is_today else f"[dim]{ds.label}[/]",
                markup=True, classes="day-label",
            )
            bar        = ProgressBar(total=goal, show_eta=False, show_percentage=False)
            time_lbl   = Label(
                f"[yellow]{ds.display_time}[/]" if is_today else f"[dim]{ds.display_time}[/]",
                markup=True, classes="day-time",
            )
            day_widget._nodes_to_add = [day_lbl, bar, time_lbl]  # compose trick
            scroll.mount(day_widget)

        # Set progress values after mounting
        from textual.widgets import ProgressBar as PB
        bars = list(scroll.query(PB))
        for bar, ds in zip(bars, self._stats.week_days):
            bar.progress = ds.focus_minutes

    def refresh_data(self, stats: OverviewStats) -> None:
        self._stats = stats
        self.border_subtitle = f"Goal: {stats.today_goal} min/day"
        self._fill_bars()
        footer = self.query(".week-footer")
        if footer:
            footer.first(Static).update(
                f"[dim]Total:[/] {fmt_mins(stats.week_focus)}  "
                f"[dim]Sessions:[/] [bold]{stats.week_sessions}[/]"
            )


# ─── RecentSessions ───────────────────────────────────────────────────────────

class RecentSessions(Widget):
    """DataTable showing the 10 most recent focus sessions."""

    DEFAULT_CSS = """
    RecentSessions {
        border: round $warning;
        width: 1fr;
        height: 1fr;
    }
    RecentSessions DataTable { height: 1fr; background: transparent; }
    """

    def __init__(self, *, service: PomodoroService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        self.border_title    = "Recent Sessions"
        self.border_subtitle = "latest 10 focus blocks"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Date", "Start", "Subject", "Duration", "✓")
        table.cursor_type = "row"
        self._fill()

    def _fill(self) -> None:
        table    = self.query_one(DataTable)
        sessions = self._svc.recent_focus(10)
        table.clear()
        for s in reversed(sessions):  # newest first
            done = "[green]✓[/]" if s.completed else "[red]✗[/]"
            table.add_row(
                f"[dim]{s.display_date}[/]",
                f"[dim]{s.start}[/]",
                s.subject,
                f"[cyan]{s.duration}m[/]",
                done,
            )
        count = len(self._svc.recent_focus(999))
        self.border_subtitle = f"latest 10  ·  {count} total"

    def refresh_data(self) -> None:
        self._fill()


# ─── PomodoroOverview (composite) ─────────────────────────────────────────────

class PomodoroOverview(Widget):
    """
    Full overview panel.

    ┌──────────────────────────────────────────────┐
    │  [Today Focus] [Sessions] [Streak] [Week]    │
    ├──────────────────────┬───────────────────────┤
    │ TodayGoalPanel (28w) │ WeeklyHeatmap (1fr)   │
    │                      ├───────────────────────┤
    │                      │ RecentSessions (1fr)  │
    └──────────────────────┴───────────────────────┘
    """

    class DataChanged(Message):
        """Broadcast whenever session data is mutated externally."""

    DEFAULT_CSS = """
    PomodoroOverview {
        width: 100%;
        height: 1fr;
        padding: 1 2;
    }
    .pom-stat-row  { height: 7;   width: 100%; }
    .pom-main-row  { width: 100%; height: 1fr; }
    .pom-right-col { width: 1fr;  height: 1fr; }
    """

    def __init__(self, *, service: PomodoroService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def _get_stats(self) -> dict:
        s = self._svc.overview_stats()
        h, m = divmod(s.today_focus, 60)
        wh, wm = divmod(s.week_focus, 60)
        return dict(
            stats  = s,
            today  = f"[bold]{h}h {m:02d}m[/]" if h else f"[bold]{m}m[/]" if m else "[dim]0m[/]",
            today_sub = f"{s.today_sessions} session{'s' if s.today_sessions != 1 else ''}  ·  goal {s.today_goal}m",
            sess   = str(s.today_sessions),
            sess_sub = f"{s.week_sessions} this week",
            streak = fmt_streak(s.streak),
            streak_sub = "consecutive days",
            week   = f"[bold]{wh}h {wm:02d}m[/]" if wh else f"[bold]{wm}m[/]" if wm else "[dim]0m[/]",
            week_sub = f"{s.week_sessions} sessions  Mon–Sun",
        )

    def compose(self) -> ComposeResult:
        v = self._get_stats()
        s = v["stats"]

        with Horizontal(classes="pom-stat-row"):
            yield PomStatCard("Today Focus", v["today"],   v["today_sub"],  "focus",   id="card-today")
            yield PomStatCard("Sessions",    v["sess"],    v["sess_sub"],   "session", id="card-sessions")
            yield PomStatCard("Streak",      v["streak"],  v["streak_sub"], "streak",  id="card-streak")
            yield PomStatCard("Week Total",  v["week"],    v["week_sub"],   "week",    id="card-week")

        with Horizontal(classes="pom-main-row"):
            yield TodayGoalPanel(stats=s, id="goal-panel")
            with Vertical(classes="pom-right-col"):
                yield WeeklyHeatmap(stats=s,         id="weekly-heatmap")
                yield RecentSessions(service=self._svc, id="recent-sessions")

    def refresh_data(self) -> None:
        v = self._get_stats()
        s = v["stats"]

        self.query_one("#card-today",    PomStatCard).set_content(v["today"],  v["today_sub"])
        self.query_one("#card-sessions", PomStatCard).set_content(v["sess"],   v["sess_sub"])
        self.query_one("#card-streak",   PomStatCard).set_content(v["streak"], v["streak_sub"])
        self.query_one("#card-week",     PomStatCard).set_content(v["week"],   v["week_sub"])

        self.query_one("#goal-panel",     TodayGoalPanel).refresh_data(s)
        self.query_one("#weekly-heatmap", WeeklyHeatmap).refresh_data(s)
        self.query_one("#recent-sessions", RecentSessions).refresh_data()

    def on_pomodoro_overview_data_changed(self, _: DataChanged) -> None:
        self.refresh_data()