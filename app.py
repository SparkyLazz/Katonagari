from textual.app import App, ComposeResult
from textual.widgets import Footer
from widgets.header import Header

class Katonagari(App):
    theme = "dracula"
    def compose(self) -> ComposeResult:
       yield Header()
       yield Footer(show_command_palette=True)

if __name__ == '__main__':
    app = Katonagari()
    app.run()