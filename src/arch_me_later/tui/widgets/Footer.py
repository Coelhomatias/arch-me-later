from __future__ import annotations

from typing import Any

from textual.widgets import Footer as TextualFooter


class ArchFooter(TextualFooter):
    """Custom Footer widget for ArchMeLater TUI."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "show_command_palette" not in kwargs:
            kwargs["show_command_palette"] = False
        super().__init__(*args, **kwargs)
        self.add_class("footer")
