"""
Command Palette
===============
VS Code / Blender style Ctrl+Shift+P command palette.

Supports:
  - Search widgets by name, category, tag, type
  - Execute commands (toggle layout, theme, etc.)
  - Recent commands history
  - Keyboard navigation
"""

from __future__ import annotations

import time
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field


@dataclass
class Command:
    command_id: str
    label: str
    category: str
    shortcut: str
    action: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    icon: str = ""
    tags: List[str] = field(default_factory=list)

    def matches(self, query: str) -> bool:
        q = query.lower()
        return (q in self.label.lower() or
                q in self.category.lower() or
                q in self.command_id.lower() or
                any(q in t.lower() for t in self.tags))


class CommandPalette:
    """Searchable command palette overlay."""

    def __init__(self):
        self._commands: Dict[str, Command] = {}
        self._recent: List[str] = []
        self._max_recent: int = 20
        self._is_open: bool = False
        self._query: str = ""
        self._selected_index: int = 0
        self._on_execute: List[Callable] = []

    def register(self, cmd: Command):
        self._commands[cmd.command_id] = cmd

    def unregister(self, command_id: str):
        self._commands.pop(command_id, None)

    def search(self, query: str) -> List[Command]:
        if not query:
            return list(self._commands.values())
        return [c for c in self._commands.values() if c.matches(query)]

    def execute(self, command_id: str):
        cmd = self._commands.get(command_id)
        if cmd:
            self._recent.append(command_id)
            if len(self._recent) > self._max_recent:
                self._recent.pop(0)
            for cb in self._on_execute:
                try:
                    cb(cmd)
                except Exception:
                    pass
            try:
                cmd.action(*cmd.args, **cmd.kwargs)
            except Exception:
                pass

    def get_recent(self) -> List[Command]:
        return [self._commands[cid] for cid in self._recent if cid in self._commands]

    def open(self, query: str = ""):
        self._is_open = True
        self._query = query
        self._selected_index = 0

    def close(self):
        self._is_open = False
        self._query = ""
        self._selected_index = 0

    def navigate(self, direction: int):
        results = self.search(self._query)
        if not results:
            return
        self._selected_index = (self._selected_index + direction) % len(results)

    def select_current(self):
        results = self.search(self._query)
        if results and 0 <= self._selected_index < len(results):
            self.execute(results[self._selected_index].command_id)

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def query(self) -> str:
        return self._query

    def get_filtered(self) -> List[Command]:
        return self.search(self._query)

    def on_execute(self, callback: Callable):
        self._on_execute.append(callback)