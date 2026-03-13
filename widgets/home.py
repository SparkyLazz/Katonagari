"""
home.py — Home tab widget.
ScheduleBox rows are clickable: clicking one posts SwitchToSchedule
so Dashboard can jump to the Schedule tab.
"""
from __future__ import annotations

import platform
import psutil
from datetime import date, datetime

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Static

from databases.scheduleData import  (
    CATEGORY_COLOR, CATEGORY_ICON, PRIORITY,
    get_events_for_date, load_events,
)


# ──────────────────────────────────────────────────────────────────────────────
# Cross-widget message
# ──────────────────────────────────────────────────────────────────────────────

class SwitchToSchedule(Message):
    """Post to make Dashboard switch to the Schedule tab."""
    def __init__(self, target_date: date) -> None:
        super().__init__()
        self.target_date = target_date


# ──────────────────────────────────────────────────────────────────────────────
# StatisticBox
# ──────────────────────────────────────────────────────────────────────────────

class StatisticBox(Vertical):
    DEFAULT_CSS = """
    StatisticBox {
        height: auto;
        border: round $primary;
        row-span: 2;
        padding: 0 2;
    }
    StatisticBox Label          { width: 100%; margin-top: 0; color: $text-muted; }
    StatisticBox Label.section  { color: $primary; text-style: bold; margin-top: 1; }
    StatisticBox Label.info     { color: $text; }
    StatisticBox ProgressBar    { width: 100%; margin-bottom: 0; }

    #cpu-label { color: $success; }
    #ram-label { color: $warning; }
    #swp-label { color: $error; }
    #dsk-label { color: $accent; }

    #cpu-bar > .bar--bar { color: $success; }
    #ram-bar > .bar--bar { color: $warning; }
    #swp-bar > .bar--bar { color: $error; }
    #dsk-bar > .bar--bar { color: $accent; }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "Statistic"
        yield Label("─ System ─",    classes="section")
        yield Label("", id="hostname-label", classes="info")
        yield Label("", id="os-label",       classes="info")
        yield Label("", id="uptime-label",   classes="info")
        yield Label("─ Resources ─", classes="section")
        yield Label("CPU  0%", id="cpu-label")
        yield ProgressBar(total=100, id="cpu-bar", show_eta=False)
        yield Label("RAM  0%", id="ram-label")
        yield ProgressBar(total=100, id="ram-bar", show_eta=False)
        yield Label("SWP  0%", id="swp-label")
        yield ProgressBar(total=100, id="swp-bar", show_eta=False)
        yield Label("─ Disk ─",      classes="section")
        yield Label("DSK  0%", id="dsk-label")
        yield ProgressBar(total=100, id="dsk-bar", show_eta=False)
        yield Label("", id="dsk-info", classes="info")

    def on_mount(self) -> None:
        uname = platform.uname()
        self.query_one("#hostname-label", Label).update(f"Host  {uname.node}")
        self.query_one("#os-label",       Label).update(f"OS    {uname.system} {uname.release}")
        self.update_stats()
        self.set_interval(2, self.update_stats)

    def update_stats(self) -> None:
        cpu  = psutil.cpu_percent()
        ram  = psutil.virtual_memory().percent
        swp  = psutil.swap_memory().percent
        disk = psutil.disk_usage("/")

        boot   = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot
        hours, rem = divmod(int(uptime.total_seconds()), 3600)
        self.query_one("#uptime-label", Label).update(f"Up    {hours}h {rem // 60}m")

        for bar_id, val in (("#cpu-bar", cpu), ("#ram-bar", ram), ("#swp-bar", swp)):
            self.query_one(bar_id, ProgressBar).progress = val
        self.query_one("#cpu-label", Label).update(f"CPU  {cpu}%")
        self.query_one("#ram-label", Label).update(f"RAM  {ram}%")
        self.query_one("#swp-label", Label).update(f"SWP  {swp}%")

        pct = disk.percent
        used  = disk.used  / 1024 ** 3
        total = disk.total / 1024 ** 3
        self.query_one("#dsk-bar",  ProgressBar).progress = pct
        self.query_one("#dsk-label", Label).update(f"DSK  {pct}%")
        self.query_one("#dsk-info",  Label).update(f"      {used:.1f} / {total:.1f} GB")


# ──────────────────────────────────────────────────────────────────────────────
# ScheduleBox — compact today overview with clickable rows
# ──────────────────────────────────────────────────────────────────────────────

class EventRow(Horizontal):
    """One clickable event row in the home ScheduleBox."""

    DEFAULT_CSS = """
    EventRow          { height: 1; width: 100%; }
    EventRow:hover    { background: $surface-lighten-1; }
    EventRow .er-time { width: 6;   color: $text-muted; }
    EventRow .er-dot  { width: 2;   text-style: bold; }
    EventRow .er-title{ width: 1fr; color: $text; }
    EventRow .er-tag  { width: 4;   text-align: right; }
    EventRow .er-due  { width: 5;   color: $error; text-style: bold; }
    EventRow.ev-past .er-time  { color: $text-disabled; }
    EventRow.ev-past .er-title { color: $text-disabled; text-style: strike; }
    EventRow.ev-now             { background: $surface; }
    EventRow.ev-now .er-time   { color: $warning; text-style: bold; }
    EventRow.ev-now .er-title  { color: $text; text-style: bold; }
    """

    DOT = {"critical": "●", "high": "●", "medium": "○", "low": "○"}

    def __init__(self, event: dict, now_str: str) -> None:
        super().__init__()
        self._ev  = event
        self._now = now_str

    def compose(self) -> ComposeResult:
        ev        = self._ev
        pri_color = PRIORITY[ev["priority"]][0]
        cat_color = CATEGORY_COLOR[ev["category"]]
        cat_icon  = CATEGORY_ICON[ev["category"]]
        dot       = self.DOT[ev["priority"]]
        end       = ev.get("end_time") or "99:99"

        is_past = end < self._now and ev["date"] == date.today()
        is_now  = (ev["date"] == date.today()
                   and ev["time"] <= self._now <= end)

        if is_now:
            self.add_class("ev-now")
        elif is_past:
            self.add_class("ev-past")

        due_today = ev.get("deadline") == date.today()

        yield Label(ev["time"],                                       classes="er-time")
        yield Label(f"[{pri_color}]{dot}[/]", markup=True,           classes="er-dot")
        yield Label(ev["title"],                                      classes="er-title")
        yield Label(f"[{cat_color}]{cat_icon}[/]", markup=True,      classes="er-tag")
        yield Label("DUE" if due_today else "",                       classes="er-due")

    def on_click(self) -> None:
        # Jump to Schedule tab, focused on today
        self.post_message(SwitchToSchedule(date.today()))


class ScheduleBox(Vertical):
    DEFAULT_CSS = """
    ScheduleBox {
        height: auto;
        border: round $primary;
        row-span: 2;
        padding: 0 2;
    }
    ScheduleBox #sb-date    { color: $text-muted; margin-bottom: 1; }
    ScheduleBox .sb-section { color: $primary; text-style: bold; margin-top: 1; }
    ScheduleBox #sb-summary { color: $text-muted; text-style: italic; margin-top: 1; }
    ScheduleBox #sb-hint    { color: $text-disabled; text-style: italic; }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "Today's Schedule"
        today_str = f"{date.today().strftime('%A, %B')} {date.today().day}"
        yield Label(f"── {today_str} ──", id="sb-date")
        yield Label("─ Upcoming ─", classes="sb-section")
        yield Label("Loading…",     id="sb-placeholder")
        yield Label("",             id="sb-summary")
        yield Label("↑ Click any event to open Schedule", id="sb-hint")

    def on_mount(self) -> None:
        self._render()
        self.set_interval(60, self._render)

    def _render(self) -> None:
        now    = datetime.now().strftime("%H:%M")
        events = get_events_for_date(load_events(), date.today())

        # Remove old rows + placeholder
        for row in self.query(EventRow):
            row.remove()
        try:
            self.query_one("#sb-placeholder", Label).remove()
        except Exception:
            pass

        if not events:
            self.mount(Label("No events today.", id="sb-placeholder"))
            self.query_one("#sb-summary", Label).update("")
            return

        upcoming = [e for e in events if (e.get("end_time") or e["time"]) >= now]
        past     = [e for e in events if (e.get("end_time") or e["time"]) <  now]
        hint     = self.query_one("#sb-hint",    Label)
        summary  = self.query_one("#sb-summary", Label)

        for ev in upcoming[:5]:
            self.mount(EventRow(ev, now), before=hint)

        if past:
            self.mount(Label(f"─ Done ({len(past)}) ─", classes="sb-section"), before=hint)
            for ev in past[-2:]:
                self.mount(EventRow(ev, now), before=hint)

        crit     = sum(1 for e in events if e["priority"] == "critical")
        due      = sum(1 for e in events if e.get("deadline") == date.today())
        parts    = []
        if crit: parts.append(f"{crit} critical")
        if due:  parts.append(f"{due} due today")
        summary.update("  ·  ".join(parts) if parts else f"{len(events)} events")


# ──────────────────────────────────────────────────────────────────────────────
# Home Widget
# ──────────────────────────────────────────────────────────────────────────────

class Home(Widget):
    DEFAULT_CSS = """
    Home {
        layout: grid;
        grid-size: 3 3;
        grid-columns: 1fr 2fr 2fr;
    }
    .box { height: 100%; border: round $primary; padding: 0 1; }
    """

    def compose(self) -> ComposeResult:
        yield StatisticBox()
        yield ScheduleBox()
        yield Static("3", classes="box")
        yield Static("4", classes="box")
        yield Static("5", classes="box")
        yield Static("6", classes="box")