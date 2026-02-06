from textual.containers import Container
from textual.screen import Screen
from textual.widgets import OptionList, Input
from textual.app import App, ComposeResult


class MainMenu(Screen):
    CSS = """
    MainMenu {
        align: center middle;
    }
    #menu {
        width: 40;
        height: auto;
        margin: 1;
        padding: 1 2;
        border: round $primary;
        background: transparent;
    }
    """

    def compose(self) -> ComposeResult:
        menu = OptionList(
            "Finance Manager",
            "Task Manager",
            "Settings",
            "Exit",
            id="menu",
        )
        menu.border_title = "Main Menu"
        yield menu


class Login(Screen):
    # Set your username and password here
    VALID_USERNAME = "SparkyLazz"
    VALID_PASSWORD = "Mycodeis9!"

    CSS = """
    Login {
        align: center middle;
    }

    #login-box {
        width: 45;
        height: auto;
        border: round $primary;
        padding: 1;
        border-subtitle-color: $accent;
    }

    Input {
        width: 100%;
        margin: 1;
        border: round $accent;
        background: transparent;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="login-box") as container:
            container.border_title = "Login"
            container.border_subtitle = "V1.0"
            username = Input(placeholder="Username", id="username")
            password = Input(placeholder="Password", password=True, id="password")
            username.border_title = "Username"
            password.border_title = "Password"
            yield username
            yield password

    def on_input_submitted(self):
        username = self.query_one("#username", Input).value
        password = self.query_one("#password", Input).value

        if username == self.VALID_USERNAME and password == self.VALID_PASSWORD:
            self.app.push_screen(MainMenu())
        else:
            self.notify("Invalid username or password!", severity="error")


class Katonagari(App):
    def on_mount(self) -> None:
        self.push_screen(MainMenu())


if __name__ == "__main__":
    app = Katonagari()
    app.run()