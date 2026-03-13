"""
schedule.py — Schedule tab widget.
Design: tab-style day nav, sidebar with boxed sections,
transparent rounded-border table panel, kbd footer.

Responsive: all widths are relative (1fr / %), Rule() for
separators, DayTabs use 1fr so they never overflow the nav bar,
modals cap at 90% so they stay inside any terminal size.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Rule, Select, Static

from databases.scheduleData import (
    CATEGORIES, CATEGORY_COLOR, CATEGORY_ICON,PRIORITY,
    add_event, delete_event, get_events_for_date,
    load_events, update_event,
)

# ── Rich color map for DataTable markup ───────────────────────────────────────
_RICH: dict[str, str] = {
    "$error":      "red",
    "$warning":    "yellow",
    "$primary":    "blue",
    "$success":    "green",
    "$accent":     "cyan",
    "$text-muted": "dim white",
}
def _rc(var: str) -> str:
    return _RICH.get(var, "white")


# ── Select options ─────────────────────────────────────────────────────────────
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


# ── Shared Rule style injected into each modal's DEFAULT_CSS ──────────────────
_MODAL_RULE_CSS = """
    Rule {
        color: $surface-lighten-2;
        margin: 0 1;
        height: 1;
    }
"""


# ══════════════════════════════════════════════════════════════════════════════
# Detail Modal
# ══════════════════════════════════════════════════════════════════════════════

class DetailModal(ModalScreen):
    BINDINGS = [("escape,enter,q", "dismiss_modal", "Close")]

    DEFAULT_CSS = """
    DetailModal { align: center middle; }

    #det-box {
        width: 90%;
        height: auto;
        border: round $surface-lighten-2;
        background: $background;
        padding: 0 0 1 0;
        overflow: hidden hidden;
    }
    #det-titlebar {
        height: 1;
        background: $primary 18%;
        color: $primary;
        text-style: bold;
        padding: 0 2;
        border-bottom: solid $surface-lighten-1;
        margin-bottom: 1;
    }
    .det-row  { height: 1; layout: horizontal; padding: 0 2; }
    .det-lbl  { width: 11; color: $text-muted; }
    .det-val  { width: 1fr; color: $text; overflow: hidden hidden; }
    .det-note {
        color: $text-muted; text-style: italic;
        padding: 0 2; margin-top: 1;
        overflow: hidden hidden;
    }
    .det-foot {
        color: $text-muted; text-align: center;
        margin-top: 1; padding: 0 2;
    }
    """ + _MODAL_RULE_CSS

    def __init__(self, event: dict) -> None:
        super().__init__()
        self._ev = event

    def compose(self) -> ComposeResult:
        ev = self._ev
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
            else:           dl_str = f"{ev['deadline'].strftime('%b %d')} ({days}d)"

        with Vertical(id="det-box"):
            yield Label(f" ◆ {ev['title']}", id="det-titlebar")
            with Horizontal(classes="det-row"):
                yield Label("Date",     classes="det-lbl")
                yield Label(f"{ev['date'].strftime('%A, %B')} {ev['date'].day}", classes="det-val")
            with Horizontal(classes="det-row"):
                yield Label("Time",     classes="det-lbl")
                yield Label(time_str,   classes="det-val")
            with Horizontal(classes="det-row"):
                yield Label("Priority", classes="det-lbl")
                yield Label(f"[{_rc(pri_color)}]{pri_label}[/]", classes="det-val", markup=True)
            with Horizontal(classes="det-row"):
                yield Label("Category", classes="det-lbl")
                yield Label(
                    f"[{_rc(cat_color)}]{cat_icon} {ev['category']}[/]",
                    classes="det-val", markup=True,
                )
            if ev.get("location"):
                with Horizontal(classes="det-row"):
                    yield Label("Location", classes="det-lbl")
                    yield Label(ev["location"], classes="det-val")
            if dl_str:
                with Horizontal(classes="det-row"):
                    yield Label("Deadline", classes="det-lbl")
                    yield Label(dl_str, classes="det-val")
            if ev.get("notes"):
                yield Rule()
                yield Label(f"  {ev['notes']}", classes="det-note")
            yield Rule()
            yield Label("Enter / Esc  ·  Close", classes="det-foot")

    def action_dismiss_modal(self) -> None:
        self.dismiss()


# ══════════════════════════════════════════════════════════════════════════════
# Confirm Modal
# ══════════════════════════════════════════════════════════════════════════════

class ConfirmModal(ModalScreen):
    BINDINGS = [("y,enter", "yes", "Yes"), ("n,escape", "no", "No")]

    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    #conf-box {
        width: 90%;
        height: 7;
        border: round $error;
        background: $background;
        padding: 1 2;
        align: center middle;
        layout: vertical;
        overflow: hidden hidden;
    }
    #conf-msg  { text-align: center; color: $text; margin-bottom: 1; }
    #conf-hint { text-align: center; color: $text-muted; }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._msg = message

    def compose(self) -> ComposeResult:
        with Vertical(id="conf-box"):
            yield Label(self._msg,                                id="conf-msg")
            yield Label("[ y / Enter ]  Yes    [ n / Esc ]  No", id="conf-hint")

    def action_yes(self) -> None: self.dismiss(True)
    def action_no(self)  -> None: self.dismiss(False)


# ══════════════════════════════════════════════════════════════════════════════
# Event Form Modal  (Add / Edit)
# ══════════════════════════════════════════════════════════════════════════════

class EventFormModal(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel"), ("ctrl+s", "confirm", "Save")]

    DEFAULT_CSS = """
    EventFormModal { align: center middle; }

    #form-box {
        width: 90%;
        height: auto;
        border: round $surface-lighten-2;
        background: $background;
        padding: 0 0 1 0;
        overflow: hidden hidden;
    }

    /* Title bar — matches TablePanel titlebar */
    #form-titlebar {
        height: 1;
        background: $primary 18%;
        color: $primary;
        text-style: bold;
        padding: 0 2;
        border-bottom: solid $surface-lighten-1;
        margin-bottom: 1;
    }

    /* Field rows */
    .f-row { height: 3; layout: horizontal; padding: 0 2; }
    .f-lbl { width: 11; content-align: left middle; color: $text-muted; }
    .f-inp { width: 1fr; }

    /* Error line */
    #form-error {
        color: $error;
        height: 1;
        text-align: center;
        padding: 0 2;
    }

    /* Hint below buttons */
    #form-hint {
        color: $text-muted;
        text-align: center;
        padding: 0 2;
        margin-top: 1;
    }

    /* Button row */
    #form-btns {
        layout: horizontal;
        height: 3;
        padding: 0 2;
        margin-top: 1;
    }

    /* Save — primary tint, round border */
    #btn-save {
        width: 1fr;
        margin-right: 1;
        background: $primary 12%;
        border: round $primary;
        color: $primary;
        text-style: bold;
    }
    #btn-save:hover { background: $primary 22%; border: round $primary; color: $primary; }
    #btn-save:focus { background: $primary 18%; border: round $primary; color: $primary; text-style: bold; }

    /* Cancel — subtle, round border */
    #btn-cancel {
        width: 1fr;
        background: transparent;
        border: round $surface-lighten-3;
        color: $text-muted;
    }
    #btn-cancel:hover { background: $surface 30%; border: round $surface-lighten-2; color: $text; }
    #btn-cancel:focus { background: $surface 20%; border: round $surface-lighten-2; color: $text-muted; }
    """ + _MODAL_RULE_CSS

    def __init__(self, event: dict | None = None, default_date: date | None = None) -> None:
        super().__init__()
        self._ev    = event
        self._ddate = default_date or date.today()
        self._mode  = "Edit" if event else "Add"

    def compose(self) -> ComposeResult:
        ev = self._ev or {}
        with Vertical(id="form-box"):
            yield Label(f" ◆ {self._mode} Event", id="form-titlebar")

            with Horizontal(classes="f-row"):
                yield Label("Title",    classes="f-lbl")
                yield Input(value=ev.get("title", ""), placeholder="Event title",
                            id="i-title", classes="f-inp")
            with Horizontal(classes="f-row"):
                yield Label("Date",     classes="f-lbl")
                yield Input(
                    value=ev["date"].isoformat() if ev.get("date") else self._ddate.isoformat(),
                    placeholder="YYYY-MM-DD", id="i-date", classes="f-inp",
                )
            with Horizontal(classes="f-row"):
                yield Label("Time",     classes="f-lbl")
                yield Input(value=ev.get("time", ""), placeholder="HH:MM",
                            id="i-time", classes="f-inp")
            with Horizontal(classes="f-row"):
                yield Label("End Time", classes="f-lbl")
                yield Input(value=ev.get("end_time") or "",
                            placeholder="HH:MM  (optional)", id="i-end", classes="f-inp")
            with Horizontal(classes="f-row"):
                yield Label("Priority", classes="f-lbl")
                yield Select(_PRI_OPTS, value=ev.get("priority", "medium"),
                             id="i-priority", classes="f-inp")
            with Horizontal(classes="f-row"):
                yield Label("Category", classes="f-lbl")
                yield Select(_CAT_OPTS, value=ev.get("category", "personal"),
                             id="i-category", classes="f-inp")
            with Horizontal(classes="f-row"):
                yield Label("Deadline", classes="f-lbl")
                yield Input(
                    value=ev["deadline"].isoformat() if ev.get("deadline") else "",
                    placeholder="YYYY-MM-DD  (optional)", id="i-deadline", classes="f-inp",
                )
            with Horizontal(classes="f-row"):
                yield Label("Notes",    classes="f-lbl")
                yield Input(value=ev.get("notes") or "",
                            placeholder="Notes  (optional)", id="i-notes", classes="f-inp")

            yield Label("", id="form-error")
            yield Rule()
            with Horizontal(id="form-btns"):
                yield Button("◆ Save",   id="btn-save",   variant="primary")
                yield Button("✕ Cancel", id="btn-cancel")
            yield Label("Ctrl+S  Save   ·   Esc  Cancel", id="form-hint")

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

        try:
            from textual.widgets._select import BLANK
        except ImportError:
            BLANK = None

        if BLANK is not None and priority is BLANK:
            err.update("Select a priority."); return
        if BLANK is not None and category is BLANK:
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


# ══════════════════════════════════════════════════════════════════════════════
# DayTab  — browser-style tab sitting on the nav border
# ══════════════════════════════════════════════════════════════════════════════

class DayTab(Button):
    DEFAULT_CSS = """
    DayTab {
        width: 1fr;
        height: 3;
        background: transparent;
        border: none;
        color: $text-muted;
        text-style: none;
        padding: 0;
        min-width: 5;
    }
    DayTab:hover { background: $surface 30%; color: $text; }

    DayTab.selected {
        background: $background;
        border-top: tall $surface-lighten-2;
        border-left: tall $surface-lighten-2;
        border-right: tall $surface-lighten-2;
        color: $primary;
        text-style: bold;
    }

    DayTab.today { color: $warning; }
    DayTab.selected.today {
        color: $warning;
        border-top: tall $warning 40%;
        border-left: tall $warning 20%;
        border-right: tall $warning 20%;
    }
    """

    def __init__(self, d: date, selected: bool = False) -> None:
        label = f"{d.strftime('%a')} {d.day}"
        super().__init__(label, id=f"day-{d.isoformat()}")
        self._date = d
        if selected:
            self.add_class("selected")
        if d == date.today():
            self.add_class("today")

    @property
    def day_date(self) -> date:
        return self._date


# ══════════════════════════════════════════════════════════════════════════════
# AllTab  — special "All Events" tab in the nav strip
# ══════════════════════════════════════════════════════════════════════════════

class AllTab(Button):
    """Fixed-width 'All' tab that shows every event across all dates."""

    DEFAULT_CSS = """
    AllTab {
        width: 7;
        height: 3;
        background: transparent;
        border: none;
        color: $text-muted;
        text-style: none;
        padding: 0;
        min-width: 5;
    }
    AllTab:hover { background: $surface 30%; color: $text; }

    AllTab.selected {
        background: $background;
        border-top: tall $accent 60%;
        border-left: tall $accent 30%;
        border-right: tall $accent 30%;
        color: $accent;
        text-style: bold;
    }
    """

    def __init__(self, selected: bool = False) -> None:
        super().__init__("All ✦", id="tab-all")
        if selected:
            self.add_class("selected")


# ══════════════════════════════════════════════════════════════════════════════
# SidebarBox  — rounded-border section panel
# ══════════════════════════════════════════════════════════════════════════════

class SidebarBox(Widget):
    DEFAULT_CSS = """
    SidebarBox {
        width: 100%;
        height: auto;
        border: round $surface-lighten-2;
        padding: 0 1;
        margin-bottom: 1;
        background: $surface 30%;
        overflow: hidden hidden;
    }
    """

    def __init__(self, title: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.border_title = title


# ══════════════════════════════════════════════════════════════════════════════
# TablePanel  — rounded border, transparent interior
# ══════════════════════════════════════════════════════════════════════════════

class TablePanel(Widget):
    DEFAULT_CSS = """
    TablePanel {
        width: 1fr;
        height: 1fr;
        border: round $surface-lighten-2;
        background: transparent;
        layout: vertical;
        padding: 0 1;
        overflow: hidden hidden;
    }
    """


# ══════════════════════════════════════════════════════════════════════════════
# Main Schedule Widget
# ══════════════════════════════════════════════════════════════════════════════

class Schedule(Widget):

    BINDINGS = [
        Binding("a",     "add",      "Add",    show=False),
        Binding("e",     "edit",     "Edit",   show=False),
        Binding("d",     "delete",   "Delete", show=False),
        Binding("enter", "detail",   "Detail", show=False),
        Binding("left",  "prev_day", "← Day",  show=False),
        Binding("right", "next_day", "→ Day",  show=False),
        Binding("h",     "prev_day", "← Day",  show=False),
        Binding("l",     "next_day", "→ Day",  show=False),
        Binding("r",     "reload",   "Reload", show=False),
    ]

    DEFAULT_CSS = """
    Schedule {
        layout: vertical;
        height: 1fr;
        width: 100%;
        background: $background;
        overflow: hidden hidden;
    }

    /* ── Tab nav ── */
    #tab-nav {
        height: 3;
        width: 100%;
        layout: horizontal;
        background: $background;
        border-bottom: solid $surface-lighten-1;
        padding: 0 1;
        align: left bottom;
        overflow: hidden hidden;
    }
    #nav-label {
        width: auto;
        height: 3;
        content-align: left middle;
        color: $primary;
        text-style: bold;
        padding: 0 1;
        border-right: solid $surface-lighten-1;
        margin-right: 1;
    }
    #tab-strip {
        height: 3;
        layout: horizontal;
        width: 1fr;
        align: left bottom;
        overflow: hidden hidden;
    }

    /* ── Body ── */
    #sched-body {
        layout: horizontal;
        height: 1fr;
        width: 100%;
        padding: 1;
        overflow: hidden hidden;
    }

    /* ── Sidebar ── */
    #sched-sidebar {
        width: 22;
        height: 100%;
        layout: vertical;
        overflow: hidden hidden;
    }

    /* Sidebar rows */
    .sb-row { height: 1; layout: horizontal; }
    .sb-lbl { width: 1fr; color: $text-muted; overflow: hidden hidden; }
    .sb-val { width: 3;   text-align: right; text-style: bold; }

    .val-crit { color: $error; }
    .val-warn { color: $warning; }
    .val-info { color: $primary; }
    .val-ok   { color: $success; }
    .val-dim  { color: $text-muted; }

    .dot-crit { color: $error;   height: 1; overflow: hidden hidden; }
    .dot-high { color: $warning; height: 1; overflow: hidden hidden; }
    .dot-med  { color: $primary; height: 1; overflow: hidden hidden; }
    .dot-low  { color: $success; height: 1; overflow: hidden hidden; }

    /* ── TablePanel interior ── */
    #tbl-titlebar {
        height: 1;
        layout: horizontal;
        background: $surface 25%;
        border-bottom: solid $surface-lighten-1;
        padding: 0 1;
        overflow: hidden hidden;
    }
    #tbl-label {
        width: 1fr;
        color: $primary;
        text-style: bold;
        overflow: hidden hidden;
    }
    #tbl-count {
        width: auto;
        color: $text-muted;
        text-style: italic;
    }

    #event-table {
        height: 1fr;
        width: 100%;
        background: transparent;
        margin: 1 0;
    }
    #no-events {
        color: $text-muted;
        text-style: italic;
        text-align: center;
        padding: 2 0;
    }

    /* ── Footer ── */
    #key-hints {
        height: 1;
        width: 100%;
        background: $surface 25%;
        border-top: solid $surface-lighten-1;
        padding: 0 1;
        overflow: hidden hidden;
        color: $text-muted;
    }
    """

    selected_date: reactive[date] = reactive(date.today)
    _all_mode: reactive[bool]     = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self._events: list[dict]         = []
        self._current_events: list[dict] = []
        # Track which Monday starts the currently displayed 7-tab week
        self._week_start: date = self._monday_of(date.today())

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _monday_of(d: date) -> date:
        """Return the Monday of the ISO week that contains *d*."""
        return d - timedelta(days=d.weekday())

    def _week_dates(self, week_start: date | None = None) -> list[date]:
        """Return the 7 dates for the displayed week."""
        ws = week_start if week_start is not None else self._week_start
        return [ws + timedelta(days=i) for i in range(7)]

    def _date_in_current_tabs(self, d: date) -> bool:
        return d in self._week_dates()

    # ─── Tab strip management ─────────────────────────────────────────────────

    def _rebuild_tabs(self, week_start: date, selected: date, all_selected: bool = False) -> None:
        """Tear down all tabs and remount a fresh AllTab + 7-day week."""
        self._week_start = week_start
        strip = self.query_one("#tab-strip", Horizontal)
        # Remove existing tabs
        for tab in self.query(DayTab):
            tab.remove()
        for tab in self.query(AllTab):
            tab.remove()
        # Mount AllTab first, then the 7-day tabs
        strip.mount(AllTab(selected=all_selected))
        for d in self._week_dates(week_start):
            strip.mount(DayTab(d, selected=(not all_selected and d == selected)))

    # ─── Compose ──────────────────────────────────────────────────────────────
    def compose(self) -> ComposeResult:

        with Horizontal(id="tab-nav"):
            yield Label("◆ SCHEDULE", id="nav-label")
            yield Horizontal(id="tab-strip")

        with Horizontal(id="sched-body"):

            with Vertical(id="sched-sidebar"):
                with SidebarBox("Overview"):
                    with Horizontal(classes="sb-row"):
                        yield Label("Events",   classes="sb-lbl")
                        yield Label("", id="leg-total",    classes="sb-val val-dim")
                    with Horizontal(classes="sb-row"):
                        yield Label("Critical", classes="sb-lbl")
                        yield Label("", id="leg-critical", classes="sb-val val-crit")
                    with Horizontal(classes="sb-row"):
                        yield Label("Due",      classes="sb-lbl")
                        yield Label("", id="leg-due",      classes="sb-val val-warn")

                with SidebarBox("Categories"):
                    with Horizontal(classes="sb-row"):
                        yield Label("[C] Class",    classes="sb-lbl")
                        yield Label("", id="leg-class",    classes="sb-val val-info")
                    with Horizontal(classes="sb-row"):
                        yield Label("[A] Assign",   classes="sb-lbl")
                        yield Label("", id="leg-assign",   classes="sb-val val-crit")
                    with Horizontal(classes="sb-row"):
                        yield Label("[W] Work",     classes="sb-lbl")
                        yield Label("", id="leg-work",     classes="sb-val val-ok")
                    with Horizontal(classes="sb-row"):
                        yield Label("[M] Meet",     classes="sb-lbl")
                        yield Label("", id="leg-meeting",  classes="sb-val val-warn")
                    with Horizontal(classes="sb-row"):
                        yield Label("[P] Personal", classes="sb-lbl")
                        yield Label("", id="leg-personal", classes="sb-val val-dim")

                with SidebarBox("Priority"):
                    yield Label("[$error]●[/] Critical",  classes="dot-crit", markup=True)
                    yield Label("[$warning]●[/] High",    classes="dot-high", markup=True)
                    yield Label("[$primary]○[/] Medium",  classes="dot-med",  markup=True)
                    yield Label("[$success]○[/] Low",     classes="dot-low",  markup=True)

            with TablePanel():
                with Horizontal(id="tbl-titlebar"):
                    yield Label("", id="tbl-label")
                    yield Label("", id="tbl-count")
                yield DataTable(
                    id="event-table",
                    show_header=True,
                    cursor_type="row",
                    zebra_stripes=False,
                )
                yield Label(
                    "No events  ·  press [a] to add one",
                    id="no-events",
                )

        yield Static(
            " [a] Add │ [e] Edit │ [d] Del │ [↵] Detail │ [←→] Day │ [↑↓] Nav │ [h/l] Vim │ [r] Reload",
            id="key-hints",
        )

    def on_mount(self) -> None:
        self._events = load_events()

        strip = self.query_one("#tab-strip", Horizontal)
        strip.mount(AllTab(selected=False))
        for i, d in enumerate(self._week_dates()):
            strip.mount(DayTab(d, selected=(i == 0)))

        table = self.query_one("#event-table", DataTable)
        table.add_columns("TIME", "PRI", "CAT", "TITLE", "DEADLINE", "LOCATION")

        self._refresh_events()

    # ─── Public API ───────────────────────────────────────────────────────────

    def go_to_date(self, d: date) -> None:
        """Jump to any date — rebuilds the week strip if needed."""
        self._all_mode = False
        if not self._date_in_current_tabs(d):
            self._rebuild_tabs(week_start=self._monday_of(d), selected=d)
        else:
            for tab in self.query(AllTab):
                tab.remove_class("selected")
            for tab in self.query(DayTab):
                tab.remove_class("selected")
                if tab.day_date == d:
                    tab.add_class("selected")
        self.selected_date = d
        self._refresh_events()

    # ─── Tab / day nav ────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button
        if isinstance(btn, AllTab):
            for t in self.query(DayTab):
                t.remove_class("selected")
            btn.add_class("selected")
            self._all_mode = True
            self._refresh_events()
            return
        if not isinstance(btn, DayTab):
            return
        for t in self.query(AllTab):
            t.remove_class("selected")
        for t in self.query(DayTab):
            t.remove_class("selected")
        btn.add_class("selected")
        self._all_mode = False
        self.selected_date = btn.day_date
        self._refresh_events()

    def action_prev_day(self) -> None:
        self.go_to_date(self.selected_date - timedelta(days=1))

    def action_next_day(self) -> None:
        self.go_to_date(self.selected_date + timedelta(days=1))

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    def action_add(self) -> None:
        default = self.selected_date if not self._all_mode else date.today()
        def cb(result: dict | None) -> None:
            if result is not None:
                add_event(self._events, result)
                self.go_to_date(result["date"])
        self.app.push_screen(EventFormModal(default_date=default), cb)

    def action_edit(self) -> None:
        ev = self._cursor_event()
        if ev is None:
            return
        def cb(result: dict | None) -> None:
            if result is not None:
                update_event(self._events, ev["id"], result)
                self.go_to_date(result["date"])
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

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _cursor_event(self) -> dict | None:
        if not self._current_events:
            return None
        idx = self.query_one("#event-table", DataTable).cursor_row
        if 0 <= idx < len(self._current_events):
            return self._current_events[idx]
        return None

    def _refresh_events(self) -> None:
        # ── Fetch events ──────────────────────────────────────────────────────
        if self._all_mode:
            events = sorted(self._events, key=lambda e: (e["date"], e["time"]))
        else:
            d      = self.selected_date
            events = get_events_for_date(self._events, d)
        self._current_events = events

        table = self.query_one("#event-table", DataTable)
        no_ev = self.query_one("#no-events",   Label)
        lbl   = self.query_one("#tbl-label",   Label)
        count = self.query_one("#tbl-count",   Label)

        # ── Title bar ─────────────────────────────────────────────────────────
        if self._all_mode:
            lbl.update(" ✦ All Events")
        else:
            d     = self.selected_date
            today = date.today()
            if   d == today:                prefix = "Today"
            elif d == today + timedelta(1): prefix = "Tomorrow"
            elif d == today - timedelta(1): prefix = "Yesterday"
            else:                           prefix = ""
            weekday = d.strftime("%A")
            mon_day = f"{d.strftime('%B')} {d.day}"
            sep     = "  ·  " if prefix else ""
            lbl.update(f" {prefix}{sep}{weekday}, {mon_day}")

        count.update(
            f"{len(events)} event{'s' if len(events) != 1 else ''}" if events else ""
        )

        # ── Rebuild columns based on mode ─────────────────────────────────────
        table.clear(columns=True)
        if self._all_mode:
            table.add_columns("DATE", "TIME", "PRI", "CAT", "TITLE", "DEADLINE", "LOCATION")
        else:
            table.add_columns("TIME", "PRI", "CAT", "TITLE", "DEADLINE", "LOCATION")

        if not events:
            table.display = False
            no_ev.display = True
            self._refresh_sidebar([], self.selected_date)
            return

        table.display = True
        no_ev.display = False

        today     = date.today()
        now_str   = datetime.now().strftime("%H:%M")

        for ev in events:
            time_str = f"{ev['time']}─{ev['end_time']}" if ev.get("end_time") else ev["time"]

            _, pri_label = PRIORITY[ev["priority"]]
            pri_rc   = _rc(PRIORITY[ev["priority"]][0])
            cat_icon = CATEGORY_ICON[ev["category"]]
            cat_rc   = _rc(CATEGORY_COLOR[ev["category"]])

            dl_str, dl_rc = "", "dim white"
            if ev.get("deadline"):
                days = (ev["deadline"] - today).days
                if   days < 0:  dl_str, dl_rc = "OVERDUE",  "red"
                elif days == 0: dl_str, dl_rc = "TODAY",    "red"
                elif days == 1: dl_str, dl_rc = "TOMORROW", "yellow"
                elif days <= 3: dl_str, dl_rc = f"{days}d", "yellow"
                else:           dl_str, dl_rc = f"{days}d", "dim white"

            end_t  = ev.get("end_time") or "99:99"
            is_now = ev["date"] == today and ev["time"] <= now_str <= end_t

            if is_now:
                time_cell  = f"[yellow bold]{time_str}[/]"
                title_cell = f"[bold yellow]{ev['title']}[/]"
            else:
                time_cell  = f"[dim]{time_str}[/]"
                title_cell = ev["title"]

            # Date cell — colored by proximity in All mode
            ev_date    = ev["date"]
            days_away  = (ev_date - today).days
            if   ev_date == today:    date_cell = f"[yellow bold]{ev_date.strftime('%b %d')}[/]"
            elif days_away < 0:       date_cell = f"[dim]{ev_date.strftime('%b %d')}[/]"
            elif days_away <= 3:      date_cell = f"[cyan]{ev_date.strftime('%b %d')}[/]"
            else:                     date_cell = f"[dim white]{ev_date.strftime('%b %d')}[/]"

            row_cells = (
                [date_cell, time_cell] if self._all_mode else [time_cell]
            ) + [
                f"[{pri_rc}]{pri_label}[/]",
                f"[{cat_rc}]{cat_icon}[/]",
                title_cell,
                f"[{dl_rc}]{dl_str}[/]" if dl_str else "",
                f"[dim]{ev.get('location') or ''}[/]",
            ]

            table.add_row(*row_cells, key=str(ev["id"]))

        sidebar_date = self.selected_date if not self._all_mode else today
        self._refresh_sidebar(events, sidebar_date)

    def _refresh_sidebar(self, events: list[dict], d: date) -> None:
        by_cat = {c: 0 for c in CATEGORIES}
        n_crit = sum(1 for e in events if e["priority"] == "critical")
        # In all-mode count events with deadline today; in day-mode count events due on d
        due_date = date.today() if self._all_mode else d
        n_due  = sum(1 for e in events if e.get("deadline") == due_date)
        for ev in events:
            by_cat[ev["category"]] += 1

        def _fmt(n: int) -> str:
            return f"{n:>2}" if n else " –"

        self.query_one("#leg-total",    Label).update(_fmt(len(events)))
        self.query_one("#leg-critical", Label).update(_fmt(n_crit))
        self.query_one("#leg-due",      Label).update(_fmt(n_due))
        self.query_one("#leg-class",    Label).update(_fmt(by_cat["class"]))
        self.query_one("#leg-assign",   Label).update(_fmt(by_cat["assignment"]))
        self.query_one("#leg-work",     Label).update(_fmt(by_cat["work"]))
        self.query_one("#leg-meeting",  Label).update(_fmt(by_cat["meeting"]))
        self.query_one("#leg-personal", Label).update(_fmt(by_cat["personal"]))