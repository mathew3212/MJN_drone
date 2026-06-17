"""
MJN Autonomous Drone Navigation Dashboard
=========================================
Professional aerospace / robotics command-center interface.
Complete architecture, layout, rendering, synchronization,
and performance redesign.

Design Philosophy:
- NASA Mission Control / DJI Ground Station aesthetic
- 95%+ space utilization
- 60 FPS target with blitting and artist reuse
- Zero crashes via defensive patterns
- Single source of truth (simulation_state)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.colorbar import Colorbar
from matplotlib.gridspec import GridSpec
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Circle
from matplotlib.text import Text
import matplotlib.patches as mpatches

# ── Constants ──────────────────────────────────────────────────────────────
MAX_TRAIL_POINTS: int = 300
FPS_SMOOTHING: float = 0.1
MAX_METRICS_HISTORY: int = 500
MAX_SIDEBAR_FIELDS: int = 20

# ── Professional Aerospace Dark Theme Palette ──────────────────────────────
BACKGROUND: str = "#08111D"
PANEL_COLOR: str = "#111827"
PANEL_INNER: str = "#0F172A"
BORDER_COLOR: str = "#334155"
TEXT_COLOR: str = "#E2E8F0"
ACCENT_COLOR: str = "#38BDF8"
SUCCESS_COLOR: str = "#22C55E"
WARNING_COLOR: str = "#F59E0B"
DANGER_COLOR: str = "#EF4444"
PATH_COLOR: str = "#37C8FF"
DRONE_COLOR: str = "#FF9800"
TARGET_COLOR: str = "#00FF66"
DYNAMIC_COLOR: str = "#FF3B30"
GRID_COLOR: str = "#334155"
SUB_TEXT_COLOR: str = "#94A3B8"
SENSOR_COLOR: str = "#14B8A6"
HEADER_BG: str = "#0A1628"

# ── Module-level singleton ─────────────────────────────────────────────────
_dashboard: Optional["DroneDashboard"] = None


# ══════════════════════════════════════════════════════════════════════════
# Simulation State (Single Source of Truth)
# ══════════════════════════════════════════════════════════════════════════


@dataclass
class SimulationState:
    """Immutable snapshot of every value the dashboard needs.

    All panels consume data from this object — guaranteeing that
    every widget updates from the same frame timestamp (no stale data).
    """
    world: Any
    drone: Any
    target: tuple[float, float]
    path: Optional[Any] = None
    smooth_path: Optional[Any] = None
    occupancy_grid: Optional[Any] = None
    perception_map: Optional[Any] = None
    risk_map: Optional[Any] = None
    memory_map: Optional[Any] = None
    context_map: Optional[Any] = None
    cognitive_map: Optional[Any] = None
    behavior_state: Optional[str] = None
    mission_state: Optional[str] = None
    planner_name: Optional[str] = None
    emergency_state: Optional[str] = None
    battery_percentage: Optional[float] = None
    memory_density: Optional[float] = None
    active_cells: Optional[int] = None
    sensor_radius: float = 8.0
    explored_percent: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════


def _as_offsets(points) -> np.ndarray:
    """Convert any iterable of 2D points to a numpy array safely."""
    points = list(points)
    if not points:
        return np.empty((0, 2))
    return np.asarray(points, dtype=float)


def _percent_color(val: float, low: float = 30.0, high: float = 70.0) -> str:
    """Traffic-light colouring for percentages."""
    if val >= high:
        return SUCCESS_COLOR
    if val >= low:
        return WARNING_COLOR
    return DANGER_COLOR


def _safe_grid(data, default: np.ndarray) -> np.ndarray:
    """Return data.grid if available, else the default."""
    if data is None:
        return default
    raw = getattr(data, "grid", None)
    if raw is None:
        return default
    return np.asarray(raw, dtype=float)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ══════════════════════════════════════════════════════════════════════════
# Panel Styling System
# ══════════════════════════════════════════════════════════════════════════


def style_panel(ax, title: str, *,
                xlabel: str = "",
                ylabel: str = "",
                show_grid: bool = True) -> None:
    """Apply consistent aerospace-themed panel styling.

    Every panel in the dashboard uses this single function so that
    padding, borders, grids, and typography remain uniform across
    all subplots.
    """
    ax.set_facecolor(PANEL_COLOR)
    ax.set_title(
        title,
        fontsize=9,
        fontweight="bold",
        color=TEXT_COLOR,
        pad=4,
        loc="left",
    )
    ax.tick_params(
        colors=SUB_TEXT_COLOR,
        labelsize=6.5,
        length=3,
        width=0.5,
        pad=2,
    )
    for spine in ax.spines.values():
        spine.set_color(BORDER_COLOR)
        spine.set_linewidth(0.5)
    if show_grid:
        ax.grid(True, color=GRID_COLOR, linewidth=0.3, alpha=0.5)
    if xlabel:
        ax.set_xlabel(xlabel, color=SUB_TEXT_COLOR, fontsize=7)
    if ylabel:
        ax.set_ylabel(ylabel, color=SUB_TEXT_COLOR, fontsize=7)
    ax.tick_params(
        which="both",
        bottom=True,
        left=True,
        labelbottom=True,
        labelleft=True,
    )


# ══════════════════════════════════════════════════════════════════════════
# DroneDashboard — Complete Redesign
# ══════════════════════════════════════════════════════════════════════════


class DroneDashboard:
    """Command-centre dashboard for autonomous drone navigation.

    Layout (12 × 12 GridSpec):
    ┌─────────────────────────────────────────────────────────────┐
    │  HEADER  (row 0, full width, 8% height)                    │
    ├──────────┬───────────────────────────────┬──────────────────┤
    │ SIDEBAR  │   WORLD NAVIGATION MAP        │ PERCEPTION MAP   │
    │ Control &│   (rows 1-10, cols 2-8)       │ MEMORY MAP       │
    │ Status   │   50% of screen               │ CONTEXT MAP      │
    │ Cards    │   Primary visual area         │ COGNITIVE STATE  │
    │          │                               │ (rows 1-10,      │
    │          │                               │  cols 8-12)      │
    ├──────────┴───────────────────────────────┴──────────────────┤
    │  METRICS TIMELINE  (rows 10-12, full width)                  │
    └─────────────────────────────────────────────────────────────┘

    Performance targets:
      - 60 FPS (minimum 30 FPS)
      - Zero artist recreation after initialisation
      - Full blitting pipeline
      - No ax.clear() / plt.cla() / plt.clf() in the update loop
    """

    # ── Initialisation ────────────────────────────────────────────────

    def __init__(self):
        plt.ion()

        self.fig = plt.figure(
            figsize=(19.2, 10.8),
            num="MJN Autonomous Drone Navigation Dashboard",
            facecolor=BACKGROUND,
            dpi=100,
        )
        # constrained_layout for responsive resizing
        self.fig.set_constrained_layout(True)

        # ── 12 × 12 GridSpec — fills 98% of window ───────────────────
        gs = GridSpec(
            12, 12,
            figure=self.fig,
            left=0.005, right=0.995,
            top=0.97, bottom=0.005,
            # hspace=0.10, wspace=0.08, # Handled by constrained_layout
        )

        # Header (row 0, full width)
        self._ax_header = self.fig.add_subplot(gs[0, :])

        # Left sidebar (rows 1-10, cols 0-2) — control & status cards
        self._ax_sidebar = self.fig.add_subplot(gs[1:10, 0:2])

        # World navigation map (rows 1-10, cols 2-8) — 50% of screen
        self._ax_world = self.fig.add_subplot(gs[1:10, 2:8])

        # Right column — 4 equal heatmaps (rows 1-10, cols 8-12)
        self._ax_perception = self.fig.add_subplot(gs[1:3, 8:12])
        self._ax_memory = self.fig.add_subplot(gs[3:5, 8:12])
        self._ax_context = self.fig.add_subplot(gs[5:7, 8:12])
        self._ax_cognitive = self.fig.add_subplot(gs[7:10, 8:12])

        # Metrics timeline (rows 10-12, full width)
        self._ax_metrics = self.fig.add_subplot(gs[10:12, :])

        # ── Heatmap axes (for blitting) ───────────────────────────────
        self._heatmap_axes = (
            self._ax_perception,
            self._ax_memory,
            self._ax_context,
            self._ax_cognitive,
        )

        # All updateable axes
        self._all_axes = (
            self._ax_header,
            self._ax_sidebar,
            self._ax_world,
            self._ax_perception,
            self._ax_memory,
            self._ax_context,
            self._ax_cognitive,
            self._ax_metrics,
        )

        # ── Running state ─────────────────────────────────────────────
        self.trail: list = []
        self._fps: float = 60.0
        self._last_time: float = time.perf_counter()
        self._bg_cache = None
        self._initialised: bool = False

        # Metrics history buffers (for the live graph)
        self._risk_history: list[float] = []
        self._memory_history: list[float] = []
        self._attention_history: list[float] = []
        self._cognitive_history: list[float] = []
        self._battery_history: list[float] = []

        # ── Build the dashboard ───────────────────────────────────────
        self._create_layout()
        self._create_artists()

        # Capture initial background for blitting
        self.fig.canvas.draw()
        self._bg_cache = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        self._initialised = True

    # ── Properties ─────────────────────────────────────────────────────

    @property
    def ax_world(self):
        return self._ax_world

    # ── Layout + Styling ──────────────────────────────────────────────

    def _create_layout(self) -> None:
        """Apply styling to every panel.  Sets aspect ratios, etc."""
        # Header
        self._ax_header.set_facecolor(HEADER_BG)
        self._ax_header.axis("off")

        # Sidebar
        self._ax_sidebar.set_facecolor(PANEL_COLOR)
        self._ax_sidebar.axis("off")

        # World navigation
        style_panel(self._ax_world, "WORLD NAVIGATION", show_grid=True)
        self._ax_world.set_aspect("equal", adjustable="box")

        # Right column heatmaps
        style_panel(self._ax_perception, "PERCEPTION MAP", show_grid=False)
        style_panel(self._ax_memory, "MEMORY MAP", show_grid=False)
        style_panel(self._ax_context, "CONTEXT MAP", show_grid=False)
        style_panel(self._ax_cognitive, "COGNITIVE STATE", show_grid=False)

        for ax in self._heatmap_axes:
            ax.set_aspect("equal", adjustable="box")
            ax.tick_params(
                bottom=False, left=False,
                labelbottom=False, labelleft=False,
            )

        # Metrics timeline
        style_panel(
            self._ax_metrics,
            "METRICS TIMELINE",
            xlabel="Frame",
            ylabel="Normalised Value",
            show_grid=True,
        )
        self._ax_metrics.set_ylim(-0.05, 1.05)
        self._ax_metrics.set_xlim(0, MAX_METRICS_HISTORY)

    # ── Artist Creation (one-time) ────────────────────────────────────

    def _create_artists(self) -> None:
        """Create all plot artists, legends, colourbars, and text fields.

        WARNING: Never call this method after __init__.
        Artists are reused every frame via set_data / set_offsets.
        """
        self._create_header_artists()
        self._create_sidebar_artists()
        self._create_world_artists()
        self._create_heatmap_artists()
        self._create_metrics_artists()

    # ── Header Artists ────────────────────────────────────────────────

    def _create_header_artists(self) -> None:
        """Create reusable text artists for the header bar."""
        # Project name (left-aligned)
        self._header_title = self._ax_header.text(
            0.012, 0.5,
            "MJN AUTONOMOUS NAVIGATION SYSTEM",
            transform=self._ax_header.transAxes,
            fontsize=12,
            fontweight="bold",
            color=TEXT_COLOR,
            va="center",
            ha="left",
            family="sans-serif",
        )

        # Status badges (right-aligned)
        badge_positions = [0.55, 0.66, 0.77, 0.88]
        badge_labels = ["FPS", "MISSION", "SYSTEM", "TIME"]
        self._header_badges: list[dict] = []

        for pos, label in zip(badge_positions, badge_labels):
            # Background box
            box = FancyBboxPatch(
                (pos, 0.12),
                0.095, 0.76,
                boxstyle=mpatches.BoxStyle("Round", pad=0.08),
                facecolor=PANEL_INNER,
                edgecolor=BORDER_COLOR,
                linewidth=0.6,
                transform=self._ax_header.transAxes,
                zorder=0,
            )
            self._ax_header.add_patch(box)

            # Label text
            lbl = self._ax_header.text(
                pos + 0.003, 0.78, label,
                transform=self._ax_header.transAxes,
                fontsize=5.5,
                color=SUB_TEXT_COLOR,
                va="top",
                ha="left",
                family="monospace",
            )

            # Value text
            val = self._ax_header.text(
                pos + 0.003, 0.38, "--",
                transform=self._ax_header.transAxes,
                fontsize=9,
                fontweight="bold",
                color=ACCENT_COLOR,
                va="top",
                ha="left",
                family="monospace",
            )

            self._header_badges.append({
                "box": box,
                "label": lbl,
                "value": val,
                "x": pos,
            })

    # ── Sidebar Artists ───────────────────────────────────────────────

    def _create_sidebar_artists(self) -> None:
        """Create telemetry card fields in the sidebar.

        Each field is a (label, value) pair rendered with monospace text.
        """
        # Sidebar title
        self._sidebar_title = self._ax_sidebar.text(
            0.06, 0.97, "TELEMETRY",
            transform=self._ax_sidebar.transAxes,
            fontsize=8,
            fontweight="bold",
            color=ACCENT_COLOR,
            va="top",
            ha="left",
            family="monospace",
        )

        # Separator
        self._sidebar_sep = self._ax_sidebar.plot(
            [0.06, 0.94], [0.91, 0.91],
            transform=self._ax_sidebar.transAxes,
            color=BORDER_COLOR,
            linewidth=0.5,
        )[0]

        # Telemetry field definitions
        sidebar_fields = [
            ("STATUS", "---", ACCENT_COLOR),
            ("PLANNER", "---", ACCENT_COLOR),
            ("BATTERY", "---", SUCCESS_COLOR),
            ("POSITION", "---", TEXT_COLOR),
            ("TARGET", "---", TARGET_COLOR),
            ("DISTANCE", "---", TEXT_COLOR),
            ("PATH LEN", "---", TEXT_COLOR),
            ("EXPLORED", "---", ACCENT_COLOR),
            ("STATIC OBJ", "---", TEXT_COLOR),
            ("DYNAMIC OBJ", "---", DYNAMIC_COLOR),
            ("EMERGENCY", "---", SUCCESS_COLOR),
            ("MEM DENSITY", "---", ACCENT_COLOR),
            ("ACTIVE CELLS", "---", ACCENT_COLOR),
            ("RISK LEVEL", "---", TEXT_COLOR),
            ("ATTENTION", "---", TEXT_COLOR),
        ]

        self._sidebar_texts: list[tuple[Text, Text, Text]] = []

        # Compute spacing to fill the sidebar
        n = len(sidebar_fields)
        row_height = 0.85 / n
        for i, (label, default, default_color) in enumerate(sidebar_fields):
            y = 0.88 - i * row_height

            # Label (dimmed)
            lbl = self._ax_sidebar.text(
                0.06, y, label,
                transform=self._ax_sidebar.transAxes,
                fontsize=5.8,
                color=SUB_TEXT_COLOR,
                va="top",
                ha="left",
                family="monospace",
            )

            # Value (bright, colour-coded)
            val = self._ax_sidebar.text(
                0.06, y - 0.5 * row_height,
                default,
                transform=self._ax_sidebar.transAxes,
                fontsize=7.5,
                fontweight="bold",
                color=default_color,
                va="top",
                ha="left",
                family="monospace",
            )

            # Divider line
            if i < n - 1:
                div = self._ax_sidebar.plot(
                    [0.06, 0.94],
                    [y - 0.85 * row_height] * 2,
                    transform=self._ax_sidebar.transAxes,
                    color=BORDER_COLOR,
                    linewidth=0.3,
                    alpha=0.4,
                )[0]
            else:
                div = None

            self._sidebar_texts.append((lbl, val, div))

    # ── World Navigation Artists ──────────────────────────────────────

    def _create_world_artists(self) -> None:
        """Create all artists for the primary navigation map.

        Uses scatter/line collections that are updated via set_offsets
        and set_data — never recreated.
        """
        # Static obstacles
        self._static_scatter: PathCollection = self._ax_world.scatter(
            [], [], s=18, c=BORDER_COLOR, alpha=0.85,
            linewidths=0, label="Static",
        )
        # Dynamic obstacles
        self._dynamic_scatter: PathCollection = self._ax_world.scatter(
            [], [], marker="D", s=80, c=DYNAMIC_COLOR,
            edgecolors="#7f1d1d", linewidths=0.6, label="Dynamic",
        )
        # Planned path
        self._path_line: Line2D = self._ax_world.plot(
            [], [], "--", linewidth=2.0, color=PATH_COLOR,
            label="Path", alpha=0.85,
        )[0]
        # Drone trail
        self._trail_line: Line2D = self._ax_world.plot(
            [], [], linewidth=2.0, color=DRONE_COLOR,
            alpha=0.6, label="Trail",
        )[0]
        # Sensor range circle (static artist — center/radius updated)
        self._sensor_circle: Circle = Circle(
            (0, 0), 1, fill=False, linestyle=":",
            linewidth=1.5, color=SENSOR_COLOR, alpha=0.7,
        )
        self._ax_world.add_patch(self._sensor_circle)
        # Drone marker
        self._drone_marker: PathCollection = self._ax_world.scatter(
            [], [], marker="^", s=260, color=DRONE_COLOR,
            edgecolors="#9A3412", linewidths=1.0, zorder=5,
            label="Drone",
        )
        # Target marker
        self._target_marker: PathCollection = self._ax_world.scatter(
            [], [], marker="*", s=380, color=TARGET_COLOR,
            edgecolors="#14532D", linewidths=1.0, zorder=4,
            label="Target",
        )

        # Legend (created once, never recreated)
        self._world_legend = self._ax_world.legend(
            loc="upper left",
            bbox_to_anchor=(1.01, 1),
            borderaxespad=0.2,
            fontsize=6.5,
            frameon=True,
            framealpha=0.9,
            facecolor=PANEL_INNER,
            edgecolor=BORDER_COLOR,
            labelcolor=TEXT_COLOR,
        )
        for text in self._world_legend.get_texts():
            text.set_fontsize(6.5)

    # ── Heatmap Artists ───────────────────────────────────────────────

    def _create_heatmap_artists(self) -> None:
        """Create imshow artists + colourbars for the four heatmaps.

        Colourbars are positioned manually to avoid overlap and are
        *never* recreated during updates (only data is refreshed).
        """
        # Perception
        self._perception_img: AxesImage = self._ax_perception.imshow(
            np.zeros((10, 10)), origin="lower", cmap="inferno",
            interpolation="nearest", vmin=0, vmax=1,
        )
        self._perception_cb: Colorbar = self.fig.colorbar(
            self._perception_img, ax=self._ax_perception,
            fraction=0.06, pad=0.04, aspect=20, shrink=0.8,
        )
        self._perception_cb.ax.tick_params(
            colors=SUB_TEXT_COLOR, labelsize=5.5, length=2,
        )
        self._perception_cb.outline.set_edgecolor(BORDER_COLOR)
        self._perception_cb.outline.set_linewidth(0.5)

        # Memory
        self._memory_img: AxesImage = self._ax_memory.imshow(
            np.zeros((10, 10)), origin="lower", cmap="YlOrRd",
            interpolation="nearest", vmin=0, vmax=1,
        )
        self._memory_cb: Colorbar = self.fig.colorbar(
            self._memory_img, ax=self._ax_memory,
            fraction=0.06, pad=0.04, aspect=20, shrink=0.8,
        )
        self._memory_cb.ax.tick_params(
            colors=SUB_TEXT_COLOR, labelsize=5.5, length=2,
        )
        self._memory_cb.outline.set_edgecolor(BORDER_COLOR)
        self._memory_cb.outline.set_linewidth(0.5)

        # Context
        self._context_img: AxesImage = self._ax_context.imshow(
            np.zeros((10, 10)), origin="lower", cmap="viridis",
            interpolation="nearest", vmin=0, vmax=1,
        )
        self._context_cb: Colorbar = self.fig.colorbar(
            self._context_img, ax=self._ax_context,
            fraction=0.06, pad=0.04, aspect=20, shrink=0.8,
        )
        self._context_cb.ax.tick_params(
            colors=SUB_TEXT_COLOR, labelsize=5.5, length=2,
        )
        self._context_cb.outline.set_edgecolor(BORDER_COLOR)
        self._context_cb.outline.set_linewidth(0.5)

        # Cognitive state
        self._cognitive_img: AxesImage = self._ax_cognitive.imshow(
            np.zeros((10, 10)), origin="lower", cmap="RdBu_r",
            interpolation="nearest", vmin=-1, vmax=1,
        )
        self._cognitive_cb: Colorbar = self.fig.colorbar(
            self._cognitive_img, ax=self._ax_cognitive,
            fraction=0.06, pad=0.04, aspect=20, shrink=0.8,
        )
        self._cognitive_cb.ax.tick_params(
            colors=SUB_TEXT_COLOR, labelsize=5.5, length=2,
        )
        self._cognitive_cb.outline.set_edgecolor(BORDER_COLOR)
        self._cognitive_cb.outline.set_linewidth(0.5)

    # ── Metrics Timeline Artists ──────────────────────────────────────

    def _create_metrics_artists(self) -> None:
        """Create multi-line chart artists for the bottom timeline.

        Five metrics: Risk, Memory, Attention, Cognitive State, Battery.
        """
        self._line_risk: Line2D = self._ax_metrics.plot(
            [], [], color=DANGER_COLOR, linewidth=1.2,
            label="Risk", alpha=0.9,
        )[0]
        self._line_memory: Line2D = self._ax_metrics.plot(
            [], [], color=WARNING_COLOR, linewidth=1.2,
            label="Memory", alpha=0.9,
        )[0]
        self._line_attention: Line2D = self._ax_metrics.plot(
            [], [], color=ACCENT_COLOR, linewidth=1.2,
            label="Attention", alpha=0.9,
        )[0]
        self._line_cognitive: Line2D = self._ax_metrics.plot(
            [], [], color=TARGET_COLOR, linewidth=1.2,
            label="Cognitive", alpha=0.9,
        )[0]
        self._line_battery: Line2D = self._ax_metrics.plot(
            [], [], color=SUCCESS_COLOR, linewidth=1.2,
            label="Battery", alpha=0.9,
        )[0]

        # Legend (created once)
        self._metrics_legend = self._ax_metrics.legend(
            loc="upper right",
            fontsize=6.5,
            frameon=True,
            framealpha=0.85,
            facecolor=PANEL_INNER,
            edgecolor=BORDER_COLOR,
            labelcolor=TEXT_COLOR,
            ncol=5,
        )
        for text in self._metrics_legend.get_texts():
            text.set_fontsize(6.5)

    # ── FPS Tracking ──────────────────────────────────────────────────

    def _compute_fps(self) -> float:
        """Compute smoothed FPS using exponential moving average."""
        now = time.perf_counter()
        dt = now - self._last_time
        self._last_time = now
        if dt > 0:
            instant_fps = 1.0 / dt
            self._fps += FPS_SMOOTHING * (instant_fps - self._fps)
        return self._fps

    # ── Build SimulationState from arguments ──────────────────────────

    def _build_state(self, **kwargs) -> SimulationState:
        """Construct a SimulationState from keyword arguments.

        This ensures every panel reads from the same data snapshot.
        """
        return SimulationState(
            world=kwargs.get("world"),
            drone=kwargs.get("drone"),
            target=kwargs.get("target", (0, 0)),
            path=kwargs.get("path"),
            smooth_path=kwargs.get("path"),
            occupancy_grid=kwargs.get("occupancy_grid"),
            perception_map=kwargs.get("perception_map"),
            risk_map=kwargs.get("risk_map"),
            memory_map=kwargs.get("memory_map"),
            context_map=kwargs.get("context_map"),
            cognitive_map=kwargs.get("cognitive_map"),
            behavior_state=kwargs.get("behavior_state"),
            mission_state=kwargs.get("mission_state"),
            planner_name=kwargs.get("planner_name"),
            emergency_state=kwargs.get("emergency_state"),
            battery_percentage=kwargs.get("battery_percentage"),
            memory_density=kwargs.get("memory_density"),
            active_cells=kwargs.get("active_cells"),
            sensor_radius=kwargs.get("sensor_radius", 8.0),
            explored_percent=kwargs.get("explored_percent", 0.0),
            timestamp=time.time(),
        )

    # ══════════════════════════════════════════════════════════════════
    # Public Update Entry Point
    # ══════════════════════════════════════════════════════════════════

    def update(self, **kwargs) -> None:
        """Update the entire dashboard from keyword arguments.

        This is the single entry point for all display updates.
        Internally it builds a SimulationState and dispatches to each
        update method.
        """
        state = self._build_state(**kwargs)
        self._update_from_state(state)

    def _update_from_state(self, state: SimulationState) -> None:
        """Update every panel from a single SimulationState.

        This guarantees perfect synchronisation — every component
        reads the same data and uses the same frame timestamp.
        """
        # Defensive guard
        if state.world is None:
            return

        fps = self._compute_fps()

        # 1. Header
        self._update_header(state, fps)

        # 2. Sidebar telemetry cards
        self._update_sidebar(state, fps)

        # 3. World navigation map
        self._update_world(state)

        # 4. Heatmap panels
        self._update_heatmaps(state)

        # 5. Metrics timeline
        self._update_metrics(state)

        # 6. Blit everything
        self._blit()

    # ══════════════════════════════════════════════════════════════════
    # Per-Panel Update Methods
    # ══════════════════════════════════════════════════════════════════

    # ── Header Update ────────────────────────────────────────────────

    def _update_header(self, state: SimulationState, fps: float) -> None:
        """Update header badges — no artist recreation."""
        mission = state.mission_state or "---"
        emergency = state.emergency_state or "NOMINAL"

        # Determine system health
        emergency_str = str(emergency)
        if "CRITICAL" in emergency_str:
            system_color = DANGER_COLOR
            system_text = "CRITICAL"
        elif "LOW_BATTERY" in emergency_str:
            system_color = WARNING_COLOR
            system_text = "LOW BAT"
        elif "NO_PATH" in emergency_str:
            system_color = WARNING_COLOR
            system_text = "NO PATH"
        elif "STUCK" in emergency_str:
            system_color = WARNING_COLOR
            system_text = "STUCK"
        else:
            system_color = SUCCESS_COLOR
            system_text = "NOMINAL"

        mission_color = (
            SUCCESS_COLOR
            if "COMPLETE" in str(mission)
            else (DANGER_COLOR if "FAIL" in str(mission) else ACCENT_COLOR)
        )

        current_time = time.strftime("%H:%M:%S", time.localtime())

        values = [
            f"{fps:.0f} FPS",
            str(mission),
            system_text,
            current_time,
        ]
        colors = [
            ACCENT_COLOR,
            mission_color,
            system_color,
            SUB_TEXT_COLOR,
        ]

        for i, badge in enumerate(self._header_badges):
            if i < len(values):
                badge["value"].set_text(values[i])
                badge["value"].set_color(colors[i])

    # ── Sidebar Update ────────────────────────────────────────────────

    def _update_sidebar(self, state: SimulationState, fps: float) -> None:
        """Update the sidebar telemetry cards."""
        world = state.world
        drone = state.drone
        target = state.target
        path = state.path

        # Defensive defaults
        drone_x = getattr(drone, "x", 0)
        drone_y = getattr(drone, "y", 0)
        target_x = target[0] if target else 0
        target_y = target[1] if target else 0

        distance = np.hypot(target_x - drone_x, target_y - drone_y)
        path_len = len(path) if path is not None else 0
        static_count = len(getattr(world, "obstacles", []))
        dynamic_count = len(getattr(world, "dynamic_obstacles", []))
        explored = state.explored_percent

        battery = state.battery_percentage
        battery_text = f"{battery:.1f}%" if battery is not None else "---"
        battery_color = (
            _percent_color(battery) if battery is not None else TEXT_COLOR
        )

        emergency_str = str(state.emergency_state or "NORMAL")
        emergency_color_map = {
            "NORMAL": SUCCESS_COLOR,
            "LOW_BATTERY": WARNING_COLOR,
            "CRITICAL_BATTERY": DANGER_COLOR,
            "CRITICAL": DANGER_COLOR,
            "NO_PATH": DANGER_COLOR,
            "STUCK": DANGER_COLOR,
        }
        emergency_color = emergency_color_map.get(emergency_str, TEXT_COLOR)

        risk_level = np.mean(self._risk_history[-10:]) if self._risk_history else 0.0
        attention = (
            np.mean(self._cognitive_history[-10:])
            if self._cognitive_history else 0.5
        )

        values = [
            (str(state.mission_state or "---"), ACCENT_COLOR),  # STATUS
            (str(state.planner_name or "---"), ACCENT_COLOR),   # PLANNER
            (battery_text, battery_color),                       # BATTERY
            (f"({drone_x:.1f}, {drone_y:.1f})", TEXT_COLOR),    # POSITION
            (f"({target_x:.0f}, {target_y:.0f})", TARGET_COLOR),# TARGET
            (                                                      # DISTANCE
                f"{distance:.1f} m",
                SUCCESS_COLOR if distance < 30
                else (WARNING_COLOR if distance < 60 else DANGER_COLOR),
            ),
            (f"{path_len}", TEXT_COLOR),                         # PATH LEN
            (f"{explored:.1f}%", ACCENT_COLOR),                  # EXPLORED
            (f"{static_count}", TEXT_COLOR),                     # STATIC OBJ
            (                                                      # DYNAMIC OBJ
                f"{dynamic_count}",
                DYNAMIC_COLOR if dynamic_count > 0 else TEXT_COLOR,
            ),
            (emergency_str, emergency_color),                    # EMERGENCY
            (                                                      # MEM DENSITY
                f"{state.memory_density:.1f}%" if state.memory_density is not None
                else "---",
                ACCENT_COLOR,
            ),
            (                                                      # ACTIVE CELLS
                str(state.active_cells) if state.active_cells is not None
                else "---",
                ACCENT_COLOR,
            ),
            (                                                      # RISK LEVEL
                f"{risk_level:.2f}",
                WARNING_COLOR if risk_level > 0.5 else SUCCESS_COLOR,
            ),
            (f"{attention:.2f}", ACCENT_COLOR),                  # ATTENTION
        ]

        for i, (text_val, color) in enumerate(values):
            if i < len(self._sidebar_texts):
                lbl, val, _ = self._sidebar_texts[i]
                val.set_text(text_val)
                val.set_color(color)

    # ── World Navigation Update ───────────────────────────────────────

    def _update_world(self, state: SimulationState) -> None:
        """Update the primary navigation map."""
        world = state.world
        drone = state.drone
        target = state.target
        path = state.path

        # Defensive bounds
        world_width = getattr(world, "width", 100)
        world_height = getattr(world, "height", 100)

        if world_width > 0 and world_height > 0:
            self._ax_world.set_xlim(-0.5, world_width - 0.5)
            self._ax_world.set_ylim(-0.5, world_height - 0.5)

        # Static obstacles
        obstacles = getattr(world, "obstacles", [])
        self._static_scatter.set_offsets(_as_offsets(obstacles))

        # Dynamic obstacles
        dynamic_obs = getattr(world, "dynamic_obstacles", [])
        self._dynamic_scatter.set_offsets(
            _as_offsets((o.x, o.y) for o in dynamic_obs)
        )

        # Path — handle None, empty list, and numpy arrays
        if path is not None and len(path) > 0:
            path_array = np.asarray(path)
            self._path_line.set_data(path_array[:, 0], path_array[:, 1])
        else:
            self._path_line.set_data([], [])

        # Trail
        drone_x = getattr(drone, "x", 0)
        drone_y = getattr(drone, "y", 0)
        self.trail.append((drone_x, drone_y))
        self.trail = self.trail[-MAX_TRAIL_POINTS:]
        if self.trail:
            trail_array = np.asarray(self.trail)
            self._trail_line.set_data(trail_array[:, 0], trail_array[:, 1])
        else:
            self._trail_line.set_data([], [])

        # Sensor circle
        self._sensor_circle.center = (drone_x, drone_y)
        self._sensor_circle.set_radius(state.sensor_radius)

        # Drone marker
        self._drone_marker.set_offsets([[drone_x, drone_y]])

        # Target marker
        target_x = target[0] if target else 0
        target_y = target[1] if target else 0
        self._target_marker.set_offsets([[target_x, target_y]])

    # ── Heatmap Update ────────────────────────────────────────────────

    def _update_heatmaps(self, state: SimulationState) -> None:
        """Update all four heatmap panels from simulation state."""
        world = state.world
        w = getattr(world, "width", 100)
        h = getattr(world, "height", 100)

        # Default empty grid
        empty = np.zeros((h, w), dtype=float)

        # Perception
        data = _safe_grid(state.perception_map, empty)
        self._perception_img.set_data(data)
        self._perception_img.set_extent([-0.5, w - 0.5, -0.5, h - 0.5])
        self._ax_perception.set_xlim(-0.5, w - 0.5)
        self._ax_perception.set_ylim(-0.5, h - 0.5)

        # Memory
        if state.memory_map is not None:
            raw = getattr(state.memory_map, "grid", None)
            if raw is None:
                raw = np.zeros((h, w))
            data = np.asarray(raw, dtype=float)
        else:
            data = empty
        self._memory_img.set_data(data)
        self._memory_img.set_extent([-0.5, w - 0.5, -0.5, h - 0.5])
        self._ax_memory.set_xlim(-0.5, w - 0.5)
        self._ax_memory.set_ylim(-0.5, h - 0.5)

        # Context
        data = _safe_grid(state.context_map, empty)
        self._context_img.set_data(data)
        self._context_img.set_extent([-0.5, w - 0.5, -0.5, h - 0.5])
        self._ax_context.set_xlim(-0.5, w - 0.5)
        self._ax_context.set_ylim(-0.5, h - 0.5)

        # Cognitive
        data = _safe_grid(state.cognitive_map, empty)
        self._cognitive_img.set_data(data)
        self._cognitive_img.set_extent([-0.5, w - 0.5, -0.5, h - 0.5])
        self._ax_cognitive.set_xlim(-0.5, w - 0.5)
        self._ax_cognitive.set_ylim(-0.5, h - 0.5)

    # ── Metrics Timeline Update ───────────────────────────────────────

    def _update_metrics(self, state: SimulationState) -> None:
        """Update the multi-line metrics timeline.

        Maintains a rolling window of MAX_METRICS_HISTORY points.
        """
        # Extract current metric values (normalised 0-1)
        world = state.world
        dynamic_obs = getattr(world, "dynamic_obstacles", [])
        obstacles = getattr(world, "obstacles", [])
        total_obstacles = len(obstacles) + len(dynamic_obs)

        # Risk: normalised obstacle count (cap at 50)
        risk = _clamp(total_obstacles / 50.0, 0, 1)

        # Memory density
        memory = (
            state.memory_density / 100.0
            if state.memory_density is not None else 0.0
        )

        # Cognitive: normalised exploration
        cognitive = state.explored_percent / 100.0

        # Battery
        battery = (
            state.battery_percentage / 100.0
            if state.battery_percentage is not None else 1.0
        )

        # Attention: inverse of distance to target
        target = state.target
        drone = state.drone
        if target and drone:
            dx = target[0] - getattr(drone, "x", 0)
            dy = target[1] - getattr(drone, "y", 0)
            dist = np.hypot(dx, dy)
            max_dist = np.hypot(
                getattr(world, "width", 100),
                getattr(world, "height", 100),
            )
            attention = 1.0 - _clamp(dist / max_dist, 0, 1)
        else:
            attention = 0.5

        # Append to rolling buffers
        self._risk_history.append(risk)
        self._memory_history.append(memory)
        self._attention_history.append(attention)
        self._cognitive_history.append(cognitive)
        self._battery_history.append(battery)

        # Trim
        if len(self._risk_history) > MAX_METRICS_HISTORY:
            self._risk_history = self._risk_history[-MAX_METRICS_HISTORY:]
            self._memory_history = self._memory_history[-MAX_METRICS_HISTORY:]
            self._attention_history = self._attention_history[-MAX_METRICS_HISTORY:]
            self._cognitive_history = self._cognitive_history[-MAX_METRICS_HISTORY:]
            self._battery_history = self._battery_history[-MAX_METRICS_HISTORY:]

        # Update line data
        n = len(self._risk_history)
        x = np.arange(n)

        self._line_risk.set_data(x, self._risk_history)
        self._line_memory.set_data(x, self._memory_history)
        self._line_attention.set_data(x, self._attention_history)
        self._line_cognitive.set_data(x, self._cognitive_history)
        self._line_battery.set_data(x, self._battery_history)

        # Maintain axis limits
        self._ax_metrics.set_xlim(max(0, n - MAX_METRICS_HISTORY), max(MAX_METRICS_HISTORY, n))
        self._ax_metrics.set_ylim(-0.05, 1.05)

    # ══════════════════════════════════════════════════════════════════
    # Blitting Pipeline
    # ══════════════════════════════════════════════════════════════════

    def _blit(self) -> None:
        """Blit all axes for smooth, tear-free rendering.

        Falls back to draw_idle() if blitting fails (e.g., after resize).
        """
        if not self._initialised:
            return

        if self._bg_cache is not None:
            try:
                self.fig.canvas.restore_region(self._bg_cache)
                for ax in self._all_axes:
                    self.fig.canvas.blit(ax.bbox)
                # Extra blit for colourbar axes
                for cb in (
                    self._perception_cb,
                    self._memory_cb,
                    self._context_cb,
                    self._cognitive_cb,
                ):
                    self.fig.canvas.blit(cb.ax.bbox)
            except Exception:
                self.fig.canvas.draw_idle()
        else:
            self.fig.canvas.draw_idle()

        self.fig.canvas.flush_events()
        # Only pause for interactive backends
        if "agg" not in plt.get_backend().lower():
            plt.pause(0.0001)

    # ── Public Redraw ─────────────────────────────────────────────────

    def render_frame(self) -> None:
        """Force a full redraw (used after resize or simulation reset)."""
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()
        if "agg" not in plt.get_backend().lower():
            plt.pause(0.0005)


# ══════════════════════════════════════════════════════════════════════════
# Module-level draw() — Backward Compatible Entry Point
# ══════════════════════════════════════════════════════════════════════════


def draw(
    world,
    drone,
    target,
    path=None,
    occupancy_grid=None,
    sensor_radius=8,
    perception_map=None,
    risk_map=None,
    memory_map=None,
    behavior_state=None,
    mission_state=None,
    planner_name=None,
    emergency_state=None,
    battery_percentage=None,
    memory_density=None,
    active_cells=None,
    context_map=None,
    cognitive_map=None,
    explored_percent=None,
) -> None:
    """Main entry point called from mission simulation.

    Creates or reuses the singleton dashboard and pushes new data.
    This function is fully backward-compatible with the existing API.

    All parameters are forwarded to SimulationState, ensuring that
    every panel updates from the same frame of data.
    """
    global _dashboard

    # Defensive: recreate dashboard if figure was closed
    if _dashboard is None or not plt.fignum_exists(_dashboard.fig.number):
        _dashboard = DroneDashboard()

    _dashboard.update(
        world=world,
        drone=drone,
        target=target,
        path=path,
        occupancy_grid=occupancy_grid,
        sensor_radius=sensor_radius,
        perception_map=perception_map,
        risk_map=risk_map,
        memory_map=memory_map,
        context_map=context_map,
        cognitive_map=cognitive_map,
        behavior_state=behavior_state,
        mission_state=mission_state,
        planner_name=planner_name,
        emergency_state=emergency_state,
        battery_percentage=battery_percentage,
        memory_density=memory_density,
        active_cells=active_cells,
        explored_percent=explored_percent or 0.0,
    )


def reset_dashboard() -> None:
    """Reset the dashboard singleton (e.g., on simulation restart)."""
    global _dashboard
    if _dashboard is not None:
        try:
            plt.close(_dashboard.fig)
        except Exception:
            pass
        _dashboard = None