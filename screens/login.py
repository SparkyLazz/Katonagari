from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input


class Login(ModalScreen):
    CSS = """
    Login {
        align: center middle;
    }

    #dialog {
        layout: vertical;
        padding: 1 1;
        width: 20%;
        height: auto;
        border: round $primary;
        border-title-align: center;
        background: transparent;
    }

    .input {
        background: transparent;
        border: round $accent;
        border-title-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog") as login:
            username = Input(placeholder="Username", classes="input", id="username")
            password = Input(placeholder="Password", password=True, classes="input", id="password")

            username.border_title = "Username"
            password.border_title = "Password"
            login.border_title = "Login"

            yield username
            yield password

    def on_input_submitted(self, event: Input.Submitted) -> None:
        username = self.query_one("#username", Input).value
        password = self.query_one("#password", Input).value

        if username == "SparkyLazz" and password == "Mycodeis9!":
            self.dismiss({"username": username, "password": password})
        else:
            self.app.notify("Please fill the username and password correctly", severity="warning")
    def on_mount(self) -> None:
        self.query_one(Input).focus()
