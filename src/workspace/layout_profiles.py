"""
Layout Profiles
===============
Save, load, export, import, switch dashboard layouts.

Supports:
  - Named layout profiles
  - Auto-save on change
  - Import/export JSON
  - Instant switching
  - Profile duplication
"""

from __future__ import annotations

import json
import time
import copy
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from .widget_base import Widget, WidgetConfig, WidgetState


@dataclass
class LayoutProfile:
    name: str
    description: str = ""
    widgets: List[dict] = field(default_factory=list)
    grid: dict = field(default_factory=dict)
    active_widget_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    is_default: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LayoutProfile":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class LayoutManager:
    """Manages layout profiles: save, load, switch, export, import."""

    def __init__(self):
        self._profiles: Dict[str, LayoutProfile] = {}
        self._active: str = "default"
        self._autosave_interval: float = 5.0
        self._last_save: float = time.time()
        self._max_profiles: int = 50

    def create(self, name: str, description: str = "",
               widgets: Optional[List[Widget]] = None,
               grid: Optional[dict] = None) -> LayoutProfile:
        if len(self._profiles) >= self._max_profiles:
            raise RuntimeError(f"Maximum profiles ({self._max_profiles}) reached")
        widget_dicts = [w.serialize() for w in (widgets or [])]
        profile = LayoutProfile(
            name=name,
            description=description,
            widgets=widget_dicts,
            grid=grid or {},
        )
        self._profiles[name] = profile
        return profile

    def save_current(self, name: Optional[str] = None,
                     widgets: Optional[List[Widget]] = None,
                     grid: Optional[dict] = None) -> LayoutProfile:
        target = name or self._active
        widget_dicts = [w.serialize() for w in (widgets or [])]
        if target in self._profiles:
            profile = self._profiles[target]
            profile.widgets = widget_dicts
            profile.grid = grid or profile.grid
            profile.modified_at = time.time()
        else:
            profile = self.create(target, widgets=widgets, grid=grid)
        return profile

    def load(self, name: str) -> Optional[LayoutProfile]:
        return self._profiles.get(name)

    def switch(self, name: str):
        if name in self._profiles:
            self._active = name
        else:
            raise KeyError(f"Profile '{name}' not found")

    def delete(self, name: str):
        if name in self._profiles and name != "default":
            del self._profiles[name]
            if self._active == name:
                self._active = "default"

    def rename(self, old_name: str, new_name: str):
        if old_name in self._profiles and old_name != "default":
            profile = self._profiles.pop(old_name)
            profile.name = new_name
            self._profiles[new_name] = profile
            if self._active == old_name:
                self._active = new_name

    def duplicate(self, name: str, new_name: str) -> LayoutProfile:
        if name not in self._profiles:
            raise KeyError(f"Profile '{name}' not found")
        src = self._profiles[name]
        dup = LayoutProfile(
            name=new_name,
            description=src.description + " (copy)",
            widgets=copy.deepcopy(src.widgets),
            grid=copy.deepcopy(src.grid),
        )
        self._profiles[new_name] = dup
        return dup

    def export(self, name: Optional[str] = None) -> str:
        target = name or self._active
        profile = self._profiles.get(target)
        if not profile:
            raise KeyError(f"Profile '{target}' not found")
        return json.dumps(profile.to_dict(), indent=2)

    def import_profile(self, json_str: str) -> LayoutProfile:
        data = json.loads(json_str)
        profile = LayoutProfile.from_dict(data)
        self._profiles[profile.name] = profile
        return profile

    def get_active(self) -> Optional[LayoutProfile]:
        return self._profiles.get(self._active)

    def list_profiles(self) -> List[str]:
        return list(self._profiles.keys())

    def autosave(self, widgets: Optional[List[Widget]] = None, grid: Optional[dict] = None):
        now = time.time()
        if (now - self._last_save) >= self._autosave_interval:
            try:
                self.save_current(widgets=widgets, grid=grid)
                self._last_save = now
            except Exception:
                pass