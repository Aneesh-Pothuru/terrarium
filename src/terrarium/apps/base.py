from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from terrarium.world import World


class AppModule:
    name = "app"

    def __init__(self, world: "World") -> None:
        self.world = world

    def log_read(self, operation: str, payload: dict[str, Any]) -> None:
        self.world.log("read", self.name, operation, payload)

    def log_write(self, operation: str, payload: dict[str, Any]) -> None:
        self.world.log("write", self.name, operation, payload)
