"""
schedule.py — Full Schedule tab widget.
btop-style: dense DataTable, sidebar stats, modal forms, key hints footer.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from databases.scheduleData import (
    CATEGORIES, CATEGORY_COLOR, CATEGORY_ICON, PRIORITIES, PRIORITY,
    add_event, delete_event, get_events_for_date, get_week_dates,
    load_events, update_event,
)

# Textual CSS var → Rich color (for use inside DataTable cells)
_RICH: dict[str, str] = {
    "$error":     "red",
    "$warning":   "yellow",
    "$primary":   "blue",
    "$success":   "green",
    "$accent":    "cyan",
    "$text-muted":"dim white",
}
def _rc(css_var: str) -> str:
    return _RICH.get(css_var, "white")

# ──────────────────────────────────────────────────────────────────────────────
# Select options
# ──────────────────────────────────────────────────────────────────────────────

_PRI_OPTS = [
    ("● Critical", "critical"),
    ("● High",     "high"),
    ("○ Medium",   "medium"),
    ("○ Low",      "low"),
]
_CAT_OPTS = [
    ("[C] Class",       "class"),
    ("[A] Assignment",  "assignment"),
    ("[W] Work",        "work"),
    ("[M] Meeting",     "meeting"),
    ("[P] Personal",    "personal"),
]

# ──────────────────────────────────────────────────────────────────────────────
# Detail Modal  (read-only)
# ──────────────────────────────────────────────────────────────────────────────

class DetailModal(ModalScreen):
    BINDINGS = [("escape,enter,q", "dismiss_modal", "Close")]

    DEFAULT_CSS = """
    DetailModal { align: center middle; }
    #det-box {
        width: 60;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    .det-head  { color: $primary; text-style: bold; margin-bottom: 1; }
    .det-row   { height: 1; layout: horizontal; }
    .det-lbl   { width: 12; color: $text-muted; }
    .det-val   { width: 1fr; color: $text; }
    .det-notes { color: $text-muted; text-style: italic; margin-top: 1; }
    .det-foot  { color: $text-muted; text-align: center; margin-top: 1; }
    """

    def __init__(self, event: dict) -> None:
        super().__init__()
        self._ev = event

    def compose(self) -> ComposeResult:
        ev  = self._ev
        pri_color, pri_label = PRIORITY[ev["priority"]]
        cat_color = CATEGORY_COLOR[ev["category"]]
        cat_icon  = CATEGORY_ICON[ev["category"]]
        time_str  = f"{ev['time']} – {ev['end_time']}" if ev.get("end_time") else ev["time"]

        dl_str = ""
        if ev.get("deadline"):
            days = (ev["deadline"] - date.today()).days
            if   days < 0:  dl_str = f"OVERDUE ({abs(days)}d ago)"
            elif days == 0: dl_str = "TODAY"
            elif days == 1: dl_str = "TOMORROW"
            else:           dl_str = f"{ev['deadline'].strftime('%b')} {ev['deadline'].day} ({days}d left)"

        with Vertical(id="det-box"):
            yield Label(f"── {ev['title']} ──", classes="det-head")
            with Horizontal(classes="det-row"):
                yield Label("Date",     classes="det-lbl")
                yield Label(f"{ev['date'].strftime('%A, %B')} {ev['date'].day}", classes="det-val")
            with Horizontal(classes="det-row"):
                yield Label("Time",     classes="det-lbl")
                yield Label(time_str,   classes="det-val")
            with Horizontal(classes="det-row"):
                yield Label("Priority", classes="det-lbl")
                yield Label(f"[{pri_color}]{pri_label}[/]", classes="det-val", markup=True)
            with Horizontal(classes="det-row"):
                yield Label("Category", classes="det-lbl")
                yield Label(f"[{cat_color}]{cat_icon} {ev['category']}[/]", classes="det-val", markup=True)
            if ev.get("location"):
                with Horizontal(classes="det-row"):
                    yield Label("Location", classes="det-lbl")
                    yield Label(ev["location"], classes="det-val")
            if dl_str:
                with Horizontal(classes="det-row"):
                    yield Label("Deadline", classes="det-lbl")
                    yield Label(dl_str, classes="det-val")
            if ev.get("notes"):
                yield Label(f"  {ev['notes']}", classes="det-notes")
            yield Label("[ Enter / Esc ]  Close", classes="det-foot")

    def action_dismiss_modal(self) -> None:
        self.dismiss()


# ──────────────────────────────────────────────────────────────────────────────
# Confirm Modal
# ──────────────────────────────────────────────────────────────────────────────

class ConfirmModal(ModalScreen):
    BINDINGS = [
        ("y,enter", "yes", "Yes"),
        ("n,escape", "no", "No"),
    ]
    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    #conf-box {
        width: 52;
        height: 7;
        border: solid $error;
        background: $surface;
        padding: 1 2;
        align: center middle;
        layout: vertical;
    }
    #conf-msg  { text-align: center; color: $text; margin-bottom: 1; }
    #conf-hint { text-align: center; color: $text-muted; }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._msg = message

    def compose(self) -> ComposeResult:
        with Vertical(id="conf-box"):
            yield Label(self._msg,                   id="conf-msg")
            yield Label("[ y / Enter ]  Yes    [ n / Esc ]  No", id="conf-hint")

    def action_yes(self) -> None: self.dismiss(True)
    def action_no(self)  -> None: self.dismiss(False)


# ──────────────────────────────────────────────────────────────────────────────
# Add / Edit Form Modal
# ──────────────────────────────────────────────────────────────────────────────

class EventFormModal(ModalScreen):
    BINDINGS = [
        ("escape",  "cancel",  "Cancel"),
        ("ctrl+s",  "confirm", "Save"),
    ]
    DEFAULT_CSS = """
    EventFormModal { align: center middle; }
    #form-box {
        width: 64;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    #form-title { color: $primary; text-style: bold; text-align: center; margin-bottom: 1; }
    .f-row      { height: 3; layout: horizontal; width: 100%; }
    .f-lbl      { width: 12; content-align: left middle; color: $text-muted; }
    .f-inp      { width: 1fr; }
    #form-error { color: $error; height: 1; text-align: center; }
    #form-hint  { color: $text-muted; text-align: center; }
    #form-btns  { layout: horizontal; height: 3; width: 100%; margin-top: 1; }
    #btn-save   { width: 1fr; margin-right: 1; }
    #btn-cancel { width: 1fr; }
    """

    def __init__(self, event: dict | None = None, default_date: date | None = None) -> None:
        super().__init__()
        self._ev    = event
        self._ddate = default_date or date.today()
        self._mode  = "Edit" if event else "Add"

    def compose(self) -> ComposeResult:
        ev = self._ev or {}
        with Vertical(id="form-box"):
            yield Label(f"── {self._mode} Event ──", id="form-title")

            with Horizontal(classes="f-row"):
                yield Label("Title",    classes="f-lbl")
                yield Input(value=ev.get("title", ""), placeholder="Event title", id="i-title", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Date",     classes="f-lbl")
                yield Input(
                    value=ev["date"].isoformat() if ev.get("date") else self._ddate.isoformat(),
                    placeholder="YYYY-MM-DD", id="i-date", classes="f-inp",
                )

            with Horizontal(classes="f-row"):
                yield Label("Time",     classes="f-lbl")
                yield Input(value=ev.get("time", ""), placeholder="HH:MM", id="i-time", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("End Time", classes="f-lbl")
                yield Input(value=ev.get("end_time") or "", placeholder="HH:MM  (optional)", id="i-end", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Priority", classes="f-lbl")
                yield Select(_PRI_OPTS, value=ev.get("priority", "medium"), id="i-priority", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Category", classes="f-lbl")
                yield Select(_CAT_OPTS, value=ev.get("category", "personal"), id="i-category", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Deadline", classes="f-lbl")
                yield Input(
                    value=ev["deadline"].isoformat() if ev.get("deadline") else "",
                    placeholder="YYYY-MM-DD  (optional)", id="i-deadline", classes="f-inp",
                )

            with Horizontal(classes="f-row"):
                yield Label("Notes",    classes="f-lbl")
                yield Input(value=ev.get("notes") or "", placeholder="Notes  (optional)", id="i-notes", classes="f-inp")

            yield Label("",                              id="form-error")
            yield Label("Ctrl+S  Save   Esc  Cancel",   id="form-hint")

            with Horizontal(id="form-btns"):
                yield Button("[ Save ]",   id="btn-save",   variant="primary")
                yield Button("[ Cancel ]", id="btn-cancel")

    def action_confirm(self) -> None: self._try_save()
    def action_cancel(self)  -> None: self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if   event.button.id == "btn-save":   self._try_save()
        elif event.button.id == "btn-cancel": self.dismiss(None)

    def _try_save(self) -> None:
        err      = self.query_one("#form-error", Label)
        title    = self.query_one("#i-title",    Input).value.strip()
        date_str = self.query_one("#i-date",     Input).value.strip()
        time_str = self.query_one("#i-time",     Input).value.strip()
        end_str  = self.query_one("#i-end",      Input).value.strip() or None
        priority = self.query_one("#i-priority", Select).value
        category = self.query_one("#i-category", Select).value
        dl_str   = self.query_one("#i-deadline", Input).value.strip()
        notes    = self.query_one("#i-notes",    Input).value.strip() or None

        # ── Validate ──
        if not title:
            err.update("Title is required."); return
        try:
            ev_date = date.fromisoformat(date_str)
        except ValueError:
            err.update("Invalid date — use YYYY-MM-DD."); return
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            err.update("Invalid time — use HH:MM."); return
        if end_str:
            try:
                datetime.strptime(end_str, "%H:%M")
            except ValueError:
                err.update("Invalid end time — use HH:MM."); return

        # Select.BLANK guard
        from textual.widgets._select import BLANK
        if priority is BLANK:
            err.update("Select a priority."); return
        if category is BLANK:
            err.update("Select a category."); return

        deadline = None
        if dl_str:
            try:
                deadline = date.fromisoformat(dl_str)
            except ValueError:
                err.update("Invalid deadline — use YYYY-MM-DD."); return

        self.dismiss({
            "title":    title,
            "date":     ev_date,
            "time":     time_str,
            "end_time": end_str,
            "priority": priority,
            "category": category,
            "deadline": deadline,
            "notes":    notes,
            "location": self._ev.get("location") if self._ev else None,
        })


# ──────────────────────────────────────────────────────────────────────────────
# Day Navigation Button
# ──────────────────────────────────────────────────────────────────────────────

class DayButton(Button):
    DEFAULT_CSS = """
    DayButton {
        min-width: 9;
        height: 3;
        border: none;
        background: $surface;
        color: $text-muted;
    }
    DayButton:hover              { background: $surface-lighten-1; color: $text; }
    DayButton.selected           { background: $primary 18%; color: $primary; text-style: bold; }
    DayButton.today              { color: $warning; }
    DayButton.selected.today     { background: $warning 12%; color: $warning; }
    """

    def __init__(self, d: date, selected: bool = False) -> None:
        label = f"{d.strftime('%a')}\n{d.day}"
        super().__init__(label, id=f"day-{d.isoformat()}")
        self._date = d
        if selected:
            self.add_class("selected")
        if d == date.today():
            self.add_class("today")

    @property
    def day_date(self) -> date:
        return self._date


# ──────────────────────────────────────────────────────────────────────────────
# Main Schedule Widget
# ──────────────────────────────────────────────────────────────────────────────

class Schedule(Widget):

    BINDINGS = [
        Binding("a",       "add",      "Add",    show=False),
        Binding("e",       "edit",     "Edit",   show=False),
        Binding("d",       "delete",   "Delete", show=False),
        Binding("enter",   "detail",   "Detail", show=False),
        Binding("left",    "prev_day", "← Day",  show=False),
        Binding("right",   "next_day", "→ Day",  show=False),
        Binding("h",       "prev_day", "← Day",  show=False),
        Binding("l",       "next_day", "→ Day",  show=False),
        Binding("r",       "reload",   "Reload", show=False),
    ]

    DEFAULT_CSS = """
    Schedule { layout: vertical; height: 1fr; width: 100%; }

    #day-nav {
        height: 3;
        width: 100%;
        background: $surface;
        border-bottom: solid $surface-lighten-2;
        layout: horizontal;
        padding: 0 1;
    }

    #sched-body { layout: horizontal; height: 1fr; width: 100%; }

    /* ── Sidebar ── */
    #sched-sidebar {
        width: 22;
        height: 100%;
        border-right: solid $surface-lighten-2;
        padding: 1 1;
        overflow: hidden hidden;
    }
    .s-head { color: $primary; text-style: bold; }
    .s-sep  { color: $surface-lighten-3; }
    .s-item { height: 1; color: $text-muted; }

    /* ── Main area ── */
    #sched-main { width: 1fr; height: 100%; layout: vertical; }
    #tbl-label  {
        height: 1;
        color: $primary;
        text-style: bold;
        padding: 0 1;
        background: $surface;
        border-bottom: solid $surface-lighten-2;
    }
    #event-table { height: 1fr; width: 100%; }
    #no-events   { color: $text-muted; text-style: italic; text-align: center; padding: 2 0; }

    /* ── Key hints ── */
    #key-hints {
        height: 1;
        background: $surface;
        border-top: solid $surface-lighten-2;
        color: $text-muted;
        padding: 0 1;
    }
    """

    selected_date: reactive[date] = reactive(date.today)

    def __init__(self) -> None:
        super().__init__()
        self._events: list[dict]         = []
        self._current_events: list[dict] = []

    # ─── Compose ──────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal(id="day-nav"):
            pass  # built in on_mount

        with Horizontal(id="sched-body"):
            with Vertical(id="sched-sidebar"):
                yield Label("OVERVIEW",           classes="s-head")
                yield Label("──────────────────", classes="s-sep")
                yield Label("",  id="leg-total",    classes="s-item")
                yield Label("",  id="leg-critical", classes="s-item")
                yield Label("",  id="leg-due",      classes="s-item")
                yield Label("──────────────────", classes="s-sep")
                yield Label("CATEGORIES",          classes="s-head")
                yield Label("──────────────────", classes="s-sep")
                yield Label("",  id="leg-class",    classes="s-item")
                yield Label("",  id="leg-assign",   classes="s-item")
                yield Label("",  id="leg-work",     classes="s-item")
                yield Label("",  id="leg-meeting",  classes="s-item")
                yield Label("",  id="leg-personal", classes="s-item")
                yield Label("──────────────────", classes="s-sep")
                yield Label("PRIORITY",            classes="s-head")
                yield Label("──────────────────", classes="s-sep")
                yield Label("[$error]●[/]   CRIT",   classes="s-item", markup=True)
                yield Label("[$warning]●[/]  HIGH",  classes="s-item", markup=True)
                yield Label("[$primary]○[/]  MED",   classes="s-item", markup=True)
                yield Label("[$success]○[/]  LOW",   classes="s-item", markup=True)

            with Vertical(id="sched-main"):
                yield Label("", id="tbl-label")
                yield DataTable(id="event-table", show_header=True, cursor_type="row", zebra_stripes=True)
                yield Label("No events. Press [a] to add one.", id="no-events")

        yield Static(
            " [a]dd  [e]dit  [d]el  [enter] detail  [←→] day  [↑↓] nav  [r]eload",
            id="key-hints",
        )

    def on_mount(self) -> None:
        self._events = load_events()
        # Build day nav
        nav = self.query_one("#day-nav", Horizontal)
        for i, d in enumerate(get_week_dates()):
            nav.mount(DayButton(d, selected=(i == 0)))
        # Table columns
        table = self.query_one("#event-table", DataTable)
        table.add_columns("TIME", "PRI", "CAT", "TITLE", "DEADLINE", "LOCATION")
        self._refresh_events()

    # ─── Public API ───────────────────────────────────────────────────────────

    def go_to_date(self, d: date) -> None:
        """Called by Dashboard when user clicks an event in the Home ScheduleBox."""
        self.selected_date = d
        for btn in self.query(DayButton):
            btn.remove_class("selected")
            if btn.day_date == d:
                btn.add_class("selected")
        self._refresh_events()

    # ─── Day nav ──────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button
        if not isinstance(btn, DayButton):
            return
        for b in self.query(DayButton):
            b.remove_class("selected")
        btn.add_class("selected")
        self.selected_date = btn.day_date
        self._refresh_events()

    def action_prev_day(self) -> None:
        self.go_to_date(self.selected_date - timedelta(days=1))

    def action_next_day(self) -> None:
        self.go_to_date(self.selected_date + timedelta(days=1))

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    def action_add(self) -> None:
        def cb(result: dict | None) -> None:
            if result is not None:
                add_event(self._events, result)
                self._refresh_events()
        self.app.push_screen(EventFormModal(default_date=self.selected_date), cb)

    def action_edit(self) -> None:
        ev = self._cursor_event()
        if ev is None:
            return
        def cb(result: dict | None) -> None:
            if result is not None:
                update_event(self._events, ev["id"], result)
                self._refresh_events()
        self.app.push_screen(EventFormModal(event=ev, default_date=self.selected_date), cb)

    def action_delete(self) -> None:
        ev = self._cursor_event()
        if ev is None:
            return
        def cb(confirmed: bool) -> None:
            if confirmed:
                delete_event(self._events, ev["id"])
                self._refresh_events()
        self.app.push_screen(ConfirmModal(f"Delete '{ev['title']}'?"), cb)

    def action_detail(self) -> None:
        ev = self._cursor_event()
        if ev is not None:
            self.app.push_screen(DetailModal(ev))

    def action_reload(self) -> None:
        self._events = load_events()
        self._refresh_events()

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _cursor_event(self) -> dict | None:
        if not self._current_events:
            return None
        idx = self.query_one("#event-table", DataTable).cursor_row
        if 0 <= idx < len(self._current_events):
            return self._current_events[idx]
        return None

    def _refresh_events(self) -> None:
        d       = self.selected_date
        events  = get_events_for_date(self._events, d)
        self._current_events = events

        table  = self.query_one("#event-table", DataTable)
        no_ev  = self.query_one("#no-events",   Label)
        lbl    = self.query_one("#tbl-label",   Label)

        # Heading
        today = date.today()
        prefix = "Today" if d == today else "Tomorrow" if d == today + timedelta(days=1) else ""
        day_str = f"{d.strftime('%A, %B')} {d.day}"
        lbl.update(f" {prefix + '  ·  ' if prefix else ''}{day_str}")

        table.clear()

        if not events:
            table.display = False
            no_ev.display = True
        else:
            table.display = True
            no_ev.display = False

            for ev in events:
                time_str = f"{ev['time']}─{ev['end_time']}" if ev.get("end_time") else ev["time"]
                _, pri_label = PRIORITY[ev["priority"]]
                cat_icon     = CATEGORY_ICON[ev["category"]]

                # Map Textual CSS vars → Rich colors for DataTable
                pri_rc = _rc(PRIORITY[ev["priority"]][0])
                cat_rc = _rc(CATEGORY_COLOR[ev["category"]])

                dl_str, dl_rc = "", "dim white"
                if ev.get("deadline"):
                    days = (ev["deadline"] - today).days
                    if   days < 0:  dl_str, dl_rc = "OVERDUE", "red"
                    elif days == 0: dl_str, dl_rc = "TODAY",   "red"
                    elif days == 1: dl_str, dl_rc = "TMRW",    "yellow"
                    else:           dl_str, dl_rc = f"{days}d", "dim white"

                table.add_row(
                    time_str,
                    f"[{pri_rc}]{pri_label}[/]",
                    f"[{cat_rc}]{cat_icon}[/]",
                    ev["title"],
                    f"[{dl_rc}]{dl_str}[/]" if dl_str else "",
                    ev.get("location") or "",
                    key=str(ev["id"]),
                )

        self._refresh_sidebar(events, d)

    def _refresh_sidebar(self, events: list[dict], d: date) -> None:
        by_cat  = {c: 0 for c in CATEGORIES}
        n_crit  = sum(1 for e in events if e["priority"] == "critical")
        n_due   = sum(1 for e in events if e.get("deadline") == d)
        for ev in events:
            by_cat[ev["category"]] += 1

        def _li(n: int, label: str, color: str = "$text-muted") -> str:
            val = f"[{color}]{n:>2}[/]" if n else " –"
            return f"{val}  {label}"

        self.query_one("#leg-total",    Label).update(_li(len(events), "events"))
        self.query_one("#leg-critical", Label).update(_li(n_crit, "critical",  "$error"))
        self.query_one("#leg-due",      Label).update(_li(n_due,  "due today", "$warning"))
        self.query_one("#leg-class",    Label).update(_li(by_cat["class"],      "[C] class"))
        self.query_one("#leg-assign",   Label).update(_li(by_cat["assignment"], "[A] assign"))
        self.query_one("#leg-work",     Label).update(_li(by_cat["work"],       "[W] work"))
        self.query_one("#leg-meeting",  Label).update(_li(by_cat["meeting"],    "[M] meeting"))
        self.query_one("#leg-personal", Label).update(_li(by_cat["personal"],   "[P] personal"))