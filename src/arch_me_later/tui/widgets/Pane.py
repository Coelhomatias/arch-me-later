from __future__ import annotations

from textual.containers import Vertical
from typing import Any


class Pane(Vertical):
    def __init__(
        self,
        border_title: str = "",
        border_subtitle: str = "",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.add_class("pane")
        self.border_title = border_title
        self.border_subtitle = border_subtitle
