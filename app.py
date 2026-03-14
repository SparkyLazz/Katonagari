from textual.app import App, ComposeResult
from textual.widgets import Footer
from screens.dashboard import Dashboard


class Katonagari(App):
    CSS = """
    /* Global colors and styles */
    * {
        transition: background 500ms;
    }

    App {
        background: #1e1e2e;
        color: #cdd6f4;
    }

    /* Override Textual variables */
    Screen {
        background: #1e1e2e;
    }

    /* Colors used by Panel (Catppuccin Mocha) */
    $primary: #f5c2e7;
    $accent: #89b4fa;
    $secondary: #b4befe;
    $success: #a6e3a1;
    $warning: #fab387;
    $error: #f38ba8;
    $surface: #313244;
    $background: #1e1e2e;
    $text-muted: #a6adc8;
    $text-disabled: #6c7086;
    """

    def compose(self) -> ComposeResult:
        yield Footer(show_command_palette=True)
    def on_mount(self) -> None:
        self.push_screen(Dashboard())
if __name__ == "__main__":
    app = Katonagari()
    app.run()