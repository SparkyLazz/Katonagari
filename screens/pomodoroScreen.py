from textual.app import ComposeResult
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, Label, TabbedContent, TabPane

class Pomodoro(Widget):
    DEFAULT_CSS = """
        Pomodoro  { padding: 1; }
        Tab         { margin-right: 4; }
        #overview   { height: 1fr; }
        #pomodoro   { height: 1fr; }
        #analysis   { height: 1fr; }
        """

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Overview", id="overview"):
                yield Label("Pomodoro")
            with TabPane("Pomodoro", id="pomodoro"):
                yield Label("Pomodoro")
            with TabPane("Analysis", id="analysis"):
                yield Label("Pomodoro")

class PomodoroScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Pomodoro()
        yield Footer()