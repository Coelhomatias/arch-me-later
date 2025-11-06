from __future__ import annotations

from textual.containers import Container
from typing import Any


class Plan(Container):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.add_class("plan-container")
