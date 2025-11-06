from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from textual.containers import Container
from textual.widgets import RichLog

from arch_me_later.logs.logger import Logger as logger

if TYPE_CHECKING:
    from textual.app import ComposeResult


class Logs(Container):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.add_class("logs-container")
        self.log_widget = RichLog(
            id="logs-widget",
            highlight=True,
            markup=True,
            wrap=True,
        )
        self.log_widget.add_class("logs-widget")
        # Configure global logger once (idempotent)
        logger.configure(log_widget=self.log_widget, log_dir=Path.cwd() / "logs")

    def compose(self) -> ComposeResult:
        yield self.log_widget

    def on_mount(self) -> None:
        logger.debug("Logs will appear here...")
        logger.log("Logs will appear here...")
        logger.info("Logs will appear here...")
        logger.status("Logs will appear here...")
        logger.warning("This is a warning message.")
        logger.error("This is an error message.")
