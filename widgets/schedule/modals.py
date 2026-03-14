from __future__ import annotations
from datetime import date

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Rule, Select

from databases.scheduleData import (
    CATEGORY_COLOR, CATEGORY_ICON, PRIORITY,
)
from .constants import (
    _rc, _PRI_OPTS, _CAT_OPTS, _MODAL_RULE_CSS
)

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
                yield Input(value=ev.get("title") or "", placeholder="Class, Work, etc.", id="i-title", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Date",     classes="f-lbl")
                yield Input(value=(ev["date"].isoformat() if ev.get("date") else self._ddate.isoformat()),
                            placeholder="YYYY-MM-DD", id="i-date", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Time",     classes="f-lbl")
                yield Input(value=ev.get("time") or "", placeholder="HH:MM (24h)", id="i-time", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("End Time", classes="f-lbl")
                yield Input(value=ev.get("end_time") or "", placeholder="HH:MM (Optional)", id="i-etime", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Priority", classes="f-lbl")
                yield Select(_PRI_OPTS, value=ev.get("priority", "medium"), id="i-pri", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Category", classes="f-lbl")
                yield Select(_CAT_OPTS, value=ev.get("category", "class"), id="i-cat", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Location", classes="f-lbl")
                yield Input(value=ev.get("location") or "", placeholder="Optional", id="i-loc", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Deadline", classes="f-lbl")
                yield Input(value=(ev["deadline"].isoformat() if ev.get("deadline") else ""),
                            placeholder="YYYY-MM-DD (Optional)", id="i-dead", classes="f-inp")

            with Horizontal(classes="f-row"):
                yield Label("Notes",    classes="f-lbl")
                yield Input(value=ev.get("notes") or "", placeholder="Optional notes", id="i-notes", classes="f-inp")

            yield Label("", id="form-error")
            yield Rule()
            with Horizontal(id="form-btns"):
                yield Button("◆ Save",   id="btn-save", variant="primary")
                yield Button("✕ Cancel", id="btn-cancel")
            yield Label("Ctrl+S  Save   ·   Esc  Cancel", id="form-hint")

    def action_confirm(self) -> None: self._try_save()
    def action_cancel(self)  -> None: self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":   self._try_save()
        elif event.button.id == "btn-cancel": self.dismiss(None)

    def _try_save(self) -> None:
        err = self.query_one("#form-error", Label)
        title = self.query_one("#i-title", Input).value.strip()
        d_str = self.query_one("#i-date",  Input).value.strip()
        t_str = self.query_one("#i-time",  Input).value.strip()
        et_str= self.query_one("#i-etime", Input).value.strip() or None
        pri   = self.query_one("#i-pri",   Select).value
        cat   = self.query_one("#i-cat",   Select).value
        loc   = self.query_one("#i-loc",   Input).value.strip() or None
        dl_str= self.query_one("#i-dead",  Input).value.strip() or None
        notes = self.query_one("#i-notes", Input).value.strip() or None

        if not title: err.update("Title is required."); return
        if not t_str: err.update("Time is required.");  return

        try:
            ev_date = date.fromisoformat(d_str)
        except ValueError:
            err.update("Invalid Date (YYYY-MM-DD)"); return

        deadline = None
        if dl_str:
            try:
                deadline = date.fromisoformat(dl_str)
            except ValueError:
                err.update("Invalid Deadline (YYYY-MM-DD)"); return

        # Validate time HH:MM
        for ts in [t_str, et_str]:
            if ts:
                try:
                    import time
                    time.strptime(ts, "%H:%M")
                except ValueError:
                    err.update(f"Invalid Time format: {ts}"); return

        result = {
            "title": title, "date": ev_date, "time": t_str,
            "end_time": et_str, "priority": str(pri), "category": str(cat),
            "location": loc, "deadline": deadline, "notes": notes,
        }
        self.dismiss(result)
