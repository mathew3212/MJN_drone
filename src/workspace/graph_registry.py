"""
Graph Registry
==============
Available interactive graph widgets for the Mission Control Workspace.

Each graph widget supports:
  - Zoom, pan, auto-scale, reset view
  - Mouse wheel zoom, box zoom
  - Double-click reset
  - Crosshair, hover tooltip
  - Data cursor, annotations
  - Export image/CSV, fullscreen
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .widget_base import Widget, WidgetConfig


@dataclass
class GraphSpec:
    graph_id: str
    title: str
    category: str
    icon: str
    tags: List[str]
    y_label: str
    unit: str = ""
    color: str = "#00D4FF"
    default_size: tuple = (300, 200)

    def to_config(self) -> WidgetConfig:
        return WidgetConfig(
            widget_type=f"graph_{self.graph_id}",
            title=self.title,
            icon=self.icon,
            category=f"Graphs / {self.category}",
            default_size=self.default_size,
            tags=self.tags + ["graph", "chart", "live"],
        )


# Pre-defined graph catalog
GRAPH_CATALOG: List[GraphSpec] = [
    GraphSpec("altitude", "Altitude", "Flight", "📏", ["altitude", "height", "z"], "Altitude", "m", "#00D4FF"),
    GraphSpec("speed", "Speed", "Flight", "🚀", ["speed", "velocity", "spd"], "Speed", "m/s", "#FF8800"),
    GraphSpec("battery", "Battery %", "Systems", "🔋", ["battery", "power"], "Battery", "%", "#00FF88"),
    GraphSpec("voltage", "Voltage", "Systems", "⚡", ["voltage", "v", "battery"], "Voltage", "V", "#9D6CFF"),
    GraphSpec("current", "Current", "Systems", "🔌", ["current", "amps", "a"], "Current", "A", "#06B6D4"),
    GraphSpec("cpu", "CPU Usage", "Performance", "🖥", ["cpu", "processor"], "CPU", "%", "#FFC857"),
    GraphSpec("ram", "RAM Usage", "Performance", "💾", ["ram", "memory"], "RAM", "%", "#9D6CFF"),
    GraphSpec("temperature", "Temperature", "Performance", "🌡", ["temp", "thermal", "heat"], "Temp", "°C", "#FF4D5A"),
    GraphSpec("risk", "Risk Score", "Safety", "⚠", ["risk", "danger"], "Risk", "", "#FF4D5A"),
    GraphSpec("confidence", "Confidence", "AI", "🎯", ["confidence", "ai"], "Confidence", "%", "#00FF88"),
    GraphSpec("latency", "Latency", "Network", "📶", ["latency", "ping", "ms"], "Latency", "ms", "#FFC857"),
    GraphSpec("mission_progress", "Mission Progress", "Mission", "📍", ["mission", "progress"], "Progress", "%", "#00D4FF"),
    GraphSpec("obstacle_count", "Obstacles", "Sensors", "🚧", ["obstacle", "lidar"], "Obstacles", "count", "#FF8800"),
    GraphSpec("gps", "GPS Signal", "Navigation", "🛰", ["gps", "satellite"], "GPS", "dBm", "#00FF88"),
    GraphSpec("wind", "Wind Speed", "Weather", "💨", ["wind", "weather"], "Wind", "m/s", "#06B6D4"),
    GraphSpec("heading", "Heading", "Flight", "🧭", ["heading", "yaw", "hdg"], "Heading", "°", "#00D4FF"),
    GraphSpec("pitch", "Pitch", "Flight", "📐", ["pitch"], "Pitch", "°", "#9D6CFF"),
    GraphSpec("roll", "Roll", "Flight", "🔄", ["roll"], "Roll", "°", "#FFC857"),
    GraphSpec("acceleration", "Acceleration", "Physics", "🏎", ["accel", "g-force"], "Accel", "m/s²", "#FF8800"),
    GraphSpec("prediction_confidence", "Pred. Confidence", "AI", "🔮", ["prediction", "ai"], "Pred. Conf.", "%", "#9D6CFF"),
    GraphSpec("decision_latency", "Decision Latency", "AI", "⏱", ["decision", "latency"], "Dec. Lat.", "ms", "#FFC857"),
    GraphSpec("planning_time", "Planning Time", "AI", "📋", ["planning", "time"], "Plan. Time", "ms", "#06B6D4"),
    GraphSpec("sensor_fps", "Sensor FPS", "Sensors", "📷", ["sensor", "fps"], "Sensor FPS", "fps", "#00FF88"),
    GraphSpec("attention_score", "Attention Score", "Cognitive", "👁", ["attention", "focus"], "Attention", "%", "#00D4FF"),
    GraphSpec("collision_probability", "Collision Prob.", "Safety", "💥", ["collision", "safety"], "Coll. Prob.", "%", "#FF4D5A"),
]


class GraphRegistry:
    """Registry of available graph/telemetry widgets."""

    def __init__(self):
        self._catalog: Dict[str, GraphSpec] = {g.graph_id: g for g in GRAPH_CATALOG}
        self._active: Dict[str, Widget] = {}

    def get_spec(self, graph_id: str) -> Optional[GraphSpec]:
        return self._catalog.get(graph_id)

    def list_graphs(self, category: Optional[str] = None) -> List[GraphSpec]:
        if category:
            return [g for g in self._catalog.values() if category in g.category]
        return list(self._catalog.values())

    def create_widget(self, graph_id: str) -> Optional[Widget]:
        spec = self._catalog.get(graph_id)
        if not spec:
            return None
        w = GraphWidget(spec)
        self._active[graph_id] = w
        return w

    def get_widget(self, graph_id: str) -> Optional[Widget]:
        return self._active.get(graph_id)

    def search(self, query: str) -> List[GraphSpec]:
        q = query.lower()
        return [g for g in self._catalog.values()
                if q in g.title.lower() or q in g.category.lower() or any(q in t.lower() for t in g.tags)]


class GraphWidget(Widget):
    """Interactive live-updating graph widget."""

    def __init__(self, spec: GraphSpec, config=None, parent=None):
        cfg = config or spec.to_config()
        # Ensure graphs are always resizable and dockable
        cfg.resizable = True
        cfg.dockable = True
        cfg.floatable = True
        cfg.default_size = spec.default_size
        super().__init__(cfg, parent)
        self.graph_id = spec.graph_id
        self.y_label = spec.y_label
        self.unit = spec.unit
        self.line_color = spec.color
        self._data: List[float] = []
        self._max_points: int = 300
        self._line = None
        self._last_value: float = 0.0

    def render(self, data=None):
        if self._content_axes is None:
            return
        self._clear_content()
        ax = self._content_axes
        ax.set_facecolor("#0B0E14")
        if data and "value" in data:
            self._last_value = data["value"]
            self._data.append(self._last_value)
            if len(self._data) > self._max_points:
                self._data = self._data[-self._max_points:]
        if self._data:
            ax.plot(self._data, color=self.line_color, linewidth=1.5)
            ax.set_ylim(min(self._data) * 0.95, max(self._data) * 1.05)
        ax.set_title(self.title, color=self.line_color, fontsize=9, fontweight="bold")
        ax.set_ylabel(f"{self.y_label} ({self.unit})" if self.unit else self.y_label,
                      color="#6B7FA0", fontsize=7)
        ax.tick_params(colors="#4A5A78", labelsize=6)
        ax.grid(True, color="#1A2035", linewidth=0.3, alpha=0.4)

    def update(self, data=None):
        self.render(data)