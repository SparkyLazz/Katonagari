"""
home.py — Home tab widget.

Layout (Horizontal → three Vertical columns, borders always flush):

  ┌─ System ────┐  ┌─ Today's Schedule ──┐  ┌─ Deadlines ────┐
  │  host/os    │  │  event rows          │  │  upcoming due  │
  │  CPU/RAM    │  │                      │  │                │
  │  Swap/Disk  │  ├─ Week Overview ──────┤  ├─ Quick Stats ──┤
  │             │  │  Mon Tue … Sun bars  │  │  by category   │
  └─────────────┘  └──────────────────────┘  └────────────────┘

ScheduleBox rows are clickable: clicking one posts SwitchToSchedule
so Dashboard can jump to the Schedule tab.
"""
from __future__ import annotations

import platform
import psutil
from collections import Counter
from datetime import date, datetime, timedelta

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ProgressBar

from databases.scheduleData import (
    CATEGORIES, CATEGORY_COLOR, CATEGORY_ICON, PRIORITY,
    get_events_for_date, load_events,
)

# ── shared helper ─────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    return load_events()


# ══════════════════════════════════════════════════════════════════════════════
# Message
# ══════════════════════════════════════════════════════════════════════════════

class SwitchToSchedule(Message):
    """Post to make Dashboard switch to the Schedule tab."""
    def __init__(self, target_date: date) -> None:
        super().__init__()
        self.target_date = target_date


# ══════════════════════════════════════════════════════════════════════════════
# Shared panel base — round border, uniform inner padding
# ══════════════════════════════════════════════════════════════════════════════

class Panel(Widget):
    """Base class: round borders, centered titles."""
    DEFAULT_CSS = """
    Panel {
        background: $surface;
        padding: 0 1;
        overflow: hidden hidden;
        border: round $primary;
        border-title-align: left;
        border-title-color: $primary;
        border-title-style: bold;
        margin-bottom: 1;
    }
    Panel .muted { color: $text-muted; }
    Panel .dim   { color: $text-disabled; }
    Panel .info  { color: $text; }
    Panel .ok    { color: $success; }
    Panel .warn  { color: $warning; }
    Panel .err   { color: $error; }
    Panel .acc   { color: $accent; }
    Panel .pri   { color: $primary; }
    """


# ══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN — System Stats
# ══════════════════════════════════════════════════════════════════════════════

class StatisticBox(Panel):
    """Full-height left panel: host info + live resource bars."""

    DEFAULT_CSS = Panel.DEFAULT_CSS + """
    StatisticBox {
        width: 100%;
        height: 1fr;
    }
    StatisticBox Label { width: 100%; }
    StatisticBox ProgressBar { width: 100%; margin-bottom: 1; }

    #cpu-lbl  { color: $success; }
    #ram-lbl  { color: $warning; }
    #swp-lbl  { color: $error;   }
    #dsk-lbl  { color: $accent;  }

    #cpu-bar > .bar--bar { color: $success; }
    #ram-bar > .bar--bar { color: $warning; }
    #swp-bar > .bar--bar { color: $error;   }
    #dsk-bar > .bar--bar { color: $accent;  }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "🤺 SYSTEM MONITORING"
        yield Label("", id="lbl-host",   classes="info")
        yield Label("", id="lbl-os",     classes="info")
        yield Label("", id="lbl-uptime", classes="muted")

        yield Label("")
        yield Label("RESOURCES", classes="muted")

        yield Label("CPU", id="cpu-lbl")
        yield ProgressBar(total=100, id="cpu-bar", show_eta=False)

        yield Label("RAM", id="ram-lbl")
        yield ProgressBar(total=100, id="ram-bar", show_eta=False)

        yield Label("SWP", id="swp-lbl")
        yield ProgressBar(total=100, id="swp-bar", show_eta=False)

        yield Label("")
        yield Label("DISK", classes="muted")
        yield Label("DSK", id="dsk-lbl")
        yield ProgressBar(total=100, id="dsk-bar", show_eta=False)
        yield Label("", id="dsk-detail", classes="muted")

    def on_mount(self) -> None:
        u = platform.uname()
        self.query_one("#lbl-host", Label).update(f"  {u.node}")
        self.query_one("#lbl-os",   Label).update(f"  {u.system} {u.release}")
        self._tick()
        self.set_interval(2, self._tick)

    def _tick(self) -> None:
        cpu  = psutil.cpu_percent()
        ram  = psutil.virtual_memory().percent
        swp  = psutil.swap_memory().percent
        disk = psutil.disk_usage("/")

        boot   = datetime.fromtimestamp(psutil.boot_time())
        h, rem = divmod(int((datetime.now() - boot).total_seconds()), 3600)
        self.query_one("#lbl-uptime", Label).update(f"  up {h}h {rem // 60}m")

        for bar_id, lbl_id, val, tag in (
            ("#cpu-bar", "#cpu-lbl", cpu,  "CPU"),
            ("#ram-bar", "#ram-lbl", ram,  "RAM"),
            ("#swp-bar", "#swp-lbl", swp,  "SWP"),
        ):
            self.query_one(bar_id,  ProgressBar).progress = val
            self.query_one(lbl_id,  Label).update(f"{tag}   {val:.0f}%")

        pct  = disk.percent
        used = disk.used  / 1024 ** 3
        tot  = disk.total / 1024 ** 3
        self.query_one("#dsk-bar",    ProgressBar).progress = pct
        self.query_one("#dsk-lbl",    Label).update(f"DSK   {pct:.0f}%")
        self.query_one("#dsk-detail", Label).update(f"  {used:.1f} / {tot:.1f} GB")


# ══════════════════════════════════════════════════════════════════════════════
# MIDDLE TOP — Today's Schedule
# ══════════════════════════════════════════════════════════════════════════════

class EventRow(Widget):
    """Single clickable event row inside ScheduleBox."""

    DEFAULT_CSS = """
    EventRow            { layout: horizontal; height: 1; width: 100%; }
    EventRow:hover      { background: $surface-lighten-1; }

    EventRow .er-time   { width: 6;   color: $text-muted; }
    EventRow .er-dot    { width: 2;   text-style: bold; }
    EventRow .er-title  { width: 1fr; color: $text; }
    EventRow .er-tag    { width: 4;   text-align: right; }
    EventRow .er-due    { width: 5;   color: $error; text-style: bold; }

    EventRow.ev-past .er-time  { color: $text-disabled; }
    EventRow.ev-past .er-title { color: $text-disabled; text-style: strike; }

    EventRow.ev-now             { background: $surface; }
    EventRow.ev-now .er-time   { color: $warning; text-style: bold; }
    EventRow.ev-now .er-title  { color: $text;    text-style: bold; }
    """

    _DOT = {"critical": "●", "high": "●", "medium": "○", "low": "○"}

    def __init__(self, event: dict, now_str: str) -> None:
        super().__init__()
        self._ev  = event
        self._now = now_str

    def compose(self) -> ComposeResult:
        ev        = self._ev
        pri_color = PRIORITY[ev["priority"]][0]
        cat_color = CATEGORY_COLOR[ev["category"]]
        cat_icon  = CATEGORY_ICON[ev["category"]]
        end       = ev.get("end_time") or "99:99"

        if ev["date"] == date.today() and ev["time"] <= self._now <= end:
            self.add_class("ev-now")
        elif end < self._now and ev["date"] == date.today():
            self.add_class("ev-past")

        yield Label(ev["time"],                                          classes="er-time")
        yield Label(f"[{pri_color}]{self._DOT[ev['priority']]}[/]",
                    markup=True,                                         classes="er-dot")
        yield Label(ev["title"],                                         classes="er-title")
        yield Label(f"[{cat_color}]{cat_icon}[/]", markup=True,         classes="er-tag")
        yield Label("DUE" if ev.get("deadline") == date.today() else "", classes="er-due")

    def on_click(self) -> None:
        self.post_message(SwitchToSchedule(date.today()))


class ScheduleBox(Panel):
    """Middle-top panel: today's events, live-refreshed every 60 s."""

    DEFAULT_CSS = Panel.DEFAULT_CSS + """
    ScheduleBox {
        height: 1fr;
        width: 1fr;
    }
    ScheduleBox #sb-hint { color: $text-disabled; text-style: italic; }
    ScheduleBox #sb-summary { color: $text-muted; text-style: italic; }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "📅 TODAY'S SCHEDULE"
        today_str = f"{date.today().strftime('%A, %B %d')}"
        yield Label(today_str, classes="muted", id="sb-date")
        yield Label("Loading…", id="sb-placeholder")
        yield Label("",         id="sb-summary")
        yield Label("↑ Click any event to open Schedule tab", id="sb-hint")

    def on_mount(self) -> None:
        self._refresh()
        self.set_interval(60, self._refresh)

    def _refresh(self) -> None:
        now    = datetime.now().strftime("%H:%M")
        events = get_events_for_date(_load(), date.today())
        hint   = self.query_one("#sb-hint", Label)

        for w in self.query(EventRow):
            w.remove()
        for w in self.query(".dyn-sep"):
            w.remove()

        placeholder = self.query_one("#sb-placeholder", Label)
        summary     = self.query_one("#sb-summary",     Label)

        if not events:
            placeholder.display = True
            placeholder.update("No events today.")
            summary.update("")
            return

        placeholder.display = False

        upcoming = [e for e in events if (e.get("end_time") or e["time"]) >= now]
        past     = [e for e in events if (e.get("end_time") or e["time"]) <  now]

        for ev in upcoming[:5]:
            self.mount(EventRow(ev, now), before=hint)

        if past:
            sep = Label(f"─ Done ({len(past)}) ─", classes="muted dyn-sep")
            self.mount(sep, before=hint)
            for ev in past[-2:]:
                self.mount(EventRow(ev, now), before=hint)

        crit  = sum(1 for e in events if e["priority"] == "critical")
        due   = sum(1 for e in events if e.get("deadline") == date.today())
        parts = []
        if crit: parts.append(f"{crit} critical")
        if due:  parts.append(f"{due} due today")
        summary.update("  ·  ".join(parts) if parts else f"{len(events)} events")


# ══════════════════════════════════════════════════════════════════════════════
# MIDDLE BOTTOM — Week Overview
# ══════════════════════════════════════════════════════════════════════════════

class WeekOverview(Panel):
    """Middle-bottom panel: 7-day bar showing event counts per day."""

    DEFAULT_CSS = Panel.DEFAULT_CSS + """
    WeekOverview {
        height: 1fr;
        width: 1fr;
    }
    WeekOverview .wo-row   { layout: horizontal; height: 1; width: 100%; }
    WeekOverview .wo-day   { width: 5;  color: $text-muted; }
    WeekOverview .wo-bar   { width: 1fr; }
    WeekOverview .wo-count { width: 4; text-align: right; color: $text-muted; }
    WeekOverview .today-lbl { color: $warning; text-style: bold; }
    """

    _BAR_CHARS = " ▏▎▍▌▋▊▉█"

    def compose(self) -> ComposeResult:
        self.border_title = "📊 WEEK OVERVIEW"
        today = date.today()
        for i in range(7):
            d = today + timedelta(days=i)
            row_id = f"wo-row-{i}"
            with Horizontal(classes="wo-row", id=row_id):
                lbl_cls = "wo-day today-lbl" if i == 0 else "wo-day"
                day_str = "Today" if i == 0 else d.strftime("%a %d")
                yield Label(day_str, classes=lbl_cls, id=f"wo-day-{i}")
                yield Label("",      classes="wo-bar",   id=f"wo-bar-{i}")
                yield Label("",      classes="wo-count", id=f"wo-cnt-{i}")

    def on_mount(self) -> None:
        self._refresh()
        self.set_interval(120, self._refresh)

    def _refresh(self) -> None:
        events = _load()
        today  = date.today()
        counts = [len(get_events_for_date(events, today + timedelta(days=i))) for i in range(7)]
        max_c  = max(counts) if any(counts) else 1
        bar_w  = 12  # approximate char width available for the bar

        for i, n in enumerate(counts):
            filled = int((n / max_c) * bar_w) if max_c else 0
            bar    = "█" * filled + ("░" * (bar_w - filled))
            if i == 0:
                bar_markup = f"[yellow]{bar}[/]"
            elif n == 0:
                bar_markup = f"[dim]{bar}[/]"
            elif n == max_c:
                bar_markup = f"[$error]{bar}[/]"
            else:
                bar_markup = f"[$primary]{bar}[/]"

            self.query_one(f"#wo-bar-{i}", Label).update(bar_markup)
            cnt_str = str(n) if n else "–"
            self.query_one(f"#wo-cnt-{i}", Label).update(cnt_str)


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT TOP — Upcoming Deadlines
# ══════════════════════════════════════════════════════════════════════════════

class DeadlineBox(Panel):
    """Right-top panel: next deadlines sorted by proximity."""

    DEFAULT_CSS = Panel.DEFAULT_CSS + """
    DeadlineBox {
        height: 1fr;
        width: 1fr;
    }
    DeadlineBox .dl-row   { layout: horizontal; height: 1; }
    DeadlineBox .dl-date  { width: 9;  }
    DeadlineBox .dl-title { width: 1fr; color: $text; overflow: hidden hidden; }
    DeadlineBox .dl-days  { width: 7;  text-align: right; }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "⏰ UPCOMING DEADLINES"
        yield Label("Loading…", id="dl-placeholder", classes="muted")
        # Reserve 8 slots
        for i in range(8):
            with Horizontal(classes="dl-row", id=f"dl-slot-{i}"):
                yield Label("", id=f"dl-date-{i}",  classes="dl-date")
                yield Label("", id=f"dl-title-{i}", classes="dl-title")
                yield Label("", id=f"dl-days-{i}",  classes="dl-days")

    def on_mount(self) -> None:
        self._refresh()
        self.set_interval(120, self._refresh)

    def _refresh(self) -> None:
        today  = date.today()
        events = _load()

        # All events that have a deadline, sorted by deadline ascending
        with_dl = sorted(
            [e for e in events if e.get("deadline")],
            key=lambda e: e["deadline"],
        )
        # Show overdue + upcoming (skip very old overdue)
        relevant = [e for e in with_dl if (e["deadline"] - today).days >= -7][:8]

        placeholder = self.query_one("#dl-placeholder", Label)
        placeholder.display = not bool(relevant)

        for i in range(8):
            date_lbl  = self.query_one(f"#dl-date-{i}",  Label)
            title_lbl = self.query_one(f"#dl-title-{i}", Label)
            days_lbl  = self.query_one(f"#dl-days-{i}",  Label)
            row       = self.query_one(f"#dl-slot-{i}",  Horizontal)

            if i >= len(relevant):
                row.display = False
                continue

            row.display = True
            ev   = relevant[i]
            days = (ev["deadline"] - today).days

            # Date label
            if   days == 0:  date_str, date_cls = "Today",    "err"
            elif days == 1:  date_str, date_cls = "Tomorrow", "warn"
            elif days < 0:   date_str, date_cls = ev["deadline"].strftime("%b %d"), "dim"
            else:            date_str, date_cls = ev["deadline"].strftime("%b %d"), "muted"

            # Days badge
            if   days < 0:   badge, badge_cls = f"{abs(days)}d ago", "dim"
            elif days == 0:  badge, badge_cls = "TODAY",              "err"
            elif days == 1:  badge, badge_cls = "1d",                 "warn"
            elif days <= 3:  badge, badge_cls = f"{days}d",           "warn"
            else:            badge, badge_cls = f"{days}d",           "muted"

            date_lbl.update(f"[{date_cls}]{date_str}[/]" if date_cls in ("err","warn","dim") else date_str)
            title_lbl.update(ev["title"])
            days_lbl.update(f"[bold {badge_cls if badge_cls != 'muted' else 'dim white'}]{badge}[/]")


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT BOTTOM — Quick Stats
# ══════════════════════════════════════════════════════════════════════════════

class QuickStatsBox(Panel):
    """Right-bottom panel: event totals by category and priority."""

    DEFAULT_CSS = Panel.DEFAULT_CSS + """
    QuickStatsBox {
        height: 1fr;
        width: 1fr;
    }
    QuickStatsBox .qs-row  { layout: horizontal; height: 1; }
    QuickStatsBox .qs-lbl  { width: 1fr; color: $text-muted; }
    QuickStatsBox .qs-val  { width: 4; text-align: right; text-style: bold; }
    QuickStatsBox .qs-bar  { width: 8; }
    """

    _MAX_BAR = 8

    def compose(self) -> ComposeResult:
        self.border_title = "📈 QUICK STATS"
        for cat in CATEGORIES:
            icon  = CATEGORY_ICON[cat]
            color = CATEGORY_COLOR[cat]
            with Horizontal(classes="qs-row"):
                yield Label(f"[{color}]{icon}[/] {cat.title()}", markup=True, classes="qs-lbl")
                yield Label("", id=f"qs-cbar-{cat}", classes="qs-bar")
                yield Label("", id=f"qs-cval-{cat}", classes="qs-val")

        yield Label("")
        yield Label("BY PRIORITY", classes="muted")
        for pri, (color, label) in PRIORITY.items():
            with Horizontal(classes="qs-row"):
                yield Label(f"[{color}]{label}[/]", markup=True, classes="qs-lbl")
                yield Label("", id=f"qs-pbar-{pri}", classes="qs-bar")
                yield Label("", id=f"qs-pval-{pri}", classes="qs-val")

        yield Label("")
        yield Label("TOTAL", classes="muted")
        with Horizontal(classes="qs-row"):
            yield Label("All events", classes="qs-lbl")
            yield Label("", id="qs-total", classes="qs-val")
        with Horizontal(classes="qs-row"):
            yield Label("This week",  classes="qs-lbl")
            yield Label("", id="qs-week",  classes="qs-val")

    def on_mount(self) -> None:
        self._refresh()
        self.set_interval(120, self._refresh)

    def _refresh(self) -> None:
        events = _load()
        today  = date.today()
        week   = [today + timedelta(days=i) for i in range(7)]

        by_cat = Counter(e["category"] for e in events)
        by_pri = Counter(e["priority"] for e in events)
        total  = len(events)
        n_week = sum(1 for e in events if e["date"] in week)

        max_cat = max(by_cat.values(), default=1)
        max_pri = max(by_pri.values(), default=1)

        def _bar(n: int, max_n: int, color: str) -> str:
            filled = int((n / max_n) * self._MAX_BAR) if max_n else 0
            return f"[{color}]{'█' * filled}[/][dim]{'░' * (self._MAX_BAR - filled)}[/]"

        for cat in CATEGORIES:
            n     = by_cat.get(cat, 0)
            color = CATEGORY_COLOR[cat]
            self.query_one(f"#qs-cbar-{cat}", Label).update(_bar(n, max_cat, color))
            self.query_one(f"#qs-cval-{cat}", Label).update(str(n) if n else "–")

        for pri, (color, _) in PRIORITY.items():
            n = by_pri.get(pri, 0)
            self.query_one(f"#qs-pbar-{pri}", Label).update(_bar(n, max_pri, color))
            self.query_one(f"#qs-pval-{pri}", Label).update(str(n) if n else "–")

        self.query_one("#qs-total", Label).update(str(total) if total else "–")
        self.query_one("#qs-week",  Label).update(str(n_week) if n_week else "–")


# ══════════════════════════════════════════════════════════════════════════════
# Home — root widget
# ══════════════════════════════════════════════════════════════════════════════

class Home(Widget):
    """
    Three-column layout. Borders are drawn by each Panel, so they always sit
    flush with no gaps and no overlapping lines.
    """

    DEFAULT_CSS = """
    Home {
        layout: horizontal;
        height: 1fr;
        width: 100%;
        background: $background;
    }

    /* left column — fixed width, full height */
    #col-left {
        width: 32;
        height: 1fr;
    }

    /* middle and right columns share remaining space equally */
    #col-mid, #col-right {
        width: 1fr;
        height: 1fr;
        layout: vertical;
    }

    /* Gaps between columns handled by layout or margins */
    #col-left, #col-mid {
        margin-right: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="col-left"):
            yield StatisticBox()

        with Vertical(id="col-mid"):
            yield ScheduleBox()
            yield WeekOverview()

        with Vertical(id="col-right"):
            yield DeadlineBox()
            yield QuickStatsBox()