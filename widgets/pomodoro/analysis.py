"""
widgets/pomodoro/analysis.py
─────────────────────────────
Analysis tab for the Pomodoro screen.

Layout:
┌────────────────────────────────────────────────────────────┐
│  [Completion %]  [Avg Efficiency]  [Avg Length]  [Total]   │  ← StatRow
├──────────────────────────┬─────────────────────────────────┤
│  SubjectBreakdown        │  PeakHours                      │
│  (progress bars)         │  (hour bars, active hours only) │
├──────────────────────────┴─────────────────────────────────┤
│  SessionQuality  (full DataTable — planned/actual/paused)  │
└────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Label, ProgressBar, Static

from services.pomodoroService import PomodoroService, fmt_mins


# ─── Stat Card ───────────────────────────────────────────────────────────────

class AnalysisStatCard(Widget):
    """Small labelled stat card for the top row."""

    DEFAULT_CSS = """
    AnalysisStatCard {
        border: round;
        padding: 0 1;
        width: 1fr;
        height: 7;
    }
    AnalysisStatCard .card-value { text-style: bold; }
    AnalysisStatCard .card-sub   { color: $text-muted; }

    AnalysisStatCard.completion { border: round $success; }
    AnalysisStatCard.completion .card-value { color: $success; }

    AnalysisStatCard.efficiency { border: round $accent; }
    AnalysisStatCard.efficiency .card-value { color: $accent; }

    AnalysisStatCard.length     { border: round $primary; }
    AnalysisStatCard.length     .card-value { color: $primary; }

    AnalysisStatCard.total      { border: round $warning; }
    AnalysisStatCard.total      .card-value { color: $warning; }
    """

    def __init__(self, label: str, value: str, sub: str,
                 variant: str = "completion", **kwargs) -> None:
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


# ─── Subject Breakdown ────────────────────────────────────────────────────────

class SubjectBreakdown(Widget):
    """Horizontal progress bars — one per subject with focus minutes."""

    DEFAULT_CSS = """
    SubjectBreakdown {
        border: round $primary;
        width: 1fr;
        height: 1fr;
    }
    SubjectBreakdown VerticalScroll { padding: 1 2; height: 1fr; }
    SubjectBreakdown .sb-header     { color: $text-muted; margin-bottom: 1; }
    SubjectBreakdown .sb-row        { height: 1; margin-bottom: 1; }
    SubjectBreakdown .sb-label      { width: 10; }
    SubjectBreakdown .sb-time       { width: 9; text-align: right; color: $text-muted; }
    SubjectBreakdown ProgressBar    { width: 1fr; }
    SubjectBreakdown .sb-empty      { color: $text-muted; }
    """

    def __init__(self, *, service: PomodoroService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        self.border_title    = "Subject Breakdown"
        self.border_subtitle = "total focus minutes"
        with VerticalScroll():
            yield Static("[dim]Subject breakdown — loading…[/]",
                         classes="sb-empty", id="sb-content", markup=True)

    def on_mount(self) -> None:
        self._fill()

    def _fill(self) -> None:
        scroll = self.query_one(VerticalScroll)

        # Remove old rows
        for old in scroll.query(".sb-row"):
            old.remove()
        for old in scroll.query(".sb-empty"):
            old.remove()

        data = self._svc.sessions_by_subject()
        if not data:
            scroll.mount(Static("[dim]No sessions yet.[/]",
                                classes="sb-empty", markup=True))
            return

        max_mins = max(data.values()) or 1
        total    = sum(data.values())
        self.border_subtitle = f"{fmt_mins(total)} total"

        for subject, mins in sorted(data.items(), key=lambda x: -x[1]):
            pct    = mins / total * 100
            row    = Horizontal(classes="sb-row")
            label  = Label(subject[:9], classes="sb-label")
            bar    = ProgressBar(total=max_mins, show_eta=False, show_percentage=False)
            time_l = Label(f"[dim]{mins}m ({pct:.0f}%)[/]",
                           markup=True, classes="sb-time")
            scroll.mount(row)
            row.mount(label, bar, time_l)
            bar.progress = mins

    def refresh_data(self) -> None:
        self._fill()


# ─── Peak Hours ───────────────────────────────────────────────────────────────

class PeakHours(Widget):
    """Shows which hours of day the user is most productive."""

    DEFAULT_CSS = """
    PeakHours {
        border: round $accent;
        width: 1fr;
        height: 1fr;
    }
    PeakHours VerticalScroll { padding: 1 2; height: 1fr; }
    PeakHours .ph-row        { height: 1; margin-bottom: 1; }
    PeakHours .ph-label      { width: 8; }
    PeakHours .ph-time       { width: 9; text-align: right; color: $text-muted; }
    PeakHours ProgressBar    { width: 1fr; }
    PeakHours .ph-empty      { color: $text-muted; }
    PeakHours .ph-peak       { color: $warning; text-style: bold; }
    """

    HOUR_LABELS = {
        0: "12am", 1: "1am",  2: "2am",  3: "3am",
        4: "4am",  5: "5am",  6: "6am",  7: "7am",
        8: "8am",  9: "9am",  10: "10am", 11: "11am",
        12: "12pm", 13: "1pm", 14: "2pm",  15: "3pm",
        16: "4pm",  17: "5pm", 18: "6pm",  19: "7pm",
        20: "8pm",  21: "9pm", 22: "10pm", 23: "11pm",
    }

    def __init__(self, *, service: PomodoroService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        self.border_title    = "Peak Hours"
        self.border_subtitle = "focus minutes by hour"
        with VerticalScroll():
            yield Static("[dim]Loading…[/]", classes="ph-empty",
                         id="ph-content", markup=True)

    def on_mount(self) -> None:
        self._fill()

    def _fill(self) -> None:
        scroll = self.query_one(VerticalScroll)

        for old in scroll.query(".ph-row"):
            old.remove()
        for old in scroll.query(".ph-empty"):
            old.remove()

        data = self._svc.sessions_by_hour()
        if not data:
            scroll.mount(Static("[dim]No sessions yet.[/]",
                                classes="ph-empty", markup=True))
            return

        max_mins = max(data.values()) or 1
        peak_hr  = max(data, key=data.__getitem__)
        self.border_subtitle = f"peak at {self.HOUR_LABELS[peak_hr]}"

        # Only show hours that have activity
        for hour in sorted(data.keys()):
            mins    = data[hour]
            is_peak = (hour == peak_hr)
            label_str = self.HOUR_LABELS[hour]

            row    = Horizontal(classes="ph-row")
            label  = Label(
                f"[yellow][bold]{label_str}[/bold][/]" if is_peak else f"[dim]{label_str}[/]",
                markup=True, classes="ph-label",
            )
            bar    = ProgressBar(total=max_mins, show_eta=False, show_percentage=False)
            time_l = Label(
                f"[yellow]{mins}m[/]" if is_peak else f"[dim]{mins}m[/]",
                markup=True, classes="ph-time",
            )
            scroll.mount(row)
            row.mount(label, bar, time_l)
            bar.progress = mins

    def refresh_data(self) -> None:
        self._fill()


# ─── Session Quality ──────────────────────────────────────────────────────────

class SessionQuality(Widget):
    """
    DataTable comparing planned vs actual duration, pause time, and
    efficiency for every Focus session.
    """

    DEFAULT_CSS = """
    SessionQuality {
        border: round $warning;
        width: 100%;
        height: 1fr;
    }
    SessionQuality DataTable { height: 1fr; background: transparent; }
    """

    def __init__(self, *, service: PomodoroService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        self.border_title    = "Session Quality"
        self.border_subtitle = "planned vs actual · pause time · efficiency"
        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(
            "Date", "Start", "End", "Subject",
            "Planned", "Actual", "Paused", "Efficiency", "✓"
        )
        table.cursor_type = "row"
        self._fill()

    def _fill(self) -> None:
        table    = self.query_one(DataTable)
        sessions = self._svc.recent_focus(50)
        table.clear()

        for s in reversed(sessions):
            done     = "[green]✓[/]" if s.completed else "[red]✗[/]"
            eff      = s.focus_efficiency * 100
            paused_m = s.paused_seconds // 60
            paused_s = s.paused_seconds % 60

            # colour efficiency
            if eff >= 90:
                eff_str = f"[green]{eff:.0f}%[/]"
            elif eff >= 70:
                eff_str = f"[cyan]{eff:.0f}%[/]"
            elif eff >= 50:
                eff_str = f"[yellow]{eff:.0f}%[/]"
            else:
                eff_str = f"[red]{eff:.0f}%[/]"

            paused_str = (
                f"[red]{paused_m}m {paused_s:02d}s[/]"
                if s.paused_seconds > 60
                else f"[dim]{paused_m}m {paused_s:02d}s[/]"
            )

            table.add_row(
                f"[dim]{s.display_date}[/]",
                f"[dim]{s.start}[/]",
                f"[dim]{s.end}[/]",
                s.subject,
                f"[dim]{s.duration_planned}m[/]",
                f"[cyan]{s.duration_actual}m[/]",
                paused_str,
                eff_str,
                done,
            )

        count = len(self._svc.recent_focus(9999))
        self.border_subtitle = (
            f"last 50 of {count}  ·  planned vs actual · pause · efficiency"
        )

    def refresh_data(self) -> None:
        self._fill()


# ─── PomodoroAnalysis (composite) ────────────────────────────────────────────

class PomodoroAnalysis(Widget):
    """
    Full analysis panel.

    ┌──────────────────────────────────────────────┐
    │  [Completion]  [Efficiency]  [Avg Len]  [Tot]│
    ├──────────────────┬───────────────────────────┤
    │  SubjectBreakdown│  PeakHours               │
    ├──────────────────┴───────────────────────────┤
    │  SessionQuality                              │
    └──────────────────────────────────────────────┘
    """

    DEFAULT_CSS = """
    PomodoroAnalysis {
        width: 100%;
        height: 1fr;
        padding: 1 2;
    }
    .ana-stat-row   { height: 7;   width: 100%; }
    .ana-mid-row    { width: 100%; height: 1fr; }
    .ana-bottom-row { width: 100%; height: 1fr; }
    """

    def __init__(self, *, service: PomodoroService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def _get_stats(self) -> dict:
        focus = [s for s in self._svc.sessions
                 if s.type == "Focus" and s.completed]
        total_sessions = len(focus)
        total_mins     = sum(s.duration_actual for s in focus)
        avg_len        = (total_mins // total_sessions) if total_sessions else 0
        completion     = self._svc.completion_rate()
        efficiency     = self._svc.avg_efficiency()

        return dict(
            completion = f"[bold]{completion:.1f}%[/]",
            comp_sub   = f"{sum(1 for s in focus if s.completed)} of "
                         f"{len([s for s in self._svc.sessions if s.type == 'Focus'])} sessions",
            efficiency = f"[bold]{efficiency:.1f}%[/]",
            eff_sub    = "net focus / planned time",
            avg_len    = f"[bold]{avg_len}m[/]",
            avg_sub    = f"{total_sessions} sessions logged",
            total      = fmt_mins(total_mins),
            total_sub  = f"across all time",
        )

    def compose(self) -> ComposeResult:
        v = self._get_stats()

        with Horizontal(classes="ana-stat-row"):
            yield AnalysisStatCard(
                "Completion Rate", v["completion"], v["comp_sub"],
                "completion", id="ana-card-completion"
            )
            yield AnalysisStatCard(
                "Avg Efficiency", v["efficiency"], v["eff_sub"],
                "efficiency", id="ana-card-efficiency"
            )
            yield AnalysisStatCard(
                "Avg Session", v["avg_len"], v["avg_sub"],
                "length", id="ana-card-length"
            )
            yield AnalysisStatCard(
                "Total Focus", v["total"], v["total_sub"],
                "total", id="ana-card-total"
            )

        with Horizontal(classes="ana-mid-row"):
            yield SubjectBreakdown(service=self._svc, id="ana-subjects")
            yield PeakHours(service=self._svc,       id="ana-hours")

        with Horizontal(classes="ana-bottom-row"):
            yield SessionQuality(service=self._svc,  id="ana-quality")

    def refresh_data(self) -> None:
        v = self._get_stats()

        self.query_one("#ana-card-completion", AnalysisStatCard).set_content(
            v["completion"], v["comp_sub"])
        self.query_one("#ana-card-efficiency", AnalysisStatCard).set_content(
            v["efficiency"], v["eff_sub"])
        self.query_one("#ana-card-length", AnalysisStatCard).set_content(
            v["avg_len"], v["avg_sub"])
        self.query_one("#ana-card-total", AnalysisStatCard).set_content(
            v["total"], v["total_sub"])

        self.query_one("#ana-subjects", SubjectBreakdown).refresh_data()
        self.query_one("#ana-hours",    PeakHours).refresh_data()
        self.query_one("#ana-quality",  SessionQuality).refresh_data()