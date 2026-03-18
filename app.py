from textual.app import App
from textual.binding import Binding
from screens.financeScreen import FinanceScreen
from screens.pomodoroScreen import PomodoroScreen


class Katonagari(App):
    BINDINGS = [
        Binding("f", "switch_to_finance", "Finance"),
        Binding("p", "switch_to_pomodoro", "Pomodoro"),
    ]

    def on_mount(self) -> None:
        self.push_screen(FinanceScreen())

    def action_switch_to_finance(self) -> None:
        self.switch_screen(FinanceScreen())

    def action_switch_to_pomodoro(self) -> None:
        self.switch_screen(PomodoroScreen())


if __name__ == "__main__":
    app = Katonagari()
    app.run()