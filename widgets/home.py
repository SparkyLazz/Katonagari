import psutil
import platform
from datetime import datetime
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Static
from textual.containers import Vertical


class StatisticBox(Vertical):
    DEFAULT_CSS = """
    StatisticBox {
        height: auto;
        border: round $primary;
        row-span: 2;
        padding: 0 2;
    }
    StatisticBox Label {
        width: 100%;
        margin-top: 0;
        color: $text-muted;
    }
    StatisticBox Label.section {
        color: $primary;
        text-style: bold;
        margin-top: 1;
    }
    StatisticBox Label.info {
        color: $text;
    }
    StatisticBox ProgressBar {
        width: 100%;
        margin-bottom: 0;
    }

    #cpu-label { color: $success; }
    #ram-label { color: $warning; }
    #swp-label { color: $error; }
    #dsk-label { color: $accent; }

    #cpu-bar > .bar--bar { color: $success; }
    #ram-bar > .bar--bar { color: $warning; }
    #swp-bar > .bar--bar { color: $error; }
    #dsk-bar > .bar--bar { color: $accent; }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "Statistic"

        # system info
        yield Label("─ System ─", classes="section")
        yield Label("", id="hostname-label", classes="info")
        yield Label("", id="os-label", classes="info")
        yield Label("", id="uptime-label", classes="info")

        # resources
        yield Label("─ Resources ─", classes="section")
        yield Label("CPU  0%", id="cpu-label")
        yield ProgressBar(total=100, id="cpu-bar", show_eta=False)
        yield Label("RAM  0%", id="ram-label")
        yield ProgressBar(total=100, id="ram-bar", show_eta=False)
        yield Label("SWP  0%", id="swp-label")
        yield ProgressBar(total=100, id="swp-bar", show_eta=False)

        # disk
        yield Label("─ Disk ─", classes="section")
        yield Label("DSK  0%", id="dsk-label")
        yield ProgressBar(total=100, id="dsk-bar", show_eta=False)
        yield Label("", id="dsk-info", classes="info")

    def on_mount(self) -> None:
        # static system info
        uname = platform.uname()
        self.query_one("#hostname-label", Label).update(f"Host  {uname.node}")
        self.query_one("#os-label", Label).update(f"OS    {uname.system} {uname.release}")

        self.update_stats()
        self.set_interval(2, self.update_stats)

    def update_stats(self) -> None:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        swp = psutil.swap_memory().percent
        disk = psutil.disk_usage("/")

        # uptime
        boot = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot
        hours, rem = divmod(int(uptime.total_seconds()), 3600)
        mins = rem // 60
        self.query_one("#uptime-label", Label).update(f"Up    {hours}h {mins}m")

        # resources
        self.query_one("#cpu-bar", ProgressBar).progress = cpu
        self.query_one("#ram-bar", ProgressBar).progress = ram
        self.query_one("#swp-bar", ProgressBar).progress = swp
        self.query_one("#cpu-label", Label).update(f"CPU  {cpu}%")
        self.query_one("#ram-label", Label).update(f"RAM  {ram}%")
        self.query_one("#swp-label", Label).update(f"SWP  {swp}%")

        # disk
        dsk_pct = disk.percent
        used_gb = disk.used / 1024 ** 3
        total_gb = disk.total / 1024 ** 3
        self.query_one("#dsk-bar", ProgressBar).progress = dsk_pct
        self.query_one("#dsk-label", Label).update(f"DSK  {dsk_pct}%")
        self.query_one("#dsk-info", Label).update(f"      {used_gb:.1f} / {total_gb:.1f} GB")


class Home(Widget):
    DEFAULT_CSS = """
    Home {
        layout: grid;
        grid-size: 3 3;
        grid-columns: 1fr 2fr 2fr;
    }
    .box {
        height: 100%;
        border: round $primary;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield StatisticBox()
        yield Static("2", classes="box")
        yield Static("3", classes="box")
        yield Static("4", classes="box")
        yield Static("5", classes="box")
        yield Static("6", classes="box")