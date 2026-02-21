from textual.app import App, ComposeResult
from textual.widgets import Footer
from screens.dashboard import Dashboard
from widgets.header import Header


class Katonagari(App):
    theme = "dracula"
    def compose(self) -> ComposeResult:
        yield Footer()
    def on_mount(self) -> None:
        self.push_screen(Dashboard())
if __name__ == "__main__":
    app = Katonagari()
    app.run()