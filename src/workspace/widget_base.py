"""
Widget Base System
==================
Every panel in the Mission Control Workspace is a Widget.
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable
from enum import Enum, auto


class WidgetState(Enum):
    DOCKED = "docked"
    FLOATING = "floating"
    COLLAPSED = "collapsed"
    FULLSCREEN = "fullscreen"
    TABBED = "tabbed"


class ResizeHandle(Enum):
    NONE = "none"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class ThemePreset(Enum):
    DARK = "dark"
    LIGHT = "light"
    MIDNIGHT = "midnight"
    BLUEPRINT = "blueprint"
    GRAPHITE = "graphite"
    ARCTIC = "arctic"
    OPERATOR = "operator"


@dataclass
class WidgetGeometry:
    grid_row: int = 0
    grid_col: int = 0
    grid_rowspan: int = 1
    grid_colspan: int = 1
    x: float = 0.0
    y: float = 0.0
    width: float = 200.0
    height: float = 150.0
    min_width: float = 100.0
    min_height: float = 80.0
    max_width: float = 2000.0
    max_height: float = 2000.0
    floating_x: Optional[float] = None
    floating_y: Optional[float] = None
    floating_width: Optional[float] = None
    floating_height: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WidgetGeometry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class WidgetConfig:
    widget_type: str = "generic"
    title: str = "Widget"
    icon: str = "\u25fb"
    category: str = "General"
    resizable: bool = True
    dockable: bool = True
    floatable: bool = True
    closable: bool = True
    minimizable: bool = True
    has_titlebar: bool = True
    has_statusbar: bool = True
    min_size: tuple = (100, 80)
    max_size: tuple = (2000, 2000)
    default_size: tuple = (250, 180)
    shortcut: str = ""
    tags: List[str] = field(default_factory=list)


class Widget:
    """Base class for all Mission Control Workspace widgets."""

    def __init__(self, config: Optional[WidgetConfig] = None, parent=None):
        self.id: str = str(uuid.uuid4())[:8]
        self.config: WidgetConfig = config or WidgetConfig(widget_type=self.__class__.__name__)
        self.parent: Optional[Widget] = parent
        self.state: WidgetState = WidgetState.DOCKED
        self.geometry: WidgetGeometry = WidgetGeometry(
            width=self.config.default_size[0],
            height=self.config.default_size[1],
        )
        self.title: str = self.config.title
        self.is_visible: bool = True
        self.is_active: bool = False
        self.is_pinned: bool = False
        self.opacity: float = 1.0
        self.z_order: int = 0
        self.tags: List[str] = list(self.config.tags)
        self.created_at: float = time.time()
        self._title_text: Optional[str] = None
        self._status_text: str = ""
        self._content_axes: Optional[Any] = None
        self._floating_fig: Optional[Any] = None
        self._artists: List[Any] = []

        self._on_drag_start: List[Callable] = []
        self._on_drag_end: List[Callable] = []
        self._on_resize: List[Callable] = []
        self._on_close: List[Callable] = []
        self._on_activate: List[Callable] = []
        self._on_state_change: List[Callable] = []

    def set_content(self, axes):
        self._content_axes = axes

    def render(self, data: Any = None):
        if self._content_axes is not None:
            self._clear_content()
            ax = self._content_axes
            ax.set_facecolor("#0D1019")
            ax.text(0.5, 0.5, f"[{self.title}]\nNo data",
                    transform=ax.transAxes, ha="center", va="center",
                    color="#6B7FA0", fontsize=8)

    def update(self, data: Any = None):
        self.render(data)

    def _clear_content(self):
        if self._content_axes is not None:
            try:
                self._content_axes.clear()
            except Exception:
                pass

    def set_title(self, title: str):
        self.title = title
        self.config.title = title
        if self._title_text is not None:
            try:
                self._title_text.set_text(title)
            except Exception:
                pass

    def set_status(self, text: str):
        self._status_text = text

    def set_geometry(self, geo: WidgetGeometry):
        self.geometry = geo

    def get_geometry(self) -> WidgetGeometry:
        return self.geometry

    def get_bounds(self) -> tuple:
        g = self.geometry
        return (g.x, g.y, g.x + g.width, g.y + g.height)

    def contains_point(self, px: float, py: float) -> bool:
        x, y, x2, y2 = self.get_bounds()
        return x <= px <= x2 and y <= py <= y2

    def get_resize_handle(self, px: float, py: float, threshold: float = 10.0) -> ResizeHandle:
        if not self.config.resizable or self.state == WidgetState.COLLAPSED:
            return ResizeHandle.NONE
        x, y, x2, y2 = self.get_bounds()
        left = abs(px - x) < threshold
        right = abs(px - x2) < threshold
        top = abs(py - y) < threshold
        bottom = abs(py - y2) < threshold
        if top and left:
            return ResizeHandle.TOP_LEFT
        if top and right:
            return ResizeHandle.TOP_RIGHT
        if bottom and left:
            return ResizeHandle.BOTTOM_LEFT
        if bottom and right:
            return ResizeHandle.BOTTOM_RIGHT
        if left:
            return ResizeHandle.LEFT
        if right:
            return ResizeHandle.RIGHT
        if top:
            return ResizeHandle.TOP
        if bottom:
            return ResizeHandle.BOTTOM
        return ResizeHandle.NONE

    def set_state(self, state: WidgetState):
        old = self.state
        self.state = state
        if old != state:
            for cb in self._on_state_change:
                try:
                    cb(self, old, state)
                except Exception:
                    pass

    def toggle_fullscreen(self):
        self.set_state(WidgetState.FULLSCREEN if self.state != WidgetState.FULLSCREEN else WidgetState.DOCKED)

    def toggle_collapse(self):
        self.set_state(WidgetState.COLLAPSED if self.state != WidgetState.COLLAPSED else WidgetState.DOCKED)

    def toggle_float(self):
        if self.state == WidgetState.FLOATING:
            self.set_state(WidgetState.DOCKED)
        else:
            self.set_state(WidgetState.FLOATING)

    def on(self, event: str, callback: Callable):
        handlers = {
            "drag_start": self._on_drag_start,
            "drag_end": self._on_drag_end,
            "resize": self._on_resize,
            "close": self._on_close,
            "activate": self._on_activate,
            "state_change": self._on_state_change,
        }
        if event in handlers:
            handlers[event].append(callback)

    def serialize(self) -> dict:
        g = self.geometry
        return {
            "id": self.id,
            "widget_type": self.config.widget_type,
            "title": self.title,
            "state": self.state.value,
            "geometry": g.to_dict(),
            "opacity": self.opacity,
            "is_pinned": self.is_pinned,
            "tags": self.tags,
            "category": self.config.category,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "Widget":
        w = cls()
        w.id = data.get("id", w.id)
        w.title = data.get("title", w.title)
        w.config.title = w.title
        w.state = WidgetState(data.get("state", WidgetState.DOCKED.value))
        w.geometry = WidgetGeometry.from_dict(data.get("geometry", {}))
        w.opacity = data.get("opacity", 1.0)
        w.is_pinned = data.get("is_pinned", False)
        w.tags = data.get("tags", [])
        return w


class WorldMapWidget(Widget):
    def __init__(self, config=None, parent=None):
        cfg = config or WidgetConfig(
            widget_type="world_map", title="World Map",
            icon="\U0001f30d", category="Navigation", default_size=(500, 400),
            tags=["map", "viewport", "drone", "terrain"],
        )
        super().__init__(cfg, parent)

    def render(self, data=None):
        if self._content_axes is None:
            return
        self._clear_content()
        ax = self._content_axes
        ax.set_facecolor("#05070B")
        ax.set_title("WORLD MAP", color="#00D4FF", fontsize=10, fontweight="bold")
        if data:
            try:
                terrain = data.get("terrain")
                if terrain is not None:
                    ax.imshow(terrain, origin="lower", aspect="equal", alpha=0.6, zorder=0)
                drone_pos = data.get("drone_pos")
                if drone_pos is not None:
                    ax.plot(drone_pos[0], drone_pos[1], "o", color="#FF8800", markersize=8, zorder=10)
                path = data.get("path")
                if path is not None and len(path) > 1:
                    px = [p[0] for p in path]
                    py = [p[1] for p in path]
                    ax.plot(px, py, "-", color="#00D4FF", linewidth=2, alpha=0.8, zorder=5)
            except Exception:
                pass


class TelemetryWidget(Widget):
    def __init__(self, config=None, parent=None):
        cfg = config or WidgetConfig(
            widget_type="telemetry", title="Telemetry",
            icon="\U0001f4e1", category="Flight", default_size=(280, 200),
            tags=["flight", "speed", "altitude", "heading", "gps"],
        )
        super().__init__(cfg, parent)
        self._speed = 0.0
        self._heading = 0.0
        self._altitude = 50.0
        self._vspd = 0.0
        self._dist_target = 0.0

    def render(self, data=None):
        if self._content_axes is None:
            return
        ax = self._content_axes
        ax.set_facecolor("#0B0E14")
        if data:
            self._speed = data.get("speed", self._speed)
            self._heading = data.get("heading", self._heading)
            self._altitude = data.get("altitude", self._altitude)
            self._vspd = data.get("vspd", self._vspd)
            self._dist_target = data.get("dist_target", self._dist_target)
        lines = [
            f"SPD  {self._speed:6.1f} m/s",
            f"HDG  {self._heading:6.0f}\u00b0",
            f"ALT  {self._altitude:6.0f} m",
            f"VSPD {self._vspd:6.1f} m/s",
            f"DST  {self._dist_target:6.1f} m",
        ]
        ax.text(0.05, 0.95, "\n".join(lines), transform=ax.transAxes,
                fontsize=9, fontfamily="monospace", color="#E8EDFF",
                va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#11151F",
                          edgecolor="#1A2035", linewidth=0.5))


class BatteryWidget(Widget):
    def __init__(self, config=None, parent=None):
        cfg = config or WidgetConfig(
            widget_type="battery", title="Battery",
            icon="\U0001f50b", category="Systems", default_size=(220, 120),
            tags=["battery", "power", "energy", "consumption"],
        )
        super().__init__(cfg, parent)
        self._pct = 100.0
        self._drain = 0.0

    def render(self, data=None):
        if data:
            self._pct = data.get("pct", self._pct)
            self._drain = data.get("drain", self._drain)
        w = 0.75 * (self._pct / 100.0)
        col = "#00FF88" if self._pct > 50 else ("#FFC857" if self._pct > 20 else "#FF4D5A")