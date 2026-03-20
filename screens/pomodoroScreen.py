from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, Label, TabbedContent, TabPane

from services.pomodoroService import PomodoroService
from widgets.pomodoro.analysis import PomodoroAnalysis
from widgets.pomodoro.overview import PomodoroOverview
from widgets.pomodoro.timer import PomodoroTimer


class Pomodoro(Widget):
    DEFAULT_CSS = """
        Pomodoro  { padding: 1; height: 1fr; }
        Tab       { margin-right: 4; }
        #overview { height: 1fr; }
        #pomodoro { height: 1fr; }
        #analysis { height: 1fr; }
    """

    def __init__(self, service: PomodoroService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = service

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Overview", id="overview"):
                yield PomodoroOverview(service=self._svc, id="pom-overview")
            with TabPane("Pomodoro", id="pomodoro"):
                yield PomodoroTimer(service=self._svc, id="pom-timer")
            with TabPane("Analysis", id="analysis"):
                yield PomodoroAnalysis(service=self._svc, id="pom-analysis")

    def on_pomodoro_timer_session_logged(self, _: PomodoroTimer.SessionLogged) -> None:
        """Refresh both Overview and Analysis after every saved session."""
        try:
            self.query_one(PomodoroOverview).refresh_data()
        except Exception:
            pass
        try:
            self.query_one(PomodoroAnalysis).refresh_data()
        except Exception:
            pass


class PomodoroScreen(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = PomodoroService()

    def compose(self) -> ComposeResult:
        yield Pomodoro(self._svc)
        yield Footer()