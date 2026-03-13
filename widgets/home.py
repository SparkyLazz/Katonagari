import psutil
import platform
from datetime import datetime, date
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Static
from textual.containers import Vertical, Horizontal

from databases.scheduleData import PRIORITY, CATEGORY_COLOR, CATEGORY_ICON, get_events_for_date


class StatisticBox(Vertical):
    DEFAULT_CSS = """
    StatisticBox {
        height: auto;
        border: round $primary;
        row-span: 2;
        padding: 0 2;
    }
    StatisticBox Label {
        width: 100%;
        margin-top: 0;
        color: $text-muted;
    }
    StatisticBox Label.section {
        color: $primary;
        text-style: bold;
        margin-top: 1;
    }
    StatisticBox Label.info {
        color: $text;
    }
    StatisticBox ProgressBar {
        width: 100%;
        margin-bottom: 0;
    }

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

        # system info
        yield Label("─ System ─", classes="section")
        yield Label("", id="hostname-label", classes="info")
        yield Label("", id="os-label", classes="info")
        yield Label("", id="uptime-label", classes="info")

        # resources
        yield Label("─ Resources ─", classes="section")
        yield Label("CPU  0%", id="cpu-label")
        yield ProgressBar(total=100, id="cpu-bar", show_eta=False)
        yield Label("RAM  0%", id="ram-label")
        yield ProgressBar(total=100, id="ram-bar", show_eta=False)
        yield Label("SWP  0%", id="swp-label")
        yield ProgressBar(total=100, id="swp-bar", show_eta=False)

        # disk
        yield Label("─ Disk ─", classes="section")
        yield Label("DSK  0%", id="dsk-label")
        yield ProgressBar(total=100, id="dsk-bar", show_eta=False)
        yield Label("", id="dsk-info", classes="info")

    def on_mount(self) -> None:
        # static system info
        uname = platform.uname()
        self.query_one("#hostname-label", Label).update(f"Host  {uname.node}")
        self.query_one("#os-label", Label).update(f"OS    {uname.system} {uname.release}")

        self.update_stats()
        self.set_interval(2, self.update_stats)

    def update_stats(self) -> None:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        swp = psutil.swap_memory().percent
        disk = psutil.disk_usage("/")

        # uptime
        boot = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot
        hours, rem = divmod(int(uptime.total_seconds()), 3600)
        mins = rem // 60
        self.query_one("#uptime-label", Label).update(f"Up    {hours}h {mins}m")

        # resources
        self.query_one("#cpu-bar", ProgressBar).progress = cpu
        self.query_one("#ram-bar", ProgressBar).progress = ram
        self.query_one("#swp-bar", ProgressBar).progress = swp
        self.query_one("#cpu-label", Label).update(f"CPU  {cpu}%")
        self.query_one("#ram-label", Label).update(f"RAM  {ram}%")
        self.query_one("#swp-label", Label).update(f"SWP  {swp}%")

        # disk
        dsk_pct = disk.percent
        used_gb = disk.used / 1024 ** 3
        total_gb = disk.total / 1024 ** 3
        self.query_one("#dsk-bar", ProgressBar).progress = dsk_pct
        self.query_one("#dsk-label", Label).update(f"DSK  {dsk_pct}%")
        self.query_one("#dsk-info", Label).update(f"      {used_gb:.1f} / {total_gb:.1f} GB")


class EventRow(Horizontal):
    """A single compact event row in the home ScheduleBox."""

    DEFAULT_CSS = """
    EventRow {
        height: auto;
        width: 100%;
        margin-bottom: 1;
    }
    EventRow .ev-time {
        width: 6;
        color: $text-muted;
    }
    EventRow .ev-priority {
        width: 2;
        text-style: bold;
    }
    EventRow .ev-title {
        width: 1fr;
        color: $text;
    }
    EventRow .ev-tag {
        width: 4;
        text-align: right;
        text-style: italic;
    }
    EventRow .ev-due {
        width: 5;
        color: $error;
        text-style: bold;
    }
    EventRow.past .ev-time  { color: $text-disabled; }
    EventRow.past .ev-title { color: $text-disabled; text-style: strike; }
    EventRow.now  { background: $surface; }
    EventRow.now .ev-time  { color: $warning; text-style: bold; }
    EventRow.now .ev-title { color: $text; text-style: bold; }
    """

    PRIORITY_DOT = {
        "critical": "●",
        "high": "●",
        "medium": "○",
        "low": "○",
    }

    def __init__(self, event: dict, now_time: str) -> None:
        super().__init__()
        self._event = event
        self._now = now_time

    def compose(self) -> ComposeResult:
        ev = self._event
        pri_color, _ = PRIORITY[ev["priority"]]
        cat_color = CATEGORY_COLOR[ev["category"]]
        cat_icon = CATEGORY_ICON[ev["category"]]
        dot = self.PRIORITY_DOT[ev["priority"]]

        is_due_today = ev["deadline"] == date.today()
        is_past = ev["time"] < self._now
        is_now = (
                ev["time"] <= self._now
                and (ev.get("end_time") or "99:99") >= self._now
        )

        if is_now:
            self.add_class("now")
        elif is_past:
            self.add_class("past")

        yield Label(ev["time"], classes="ev-time")
        yield Label(
            f"[{pri_color}]{dot}[/]",
            classes="ev-priority",
            markup=True,
        )
        yield Label(ev["title"], classes="ev-title")
        yield Label(
            f"[{cat_color}]{cat_icon}[/]",
            classes="ev-tag",
            markup=True,
        )
        if is_due_today:
            yield Label("DUE", classes="ev-due")
        else:
            yield Label("", classes="ev-due")


class ScheduleBox(Vertical):
    DEFAULT_CSS = """
    ScheduleBox {
        height: auto;
        border: round $primary;
        row-span: 2;
        padding: 0 2;
    }
    ScheduleBox #sched-header {
        color: $primary;
        text-style: bold;
        margin-top: 0;
        margin-bottom: 1;
    }
    ScheduleBox #sched-empty {
        color: $text-muted;
        text-style: italic;
    }
    ScheduleBox #sched-date {
        width: 100%;
        color: $text-muted;
        margin-bottom: 1;
    }
    ScheduleBox .section {
        color: $primary;
        text-style: bold;
        margin-top: 1;
    }
    ScheduleBox #sched-summary {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "Today's Schedule"
        today_str = date.today().strftime("%A, %B ") + str(date.today().day)
        yield Label(f"── {today_str} ──", id="sched-date")
        yield Label("─ Upcoming ─", classes="section")
        yield Label("Loading...", id="sched-events-placeholder")
        yield Label("", id="sched-summary")

    def on_mount(self) -> None:
        self._render_events()
        self.set_interval(60, self._render_events)

    def _render_events(self) -> None:
        now = datetime.now().strftime("%H:%M")
        events = get_events_for_date(date.today())

        # Remove old event rows
        for row in self.query(EventRow):
            row.remove()
        placeholder = self.query_one("#sched-events-placeholder", Label)
        placeholder.remove()

        if not events:
            self.mount(Label("No events today.", id="sched-events-placeholder"))
            self.query_one("#sched-summary", Label).update("")
            return

        # Split into upcoming/past
        upcoming = [e for e in events if (e.get("end_time") or e["time"]) >= now]
        past = [e for e in events if (e.get("end_time") or e["time"]) < now]

        # Mount upcoming (show max 5 to avoid overflow)
        for ev in upcoming[:5]:
            self.mount(EventRow(ev, now))

        # Past events — compact count
        if past:
            self.mount(Label(f"─ Done ({len(past)}) ─", classes="section"))
            for ev in past[-2:]:  # show last 2 done
                self.mount(EventRow(ev, now))

        # Summary line
        critical = sum(1 for e in events if e["priority"] == "critical")
        due_today = sum(1 for e in events if e.get("deadline") == date.today())
        parts = []
        if critical:
            parts.append(f"{critical} critical")
        if due_today:
            parts.append(f"{due_today} due today")
        summary = "  ·  ".join(parts) if parts else f"{len(events)} events"
        self.query_one("#sched-summary", Label).update(summary)

class Home(Widget):
    DEFAULT_CSS = """
    Home {
        layout: grid;
        grid-size: 3 3;
        grid-columns: 1fr 2fr 2fr;
    }
    .box {
        height: 100%;
        border: round $primary;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield StatisticBox()
        yield ScheduleBox()
        yield Static("3", classes="box")
        yield Static("4", classes="box")
        yield Static("5", classes="box")
        yield Static("6", classes="box")