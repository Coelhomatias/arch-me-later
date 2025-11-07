from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal

from arch_me_later.logs import logger
from arch_me_later.tui.widgets import Footer, Header, Logs, Pane, Plan, ProgressBar

STYLES_DIR: Path = Path(__file__).parent / "styles"
STYLES: list[str] = [str(file) for file in STYLES_DIR.glob("*.tcss")]
LOG_DIR: Path = Path.cwd() / "logs"


class ArchMeLaterTUI(App):
    """Textual TUI for Arch Me Later."""

    CSS_PATH = STYLES
    BINDINGS: list[tuple[str, str, str]] = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Horizontal():
            with Pane(border_title="Plan & Progress"):
                yield Plan()
                yield ProgressBar()
            with Pane(border_title="Logs"):
                yield Logs()
        yield Footer()

    def on_mount(self) -> None:
        """Actions to perform when the app is mounted."""
        self.theme = "tokyo-night"


def run() -> None:
    """Run the Arch Me Later TUI application."""
    # Configure logger as early as possible (file handler only for now).
    logger.configure(log_dir=LOG_DIR)
    app = ArchMeLaterTUI()
    app.run()
