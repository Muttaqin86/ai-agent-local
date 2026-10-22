"""Tool registry and base tool interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    name: str
    description: str
    func: Any

    def __call__(self, args: dict[str, Any] | None = None) -> Any:
        return self.func(**(args or {}))


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())
