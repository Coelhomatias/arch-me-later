from __future__ import annotations

from typing import Any

from textual.widgets import Header as TextualHeader


class ArchHeader(TextualHeader):
    """Custom Header widget for ArchMeLater TUI."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "show_clock" not in kwargs:
            kwargs["show_clock"] = True
        super().__init__(*args, **kwargs)
        self.add_class("header")
