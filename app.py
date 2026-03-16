from textual.app import App
from screens.financeScreen import FinanceScreen

class Katonagari(App):
    def on_mount(self) -> None:
        self.push_screen(FinanceScreen())


if __name__ == "__main__":
    app = Katonagari()
    app.run()