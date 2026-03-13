from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane

from widgets.header import Header
from widgets.home import Home, SwitchToSchedule
from widgets.finance import Finance
from widgets.schedule import Schedule


class Dashboard(Screen):
    CSS = """
    Tabs { align: center middle; width: 100%; }
    Tab  { width: auto; padding: 0 4; }
    TabbedContent { height: 1fr; }
    Home, Finance, Schedule { height: 1fr; width: 100%; padding: 0 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Home",     id="home"):
                yield Home()
            with TabPane("Finance",  id="finance"):
                yield Finance()
            with TabPane("Schedule", id="schedule"):
                yield Schedule()

    def on_switch_to_schedule(self, message: SwitchToSchedule) -> None:
        """Received when user clicks an event row in the Home ScheduleBox."""
        self.query_one(TabbedContent).active = "schedule"
        self.query_one(Schedule).go_to_date(message.target_date)