from datetime import datetime, timedelta, date

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Center
from textual.widget import Widget
from textual.widgets import (
    Input, RadioSet, RadioButton,
    Label, Digits, ProgressBar, DataTable
)

from services.pomodoroService import PomodoroService, Session as PomSession


# ─────────────────────────────────────────────
# INPUT COMPONENTS
# ─────────────────────────────────────────────

class Session(Widget):
    DEFAULT_CSS = """
    Session {
        border: round $success;
        padding: 1;
        height: 7;
    }
    """
    def compose(self) -> ComposeResult:
        self.border_title = "Session"
        yield Input(placeholder="Session Name", id="session-name")


class Subject(Widget):
    DEFAULT_CSS = """
    Subject {
        border: round $primary;
        padding: 1;
        height: 9;
    }
    """
    def compose(self) -> ComposeResult:
        self.border_title = "Subject"
        with RadioSet(id="subject-set"):
            yield RadioButton("Coding", value=True)
            yield RadioButton("Math")
            yield RadioButton("Reading")


class Duration(Widget):
    DEFAULT_CSS = """
    Duration {
        border: round $accent;
        padding: 1;
        height: 9;
    }
    """
    def compose(self) -> ComposeResult:
        self.border_title = "Duration"
        with RadioSet(id="duration-set"):
            yield RadioButton("25 Minutes", value=True)
            yield RadioButton("50 Minutes")
            yield RadioButton("60 Minutes")


# ─────────────────────────────────────────────
# MAIN DISPLAY
# ─────────────────────────────────────────────

class PomodoroMain(Widget):
    DEFAULT_CSS = """
    PomodoroMain {
        border: round $primary;
        height: 12;
        padding: 1;
    }
    #clock {
        width: auto;
    }
    #session-text {
        color: $success;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "Pomodoro"

        with Center():
            yield Digits("25:00", id="clock")

        with Center():
            yield Label("S = Start | P = Pause | R = Resume | E = End")

        with Center():
            yield Label("- Focus Session -", id="session-text")

        with Center():
            yield ProgressBar(total=25 * 60, show_eta=False, show_percentage=False)


class Log(Widget):
    DEFAULT_CSS = """
    Log {
        border: round $success;
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "Session Log"
        yield DataTable()


# ─────────────────────────────────────────────
# CORE TIMER (THIS IS THE BRAIN)
# ─────────────────────────────────────────────

class PomodoroTimer(Widget):
    DEFAULT_CSS = """
        #input-box {
            width: 30;
    }
    """
    BINDINGS = [
        ("s", "start", "Start"),
        ("p", "pause", "Pause"),
        ("r", "resume", "Resume"),
        ("e", "end", "End"),
    ]

    def __init__(self, *, service: PomodoroService, **kwargs):
        super().__init__(**kwargs)

        self._svc = service

        # STATE
        self._state = "idle"  # idle | running | paused
        self._duration = 25 * 60
        self._remaining = self._duration

        self._start_time: datetime | None = None
        self._pause_time: datetime | None = None
        self._timer = None

    # ─────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="input-box"):
                yield Session()
                yield Subject()
                yield Duration()

            with Vertical(id="output-box"):
                yield PomodoroMain()
                yield Log()

    # ─────────────────────────────────────────
    # KEY ACTIONS
    # ─────────────────────────────────────────

    def action_start(self):
        if self._state == "running":
            return

        self._state = "running"
        self._start_time = datetime.now()
        self._remaining = self._duration

        self._start_tick()

    def action_pause(self):
        if self._state != "running":
            return

        self._state = "paused"
        self._pause_time = datetime.now()

        if self._timer:
            self._timer.stop()

    def action_resume(self):
        if self._state != "paused":
            return

        pause_duration = (datetime.now() - self._pause_time).total_seconds()
        self._start_time += timedelta(seconds=pause_duration)

        self._state = "running"
        self._start_tick()

    def action_end(self):
        # SAVE SESSION
        if self._state == "running":
            minutes_done = (self._duration - self._remaining) // 60

            if minutes_done > 0:
                subject = self._get_selected_subject()

                self._svc.add(PomSession(
                    date=date.today().isoformat(),
                    start=self._start_time.strftime("%H:%M"),
                    duration=int(minutes_done),
                    type="Focus",
                    subject=subject,
                ))

        self._state = "idle"
        self._remaining = self._duration

        if self._timer:
            self._timer.stop()

        self._update_display()

    # ─────────────────────────────────────────
    # TIMER LOOP
    # ─────────────────────────────────────────

    def _start_tick(self):
        self._timer = self.set_interval(1, self._tick)

    def _tick(self):
        if self._state != "running":
            return

        elapsed = (datetime.now() - self._start_time).total_seconds()
        self._remaining = max(0, self._duration - int(elapsed))

        if self._remaining == 0:
            self.action_end()
            return

        self._update_display()

    # ─────────────────────────────────────────
    # UI UPDATE
    # ─────────────────────────────────────────

    def _update_display(self):
        minutes, seconds = divmod(self._remaining, 60)
        time_str = f"{minutes:02}:{seconds:02}"

        clock = self.query_one("#clock", Digits)
        clock.update(time_str)

        bar = self.query_one(ProgressBar)
        bar.update(total=self._duration, progress=self._duration - self._remaining)

    # ─────────────────────────────────────────
    # INPUT HANDLING
    # ─────────────────────────────────────────

    def on_radio_set_changed(self, event: RadioSet.Changed):
        rs_id = event.radio_set.id
        label = event.pressed.label

        if rs_id == "duration-set":
            if "25" in label:
                self._duration = 25 * 60
            elif "50" in label:
                self._duration = 50 * 60
            elif "60" in label:
                self._duration = 60 * 60

            self._remaining = self._duration
            self._update_display()

    def _get_selected_subject(self) -> str:
        rs = self.query_one("#subject-set", RadioSet)
        for btn in rs.buttons:
            if btn.value:
                return btn.label
        return "Coding"