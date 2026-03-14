from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import ContentSwitcher

from widgets.home import Home, SwitchToSchedule
from widgets.finance import Finance
from widgets.schedule import Schedule
from widgets.sidebar import Sidebar


class Dashboard(Screen):
    CSS = """
    Dashboard {
        layout: horizontal;
        background: $background;
        padding: 1 2;
    }

    #main-content {
        width: 1fr;
        height: 100%;
        margin-left: 2;
    }

    /* Transition effect for switcher could be added here if Textual supported it easily, 
       but for now we just ensure it's clean. */
    """

    def compose(self) -> ComposeResult:
        yield Sidebar()
        with ContentSwitcher(id="main-content", initial="home"):
            yield Home(id="home")
            yield Finance(id="finance")
            yield Schedule(id="schedule")

    def on_sidebar_switch(self, message: Sidebar.Switch) -> None:
        """Handle navigation switch from sidebar."""
        self.query_one(ContentSwitcher).current = message.target_id

    def on_switch_to_schedule(self, message: SwitchToSchedule) -> None:
        """Received when user clicks an event row in the Home ScheduleBox."""
        self.query_one(ContentSwitcher).current = "schedule"
        self.query_one(Sidebar).set_active("schedule")
        # Ensure the schedule widget jumps to the correct date
        self.query_one(Schedule).go_to_date(message.target_date)