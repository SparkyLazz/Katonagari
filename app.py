from textual.app import App, ComposeResult
from textual.widgets import Footer
from screens.dashboard import Dashboard


class Katonagari(App):
    def compose(self) -> ComposeResult:
        yield Footer(show_command_palette=True)
    def on_mount(self) -> None:
        self.push_screen(Dashboard())
if __name__ == "__main__":
    app = Katonagari()
    app.run()