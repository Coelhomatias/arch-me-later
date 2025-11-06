from __future__ import annotations

from textual.widgets import ProgressBar
from textual.containers import Container
from textual.app import ComposeResult
from typing import Any


class ArchProgressBar(Container):
    """Custom ProgressBar widget for ArchMeLater TUI."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.add_class("progress-bar-container")
        self.progress_bar = ProgressBar(
            total=100, classes="progress-bar", show_eta=False
        )

    def on_mount(self) -> None:
        self.progress_bar.update(progress=70)

    def compose(self) -> ComposeResult:
        yield self.progress_bar
