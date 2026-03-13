from datetime import date, timedelta
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Button, Static
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.reactive import reactive
from databases.scheduleData import (
    get_events_for_date, get_week_dates,
    PRIORITY, CATEGORY_ICON, CATEGORY_COLOR,
)


# ─── Event Card (full detail) ─────────────────────────────────────────────────

class EventCard(Vertical):
    DEFAULT_CSS = """
    EventCard {
        height: auto;
        width: 100%;
        border: round $surface-lighten-2;
        padding: 0 2;
        margin-bottom: 1;
    }
    EventCard.priority-critical { border: round $error; }
    EventCard.priority-high     { border: round $warning; }
    EventCard.priority-medium   { border: round $primary; }
    EventCard.priority-low      { border: round $success; }

    EventCard .card-header {
        layout: horizontal;
        height: 2;
        width: 100%;
    }
    EventCard .card-time {
        width: 14;
        color: $text-muted;
        text-style: bold;
    }
    EventCard .card-title {
        width: 1fr;
        text-style: bold;
        color: $text;
    }
    EventCard .card-priority-badge {
        width: 8;
        text-align: right;
        text-style: bold;
    }
    EventCard .card-cat-badge {
        width: 5;
        text-align: right;
    }
    EventCard .card-meta {
        color: $text-muted;
        height: auto;
        width: 100%;
    }
    EventCard .card-deadline {
        color: $error;
        text-style: bold;
    }
    EventCard .card-notes {
        color: $text-muted;
        text-style: italic;
        width: 100%;
        height: auto;
    }
    EventCard .card-divider {
        color: $surface-lighten-3;
    }

    EventCard.is-now {
        background: $surface;
    }
    EventCard.is-now .card-title {
        color: $warning;
    }
    EventCard.is-past .card-title {
        color: $text-disabled;
        text-style: strike;
    }
    EventCard.is-past .card-time {
        color: $text-disabled;
    }
    """

    def __init__(self, event: dict, now_str: str) -> None:
        super().__init__()
        self._ev  = event
        self._now = now_str

    def compose(self) -> ComposeResult:
        ev  = self._ev
        now = self._now

        pri_color, pri_label = PRIORITY[ev["priority"]]
        cat_color            = CATEGORY_COLOR[ev["category"]]
        cat_icon             = CATEGORY_ICON[ev["category"]]

        # Time range
        time_str = ev["time"]
        if ev.get("end_time"):
            time_str = f"{ev['time']}–{ev['end_time']}"

        is_past = (ev.get("end_time") or ev["time"]) < now and ev["date"] == date.today()
        is_now  = (
            ev["date"] == date.today()
            and ev["time"] <= now
            and (ev.get("end_time") or "99:99") >= now
        )

        self.add_class(f"priority-{ev['priority']}")
        if is_now:
            self.add_class("is-now")
        elif is_past:
            self.add_class("is-past")

        # ── Header row ──
        with Horizontal(classes="card-header"):
            yield Label(time_str, classes="card-time")
            yield Label(ev["title"], classes="card-title")
            yield Label(
                f"[{pri_color}]{pri_label}[/]",
                classes="card-priority-badge",
                markup=True,
            )
            yield Label(
                f"[{cat_color}]{cat_icon}[/]",
                classes="card-cat-badge",
                markup=True,
            )

        # ── Meta row (location) ──
        if ev.get("location"):
            yield Label(f"  @ {ev['location']}", classes="card-meta")

        # ── Deadline ──
        if ev.get("deadline"):
            dl = ev["deadline"]
            days_left = (dl - date.today()).days
            if days_left == 0:
                dl_str = "Due TODAY"
            elif days_left == 1:
                dl_str = "Due TOMORROW"
            elif days_left < 0:
                dl_str = f"OVERDUE ({abs(days_left)}d ago)"
            else:
                dl_str = f"Deadline: {dl.strftime('%b')} {dl.day} ({days_left}d)"
            yield Label(f"  ⚑ {dl_str}", classes="card-deadline")

        # ── Notes ──
        if ev.get("notes"):
            yield Label(f"  {ev['notes']}", classes="card-notes")


# ─── Day Selector Bar ─────────────────────────────────────────────────────────

class DayButton(Button):
    DEFAULT_CSS = """
    DayButton {
        min-width: 10;
        height: 3;
        border: none;
        background: $surface;
        color: $text-muted;
    }
    DayButton:hover {
        background: $surface-lighten-1;
        color: $text;
    }
    DayButton.selected {
        background: $primary 30%;
        color: $primary;
        text-style: bold;
        border-bottom: solid $primary;
    }
    DayButton.today {
        color: $warning;
    }
    DayButton.has-critical {
        color: $error;
    }
    """

    def __init__(self, d: date, selected: bool = False) -> None:
        today     = date.today()
        label_day = d.strftime("%a")   # Mon, Tue …
        label_num = str(d.day)         # 1, 2 … (cross-platform)
        events    = get_events_for_date(d)
        dot       = f" ({'!' if any(e['priority']=='critical' for e in events) else len(events)})" if events else ""
        label     = f"{label_day}\n{label_num}{dot}"
        # super().__init__ MUST come before add_class / reactive access
        super().__init__(label, id=f"day-{d.isoformat()}")
        self._date = d
        if selected:
            self.add_class("selected")
        if d == today:
            self.add_class("today")
        if any(e["priority"] == "critical" for e in events):
            self.add_class("has-critical")

    @property
    def day_date(self) -> date:
        return self._date


# ─── Main Schedule Widget ─────────────────────────────────────────────────────

class Schedule(Widget):
    selected_date: reactive[date] = reactive(date.today)

    DEFAULT_CSS = """
    Schedule {
        layout: vertical;
        height: 1fr;
        width: 100%;
    }

    /* ── Day nav bar ── */
    #day-nav {
        height: 4;
        width: 100%;
        layout: horizontal;
        background: $surface;
        border-bottom: solid $surface-lighten-2;
        padding: 0 1;
    }

    /* ── Body: legend + event list ── */
    #sched-body {
        layout: horizontal;
        height: 1fr;
        width: 100%;
    }

    /* ── Left legend / stats ── */
    #sched-legend {
        width: 22;
        height: 100%;
        border-right: solid $surface-lighten-2;
        padding: 1 2;
    }
    #sched-legend .leg-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    #sched-legend .leg-item {
        color: $text-muted;
        height: auto;
        margin-bottom: 0;
    }
    #sched-legend .leg-count {
        color: $text;
        text-style: bold;
    }
    #sched-legend .leg-sep {
        color: $surface-lighten-3;
        margin-top: 1;
        margin-bottom: 1;
    }
    #sched-legend .leg-cat-title {
        color: $primary;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
    }

    /* ── Event scroll area ── */
    #event-scroll {
        width: 1fr;
        height: 100%;
        padding: 1 2;
    }

    #no-events {
        color: $text-muted;
        text-style: italic;
        text-align: center;
        width: 100%;
        margin-top: 3;
    }
    #day-heading {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        # ── Day navigation ──
        with Horizontal(id="day-nav"):
            for i, d in enumerate(get_week_dates()):
                yield DayButton(d, selected=(i == 0))

        with Horizontal(id="sched-body"):
            # ── Left sidebar ──
            with Vertical(id="sched-legend"):
                yield Label("Overview", classes="leg-title")
                yield Label("", id="leg-total",    classes="leg-item")
                yield Label("", id="leg-critical",  classes="leg-item")
                yield Label("", id="leg-due",       classes="leg-item")
                yield Label("────────────────", classes="leg-sep")
                yield Label("Categories", classes="leg-cat-title")
                yield Label("", id="leg-class",     classes="leg-item")
                yield Label("", id="leg-assign",    classes="leg-item")
                yield Label("", id="leg-work",      classes="leg-item")
                yield Label("", id="leg-meeting",   classes="leg-item")
                yield Label("", id="leg-personal",  classes="leg-item")
                yield Label("────────────────", classes="leg-sep")
                yield Label("Priority", classes="leg-cat-title")
                yield Label("[$error]●[/] Critical", classes="leg-item", markup=True)
                yield Label("[$warning]●[/] High",   classes="leg-item", markup=True)
                yield Label("[$primary]○[/] Medium", classes="leg-item", markup=True)
                yield Label("[$success]○[/] Low",    classes="leg-item", markup=True)

            # ── Scrollable event list ──
            with ScrollableContainer(id="event-scroll"):
                yield Label("", id="day-heading")
                yield Label("", id="no-events")

    def on_mount(self) -> None:
        self._refresh_events()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button
        if not isinstance(btn, DayButton):
            return
        # Update selection styling
        for b in self.query(DayButton):
            b.remove_class("selected")
        btn.add_class("selected")
        self.selected_date = btn.day_date
        self._refresh_events()

    def _refresh_events(self) -> None:
        from datetime import datetime
        now_str  = datetime.now().strftime("%H:%M")
        d        = self.selected_date
        events   = get_events_for_date(d)
        today    = date.today()

        # ── Heading ──
        if d == today:
            heading = f"Today  ·  {d.strftime('%A, %B')} {d.day}"
        elif d == today + timedelta(days=1):
            heading = f"Tomorrow  ·  {d.strftime('%A, %B')} {d.day}"
        else:
            heading = f"{d.strftime('%A, %B')} {d.day}"
        self.query_one("#day-heading", Label).update(heading)

        # ── Remove old cards ──
        for card in self.query(EventCard):
            card.remove()
        no_ev = self.query_one("#no-events", Label)

        if not events:
            no_ev.update("No events scheduled for this day.\nEnjoy the downtime. 🎉")
            return
        no_ev.update("")

        scroll = self.query_one("#event-scroll", ScrollableContainer)
        for ev in events:
            scroll.mount(EventCard(ev, now_str))

        # ── Sidebar stats ──
        by_cat = {k: 0 for k in ["class", "assignment", "work", "meeting", "personal"]}
        critical = 0
        due_today = 0
        for ev in events:
            by_cat[ev["category"]] = by_cat.get(ev["category"], 0) + 1
            if ev["priority"] == "critical":
                critical += 1
            if ev.get("deadline") == d:
                due_today += 1

        def _lbl(val: int, label: str, color: str = "$text") -> str:
            return f"[{color}]{val:>2}[/]  {label}" if val else f" –   {label}"

        self.query_one("#leg-total",   Label).update(_lbl(len(events), "Events"))
        self.query_one("#leg-critical",Label).update(_lbl(critical,    "Critical", "$error"))
        self.query_one("#leg-due",     Label).update(_lbl(due_today,   "Due today", "$warning"))
        self.query_one("#leg-class",   Label).update(_lbl(by_cat["class"],      "[C] Classes"))
        self.query_one("#leg-assign",  Label).update(_lbl(by_cat["assignment"], "[A] Assignments"))
        self.query_one("#leg-work",    Label).update(_lbl(by_cat["work"],       "[W] Work"))
        self.query_one("#leg-meeting", Label).update(_lbl(by_cat["meeting"],    "[M] Meetings"))
        self.query_one("#leg-personal",Label).update(_lbl(by_cat["personal"],   "[P] Personal"))