from __future__ import annotations
from datetime import date
from textual.widgets import Button

class DayTab(Button):
    DEFAULT_CSS = """
    DayTab {
        width: 1fr;
        height: 3;
        background: transparent;
        border: none;
        color: $text-muted;
        text-style: none;
        padding: 0;
        min-width: 5;
    }
    DayTab:hover { background: $surface 30%; color: $text; }

    DayTab.selected {
        background: $background;
        border-top: tall $surface-lighten-2;
        border-left: tall $surface-lighten-2;
        border-right: tall $surface-lighten-2;
        color: $primary;
        text-style: bold;
    }

    DayTab.today { color: $warning; }
    DayTab.selected.today {
        color: $warning;
        border-top: tall $warning 40%;
        border-left: tall $warning 20%;
        border-right: tall $warning 20%;
    }
    """

    def __init__(self, d: date, selected: bool = False) -> None:
        label = f"{d.strftime('%a')} {d.day}"
        super().__init__(label, id=f"day-{d.isoformat()}")
        self._date = d
        if selected:
            self.add_class("selected")
        if d == date.today():
            self.add_class("today")

    @property
    def day_date(self) -> date:
        return self._date


class AllTab(Button):
    """Fixed-width 'All' tab that shows every event across all dates."""

    DEFAULT_CSS = """
    AllTab {
        width: 7;
        height: 3;
        background: transparent;
        border: none;
        color: $text-muted;
        text-style: none;
        padding: 0;
        min-width: 5;
    }
    AllTab:hover { background: $surface 30%; color: $text; }

    AllTab.selected {
        background: $background;
        border-top: tall $accent 60%;
        border-left: tall $accent 30%;
        border-right: tall $accent 30%;
        color: $accent;
        text-style: bold;
    }
    """

    def __init__(self, selected: bool = False) -> None:
        super().__init__("All ✦", id="tab-all")
        if selected:
            self.add_class("selected")
