"""
Plugin Architecture — Modular Extension System
================================================
Allows new modules to be added without changing the core.
Supports plugins for:
  - Sensors
  - Planners
  - Controllers
  - Perception models
  - Environments
  - Dashboards
  - Missions
  - Analytics
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum, auto

from .event_bus import get_event_bus


class PluginType(Enum):
    SENSOR = auto()
    PLANNER = auto()
    CONTROLLER = auto()
    PERCEPTION = auto()
    ENVIRONMENT = auto()
    DASHBOARD = auto()
    MISSION = auto()
    ANALYTICS = auto()
    AI_MODEL = auto()


@dataclass
class PluginInfo:
    """Metadata about a registered plugin."""
    name: str
    plugin_type: PluginType
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    enabled: bool = True
    instance: Any = None


class PluginManager:
    """
    Manages the lifecycle of all plugins in the system.
    
    Plugins register themselves and are discovered by type.
    """

    def __init__(self):
        self.bus = get_event_bus()
        self._plugins: Dict[str, PluginInfo] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    def register(self, name: str, plugin_type: PluginType,
                 instance: Any, version: str = "1.0.0",
                 author: str = "", description: str = ""):
        """Register a plugin."""
        info = PluginInfo(
            name=name, plugin_type=plugin_type,
            version=version, author=author,
            description=description, instance=instance,
        )
        self._plugins[name] = info
        self.bus.publish("plugin.registered", {
            "name": name, "type": plugin_type.name,
        })

    def unregister(self, name: str):
        """Unregister a plugin."""
        if name in self._plugins:
            del self._plugins[name]
            self.bus.publish("plugin.unregistered", {"name": name})

    def enable(self, name: str):
        if name in self._plugins:
            self._plugins[name].enabled = True

    def disable(self, name: str):
        if name in self._plugins:
            self._plugins[name].enabled = False

    def get_plugin(self, name: str) -> Optional[Any]:
        info = self._plugins.get(name)
        if info and info.enabled:
            return info.instance
        return None

    def get_by_type(self, plugin_type: PluginType) -> List[Any]:
        return [
            info.instance for info in self._plugins.values()
            if info.plugin_type == plugin_type and info.enabled
        ]

    def add_hook(self, hook_name: str, callback: Callable):
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)

    def run_hook(self, hook_name: str, *args, **kwargs):
        for callback in self._hooks.get(hook_name, []):
            try:
                callback(*args, **kwargs)
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        types = {}
        for info in self._plugins.values():
            t = info.plugin_type.name
            types[t] = types.get(t, 0) + 1
        return {
            "total": len(self._plugins),
            "enabled": sum(1 for p in self._plugins.values() if p.enabled),
            "by_type": types,
        }