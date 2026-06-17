"""
Brain Integration
=================
Connects MissionControlWorkspace to the drone brain.

Wires all simulation data into workspace widgets in real-time:
  - Flight telemetry → TelemetryWidget
  - Battery status → BatteryWidget
  - World map → WorldMapWidget
  - Graphs → GraphWidget instances
  - Airspace → Airspace panel
  - Cognitive metrics → Drone Brain panel
  - Events → Command palette / status widgets

This is the data bridge between the simulation and the workspace UI.
"""

from __future__ import annotations

import time
import math
from typing import Optional, Any, Dict, List
from dataclasses import dataclass

from .widget_base import Widget, WorldMapWidget, TelemetryWidget, BatteryWidget
from .workspace import MissionControlWorkspace
from .graph_registry import GraphRegistry, GraphWidget, GraphSpec
from .theme_manager import ThemePreset


def _val(obj: Any, attr: str, default: Any = None) -> Any:
    """Get a value from an object or dict. Handles both attribute and key access."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _float(obj: Any, attr: str, default: float = 0.0) -> float:
    v = _val(obj, attr, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


class BrainIntegration:
    """
    Real-time data bridge between drone brain and MissionControlWorkspace.

    Usage:
        brain = BrainIntegration(workspace)
        brain.update(mission_snapshot_dict)
    """

    def __init__(self, workspace: MissionControlWorkspace):
        self.workspace = workspace
        self._graph_widgets: Dict[str, GraphWidget] = {}
        self._last_update: Dict[str, float] = {}
        self._update_interval: float = 0.05  # 20 FPS per widget
        self._history_length: int = 300

        # Register default widget bindings
        self._bindings: Dict[str, str] = {
            "telemetry": "telemetry",
            "battery": "battery",
            "world_map": "world_map",
        }

    def bind_widget(self, data_key: str, widget_id: str):
        self._bindings[data_key] = widget_id

    def update(self, data: Dict[str, Any]):
        """Push new data into all bound widgets and graph widgets."""
        now = time.time()
        for key, wid in self._bindings.items():
            if key not in data:
                continue
            if now - self._last_update.get(wid, 0) < self._update_interval:
                continue
            widget = self.workspace.get_widget(wid)
            if widget:
                widget.update(data[key])
                self._last_update[wid] = now

        # Push graph values from the snapshot's 'graphs' dict
        graphs_data = data.get("graphs", {})
        if graphs_data:
            for graph_id, value in graphs_data.items():
                self.update_graph(graph_id, value)

    def update_graph(self, graph_id: str, value: float):
        """Push a new sample into a graph widget, auto-placing it in the workspace."""
        gw = self._graph_widgets.get(graph_id)
        if gw is None:
            reg = self.workspace.graphs
            w = reg.create_widget(graph_id)
            if w:
                self._graph_widgets[graph_id] = w
                # Auto-place in the first free grid slot if not already in workspace
                existing = self.workspace.get_widget(w.id)
                if existing is None:
                    row, col = self._find_free_slot(w)
                    self.workspace.add_widget(w, row=row, col=col)
                gw = w
        if gw:
            gw.update({"value": value})

    def _find_free_slot(self, widget) -> tuple:
        """Find first free grid position for a new widget, with proper sizing."""
        ws = self.workspace
        grid = ws.grid
        # Calculate spans based on widget's default pixel size vs grid cell size
        cell_size = grid.cell_size
        default_w, default_h = widget.geometry.width, widget.geometry.height
        colspan = max(1, round(default_w / cell_size))
        rowspan = max(1, round(default_h / cell_size))
        # Clamp to grid limits
        colspan = min(colspan, grid.cols)
        rowspan = min(rowspan, grid.rows)

        for r in range(grid.rows - rowspan + 1):
            for c in range(grid.cols - colspan + 1):
                # Use a try-place approach by checking manually
                from .workspace_manager import GridCell
                new_cell = GridCell(r, c, rowspan, colspan, widget.id)
                collision = False
                for existing in grid._cells:
                    if existing.widget_id and existing.widget_id != widget.id:
                        if new_cell.overlaps(existing):
                            collision = True
                            break
                if not collision:
                    # Now place it for real
                    grid.place_widget(widget, r, c, rowspan, colspan)
                    return (r, c)
        # Fallback: place at (0,0)
        grid.place_widget(widget, 0, 0, rowspan, colspan)
        return (0, 0)

    def create_standard_widgets(self) -> List[Widget]:
        """Create the standard set of mission control widgets."""
        widgets = [
            WorldMapWidget(),
            TelemetryWidget(),
            BatteryWidget(),
        ]
        return widgets

    def setup_standard_layout(self):
        """Auto-arrange standard widgets in a sensible default layout."""
        std = self.create_standard_widgets()
        positions = [
            (0, 0, 8, 8),   # World map
            (0, 8, 4, 4),   # Telemetry
            (4, 8, 4, 4),   # Battery
        ]
        for w, (row, col, rs, cs) in zip(std, positions):
            self.workspace.add_widget(w, row=row, col=col)
        return std

    def get_widget_data(self, widget_id: str) -> Optional[Dict]:
        w = self.workspace.get_widget(widget_id)
        if w and hasattr(w, "serialize"):
            return w.serialize()
        return None

    def get_all_graph_data(self) -> Dict[str, List[float]]:
        return {gid: gw._data for gid, gw in self._graph_widgets.items()}


def build_mission_snapshot(mission: Any) -> Dict[str, Any]:
    """Extract current mission state into a snapshot dict for workspace widgets.
    
    Accepts either:
      - A dict-like object with keys 'drone', 'battery', 'world', etc.
      - An object with attributes drone, battery, current_path, etc.
    """
    m = mission
    drone = _val(m, "drone")
    battery = _val(m, "battery")
    airspace_manager = _val(m, "airspace_manager")
    
    # Drone state — fall back to keys if the drone itself is a dict
    drone_x = _float(drone, "x", 50.0)
    drone_y = _float(drone, "y", 50.0)
    drone_z = _float(drone, "z", 0.0)
    drone_speed = _float(drone, "speed", 0.0)
    drone_heading = _float(drone, "heading", 0.0)
    drone_vspd = _float(drone, "vertical_speed", 0.0)
    
    # Battery
    battery_pct = 100.0
    battery_drain = 0.0
    if battery is not None:
        pct_method = getattr(battery, "percentage", None)
        if callable(pct_method):
            battery_pct = float(pct_method())
        battery_drain = _float(battery, "drain_rate", 0.0)
    
    # Targets / path
    target_x = _float(m, "target_x", 90.0)
    target_y = _float(m, "target_y", 90.0)
    current_path = _val(m, "current_path", None)
    
    # Mission progress
    mission_progress = _float(m, "mission_progress", 0.0)
    
    # Risk / confidence
    current_risk = _float(m, "current_risk", 0.0)
    ai_confidence = _float(m, "ai_confidence", 0.0)
    
    # Obstacles
    visible_obstacles = _val(m, "visible_obstacles", [])
    obstacle_count = len(visible_obstacles) if isinstance(visible_obstacles, (list, tuple)) else 0.0
    
    # Airspace
    airspace_zone_count = 0
    airspace_violations = 0
    airspace_risk_score = 0.0
    if airspace_manager is not None:
        geofence = getattr(airspace_manager, "geofence", None)
        if geofence is not None:
            airspace_zone_count = getattr(geofence, "get_zone_count", lambda: 0)()
            airspace_violations = getattr(geofence, "get_violation_count", lambda: 0)()
        airspace_risk_score = _float(m, "airspace_risk_score", 0.0)
    
    dist_target = math.hypot(drone_x - target_x, drone_y - target_y)
    
    snapshot = {
        "telemetry": {
            "speed": float(drone_speed),
            "heading": float(drone_heading),
            "altitude": float(drone_z),
            "vspd": float(drone_vspd),
            "dist_target": float(dist_target),
        },
        "battery": {
            "pct": float(battery_pct),
            "drain": float(battery_drain),
        },
        "world_map": {
            "drone_pos": (float(drone_x), float(drone_y)),
            "path": current_path,
            "terrain": None,
        },
        "graphs": {
            "altitude": float(drone_z),
            "speed": float(drone_speed),
            "battery": float(battery_pct),
            "risk": float(current_risk),
            "confidence": float(ai_confidence),
            "mission_progress": float(mission_progress),
            "obstacle_count": float(obstacle_count),
        },
        "airspace": {
            "zones_active": int(airspace_zone_count),
            "violations": int(airspace_violations),
            "risk_score": float(airspace_risk_score),
        },
    }
    return snapshot