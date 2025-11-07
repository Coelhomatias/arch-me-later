from __future__ import annotations

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

    def compose(self) -> ComposeResult:
        yield self.log_widget

    def on_mount(self) -> None:
        # Register the RichLog with the global logger once the widget is ready
        logger.register_rich_log(self.log_widget)
        logger.debug("Logs will appear here...")
        logger.log("Logs [red]will[/] appear here...")
        logger.info("Logs [green]will[/] appear here...")
        logger.status("Logs [blue]will[/] appear here...")
        logger.warning("This is a [yellow]warning message.[/]")
        logger.error("This is a [red]error message.[/]")
