# Utils.py
from textual.app import ComposeResult
from textual.containers import Container

class Panel(Container):  # This should be a CLASS
    DEFAULT_CSS = """
    Panel {
        height: auto;
        border: round $primary;
        border-title-align: left;
        border-title-style: bold;
        border-subtitle-align: right;
        border-subtitle-style: dim;
        padding: 0;
        margin: 1;
    }
    """

    def __init__(self, title: str = "", subtitle: str = "", *children, **kwargs):
        super().__init__(**kwargs)
        if title:
            self.border_title = title
        if subtitle:
            self.border_subtitle = subtitle
        self._children = children

    def compose(self) -> ComposeResult:
        for child in self._children:
            yield child