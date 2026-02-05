from rich.align import Align
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static
from textual.containers import Container, Center
from Utils.Panel import Panel


class Katonagari(App):
    def compose(self) -> ComposeResult:
        yield Panel(
            "katonagari",
            "V1.0",
            Static(Align.center("An Personal Ultimate Productivity by Rui"))
        )

if __name__ == "__main__":
    app = Katonagari()
    app.run()