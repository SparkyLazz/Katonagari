from textual.app import App, ComposeResult
from textual.widgets import Footer, TabbedContent, TabPane, Label, Static, Button

from screens.login import Login
from widgets.header import Header

class Katonagari(App):
    theme = "dracula"
    def compose(self) -> ComposeResult:
       yield Header()
       yield Footer(show_command_palette=True)

    def on_mount(self) -> None:
        self.push_screen(Login())

if __name__ == '__main__':
    app = Katonagari()
    app.run()