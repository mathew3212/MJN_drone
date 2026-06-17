"""
Military-Grade Visualization Engine
=====================================
Cinematic, tactical-grade rendering for autonomous drone simulation.

Features:
  - Terrain rendering with height-based shading
  - Weather effects (rain, snow, fog, clouds, wind arrows)
  - Day/night cycle with atmospheric lighting
  - Military tactical overlays (zones, threat rings, HUD)
  - Particle effects (dust, smoke, explosions)
  - Enhanced drone with propeller animation
  - Convoy and enemy drone rendering
  - Professional military command center UI
  - Full backward compatibility with existing draw() API
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional, Any

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.gridspec import GridSpec
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.patches import (
    FancyBboxPatch, Circle, FancyArrowPatch, Wedge,
)
from matplotlib.text import Text

# ── Color Palette: Military Dark Theme ───────────────────────────────────────
BG_DARK = "#060E1A"
BG_PANEL = "#0C1524"
BG_INNER = "#0F172A"
BORDER = "#1E293B"
BORDER_BRIGHT = "#334155"
TEXT = "#E2E8F0"
TEXT_DIM = "#94A3B8"
ACCENT = "#38BDF8"
ACCENT2 = "#06B6D4"
SUCCESS = "#22C55E"
WARNING = "#F59E0B"
DANGER = "#EF4444"
PATH_COL = "#38BDF8"
DRONE_COL = "#FF9800"
TARGET_COL = "#00FF88"
DYNAMIC_COL = "#FF3B30"
ENEMY_COL = "#DC2626"
CONVOY_COL = "#F97316"
GRID_COL = "#1E293B"
TERRAIN_GRID = "#15221A"
HEADER_BG = "#081428"
LZ_COL = "#22C55E"
RESTRICTED_COL = "#EF4444"
MISSION_COL = "#F59E0B"
RADAR_COL = "#8B5CF6"
WATER_COL = "#1E40AF"
FOG_COL = "#64748B"
RAIN_COL = "#60A5FA"
SNOW_COL = "#DBEAFE"
CLOUD_COL = "#475569"
WIND_COL = "#94A3B8"
BANNER_BG = "#0F172A"

# ── Constants ────────────────────────────────────────────────────────────────
MAX_TRAIL = 400
FPS_SMOOTH = 0.12
MAX_HIST = 500


# ── Module singleton ─────────────────────────────────────────────────────────
_mil_dashboard: Optional["MilitaryDashboard"] = None


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _offsets(pts) -> np.ndarray:
    pts = list(pts)
    return np.asarray(pts, dtype=float) if pts else np.empty((0, 2))


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _pct_color(v, lo=30, hi=70):
    return SUCCESS if v >= hi else (WARNING if v >= lo else DANGER)


def _safe_grid(data, default):
    if data is None:
        return default
    raw = getattr(data, "grid", None)
    return np.asarray(raw, dtype=float) if raw is not None else default


# ══════════════════════════════════════════════════════════════════════════════
# Military Dashboard
# ══════════════════════════════════════════════════════════════════════════════


class MilitaryDashboard:
    """Full military-grade command-centre dashboard.

    Layout (16×16 GridSpec):
    ┌──────────────────────────────────────────────────────────────────┐
    │  HEADER  (row 0, full width)                                     │
    ├──────────┬──────────────────────────────┬────────────────────────┤
    │ SIDEBAR  │   WORLD / TERRAIN MAP         │  HEATMAPS (4 panels)  │
    │ Telemetry│   with tactical overlays      │  Perception / Memory   │
    │ & Status │   Primary visual area          │  Context / Cognitive   │
    │          │   rows 1-12, cols 2-9         │  rows 1-12, cols 9-16 │
    ├──────────┴──────────────────────────────┴────────────────────────┤
    │  METRICS TIMELINE  (rows 12-16, full width)                      │
    └──────────────────────────────────────────────────────────────────┘
    """

    def __init__(self):
        plt.ion()
        self.fig = plt.figure(
            figsize=(20.0, 11.25),
            num="MJN Military Drone Command Center",
            facecolor=BG_DARK,
            dpi=100,
        )
        self.fig.set_constrained_layout(True)

        gs = GridSpec(
            16, 16,
            figure=self.fig,
            left=0.004, right=0.996,
            top=0.975, bottom=0.005,
        )

        # Axes
        self._ax_hdr = self.fig.add_subplot(gs[0, :])
        self._ax_side = self.fig.add_subplot(gs[1:13, 0:2])
        self._ax_world = self.fig.add_subplot(gs[1:13, 2:9])
        self._ax_p1 = self.fig.add_subplot(gs[1:4, 9:16])
        self._ax_p2 = self.fig.add_subplot(gs[4:7, 9:16])
        self._ax_p3 = self.fig.add_subplot(gs[7:10, 9:16])
        self._ax_p4 = self.fig.add_subplot(gs[10:13, 9:16])
        self._ax_metrics = self.fig.add_subplot(gs[13:16, :])

        self._heat_axes = (self._ax_p1, self._ax_p2, self._ax_p3, self._ax_p4)
        self._all_axes = (
            self._ax_hdr, self._ax_side, self._ax_world,
            self._ax_p1, self._ax_p2, self._ax_p3, self._ax_p4,
            self._ax_metrics,
        )

        self.trail: list = []
        self._fps: float = 60.0
        self._last_t: float = time.perf_counter()
        self._bg_cache = None
        self._init_done = False
        self._frame_count = 0

        # History
        self._hist_risk: list[float] = []
        self._hist_mem: list[float] = []
        self._hist_att: list[float] = []
        self._hist_cog: list[float] = []
        self._hist_bat: list[float] = []
        self._hist_speed: list[float] = []

        self._style_layout()
        self._create_artists()
        self.fig.canvas.draw()
        self._bg_cache = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        self._init_done = True

    # ── Layout ─────────────────────────────────────────────────────────

    def _style_layout(self):
        self._ax_hdr.set_facecolor(HEADER_BG)
        self._ax_hdr.axis("off")
        self._ax_side.set_facecolor(BG_PANEL)
        self._ax_side.axis("off")
        self._ax_world.set_facecolor(BG_INNER)
        self._ax_world.set_aspect("equal", adjustable="box")
        for ax in self._heat_axes:
            ax.set_facecolor(BG_INNER)
            ax.set_aspect("equal", adjustable="box")
            ax.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False)
        self._ax_metrics.set_facecolor(BG_PANEL)
        self._ax_metrics.set_ylim(-0.05, 1.05)
        self._ax_metrics.set_xlim(0, MAX_HIST)
        # Grid styling
        for ax in [self._ax_world, self._ax_metrics]:
            ax.grid(True, color=GRID_COL, linewidth=0.3, alpha=0.4)
        for spine in self._ax_world.spines.values():
            spine.set_color(BORDER)
            spine.set_linewidth(0.5)
        for spine in self._ax_metrics.spines.values():
            spine.set_color(BORDER)
            spine.set_linewidth(0.5)

    # ── Artist Creation ────────────────────────────────────────────────

    def _create_artists(self):
        self._create_header()
        self._create_sidebar()
        self._create_world_artists()
        self._create_heatmap_artists()
        self._create_metrics_artists()

    def _create_header(self):
        self._hdr_title = self._ax_hdr.text(
            0.008, 0.5, "MJN  AUTONOMOUS  DRONE  COMMAND  CENTER",
            transform=self._ax_hdr.transAxes,
            fontsize=13, fontweight="bold", color=TEXT, va="center", family="sans-serif",
        )
        # Classification banner
        self._hdr_class = self._ax_hdr.text(
            0.35, 0.5, "UNCLASSIFIED // SIMULATION",
            transform=self._ax_hdr.transAxes,
            fontsize=7, color="#475569", va="center", family="monospace",
            fontweight="bold",
        )
        # Badges
        badges = [("FPS", ACCENT), ("MISSION", SUCCESS), ("SYSTEM", SUCCESS),
                  ("TIME", TEXT_DIM), ("WEATHER", ACCENT2), ("DAY/NIGHT", WARNING)]
        self._hdr_badges = []
        for i, (lbl, _) in enumerate(badges):
            x = 0.50 + i * 0.083
            box = FancyBboxPatch(
                (x, 0.1), 0.078, 0.8,
                boxstyle=mpatches.BoxStyle("Round", pad=0.06),
                facecolor=BG_INNER, edgecolor=BORDER, linewidth=0.6,
                transform=self._ax_hdr.transAxes, zorder=0,
            )
            self._ax_hdr.add_patch(box)
            lt = self._ax_hdr.text(
                x + 0.005, 0.82, lbl,
                transform=self._ax_hdr.transAxes,
                fontsize=5, color=TEXT_DIM, va="top", family="monospace",
            )
            vt = self._ax_hdr.text(
                x + 0.005, 0.42, "--",
                transform=self._ax_hdr.transAxes,
                fontsize=8, fontweight="bold", color=ACCENT, va="top", family="monospace",
            )
            self._hdr_badges.append({"box": box, "lbl": lt, "val": vt, "x": x})

    def _create_sidebar(self):
        self._side_title = self._ax_side.text(
            0.06, 0.97, "TACTICAL TELEMETRY",
            transform=self._ax_side.transAxes,
            fontsize=8, fontweight="bold", color=ACCENT, va="top", family="monospace",
        )
        self._ax_side.plot(
            [0.06, 0.94], [0.935, 0.935],
            transform=self._ax_side.transAxes, color=BORDER, linewidth=0.5,
        )

        fields = [
            ("STATUS", ACCENT), ("PLANNER", ACCENT), ("BATTERY", SUCCESS),
            ("POSITION", TEXT), ("TARGET", TARGET_COL), ("DISTANCE", TEXT),
            ("PATH LEN", TEXT), ("EXPLORED", ACCENT), ("STATIC OBJ", TEXT),
            ("DYNAMIC OBJ", DYNAMIC_COL), ("ENEMY DRONES", ENEMY_COL),
            ("CONVOYS", CONVOY_COL), ("EMERGENCY", SUCCESS), ("MEM DENSITY", ACCENT),
            ("RISK LEVEL", TEXT), ("WIND", WIND_COL), ("TERRAIN", TEXT),
            ("WEATHER", ACCENT2), ("TIME OF DAY", WARNING),
        ]
        n = len(fields)
        rh = 0.88 / n
        self._side_texts = []
        for i, (lbl, col) in enumerate(fields):
            y = 0.91 - i * rh
            lt = self._ax_side.text(
                0.06, y, lbl,
                transform=self._ax_side.transAxes,
                fontsize=5.5, color=TEXT_DIM, va="top", family="monospace",
            )
            vt = self._ax_side.text(
                0.06, y - 0.55 * rh, "--",
                transform=self._ax_side.transAxes,
                fontsize=7, fontweight="bold", color=col, va="top", family="monospace",
            )
            if i < n - 1:
                self._ax_side.plot(
                    [0.06, 0.94], [y - 0.85 * rh] * 2,
                    transform=self._ax_side.transAxes,
                    color=BORDER, linewidth=0.3, alpha=0.4,
                )
            self._side_texts.append((lt, vt))

    def _create_world_artists(self):
        ax = self._ax_world
        # Terrain image (updated via set_data)
        self._terrain_img = ax.imshow(
            np.zeros((10, 10, 3)),
            origin="lower", interpolation="nearest", aspect="equal", alpha=0.9,
        )
        # Static obstacles
        self._static_sc = ax.scatter(
            [], [], s=14, c=BORDER_BRIGHT, alpha=0.7, linewidths=0, zorder=2,
        )
        # Dynamic obstacles
        self._dynamic_sc = ax.scatter(
            [], [], marker="D", s=60, c=DYNAMIC_COL,
            edgecolors="#7f1d1d", linewidths=0.5, zorder=4,
        )
        # Enemy drones
        self._enemy_sc = ax.scatter(
            [], [], marker="v", s=100, c=ENEMY_COL,
            edgecolors="#991b1b", linewidths=0.8, zorder=5,
        )
        # Convoys
        self._convoy_sc = ax.scatter(
            [], [], marker="s", s=50, c=CONVOY_COL,
            edgecolors="#9a3412", linewidths=0.5, zorder=4,
        )
        # Path
        self._path_line = ax.plot(
            [], [], "--", linewidth=2.0, color=PATH_COL, alpha=0.85, zorder=3,
        )[0]
        # Trail
        self._trail_line = ax.plot(
            [], [], linewidth=2.0, color=DRONE_COL, alpha=0.5, zorder=3,
        )[0]
        # Sensor circle
        self._sensor_ring = Circle(
            (0, 0), 1, fill=False, linestyle=":", linewidth=1.2,
            color=ACCENT, alpha=0.5, zorder=3,
        )
        ax.add_patch(self._sensor_ring)
        # Threat rings (for dynamic obstacles)
        self._threat_ring = Circle(
            (0, 0), 3, fill=True, facecolor=DYNAMIC_COL,
            alpha=0.06, edgecolor=DYNAMIC_COL, linewidth=0.5, zorder=1,
        )
        ax.add_patch(self._threat_ring)
        # Drone
        self._drone_sc = ax.scatter(
            [], [], marker="^", s=300, color=DRONE_COL,
            edgecolors="#9A3412", linewidths=1.2, zorder=10,
        )
        # Drone heading arrow
        self._drone_arrow = ax.annotate(
            "", xy=(0, 0), xytext=(0, 0),
            arrowprops=dict(arrowstyle="->", color=DRONE_COL, lw=1.5),
            zorder=11,
        )
        # Target
        self._target_sc = ax.scatter(
            [], [], marker="*", s=450, color=TARGET_COL,
            edgecolors="#14532D", linewidths=1.0, zorder=9,
        )
        # Military zones (drawn as patches)
        self._zone_patches: list = []
        # Wind arrows
        self._wind_arrows = []
        # Precipitation scatter
        self._rain_sc = ax.scatter(
            [], [], s=2, c=RAIN_COL, alpha=0.3, linewidths=0, zorder=12,
        )
        # Cloud patches
        self._cloud_patches: list = []
        # Particle scatter
        self._particle_sc = ax.scatter(
            [], [], s=15, c=WIND_COL, alpha=0.4, linewidths=0, zorder=12,
        )

        # Legend
        legend_items = [
            Line2D([0], [0], marker="^", color="w", markerfacecolor=DRONE_COL,
                   markersize=8, label="Drone"),
            Line2D([0], [0], marker="*", color="w", markerfacecolor=TARGET_COL,
                   markersize=10, label="Target"),
            Line2D([0], [0], marker="D", color="w", markerfacecolor=DYNAMIC_COL,
                   markersize=6, label="Dynamic"),
            Line2D([0], [0], marker="v", color="w", markerfacecolor=ENEMY_COL,
                   markersize=7, label="Enemy"),
            Line2D([0], [0], marker="s", color="w", markerfacecolor=CONVOY_COL,
                   markersize=6, label="Convoy"),
            Line2D([0], [0], color=PATH_COL, linewidth=2, linestyle="--", label="Path"),
            Line2D([0], [0], color=DRONE_COL, linewidth=2, label="Trail"),
        ]
        self._legend = ax.legend(
            handles=legend_items, loc="upper left",
            bbox_to_anchor=(1.01, 1), fontsize=6, frameon=True,
            framealpha=0.9, facecolor=BG_INNER, edgecolor=BORDER,
            labelcolor=TEXT,
        )

    def _create_heatmap_artists(self):
        labels = ["PERCEPTION", "MEMORY", "CONTEXT", "COGNITIVE"]
        cmaps = ["inferno", "YlOrRd", "viridis", "RdBu_r"]
        vmins = [0, 0, 0, -1]
        vmaxs = [1, 1, 1, 1]
        self._hm_imgs = []
        self._hm_cbs = []
        for ax, lbl, cm, mn, mx in zip(self._heat_axes, labels, cmaps, vmins, vmaxs):
            img = ax.imshow(np.zeros((10, 10)), origin="lower", cmap=cm,
                            interpolation="nearest", vmin=mn, vmax=mx)
            cb = self.fig.colorbar(img, ax=ax, fraction=0.05, pad=0.03, aspect=18, shrink=0.85)
            cb.ax.tick_params(colors=TEXT_DIM, labelsize=5, length=2)
            cb.outline.set_edgecolor(BORDER)
            cb.outline.set_linewidth(0.5)
            ax.set_title(lbl, fontsize=7, fontweight="bold", color=TEXT, pad=3, loc="left")
            for spine in ax.spines.values():
                spine.set_color(BORDER)
                spine.set_linewidth(0.4)
            self._hm_imgs.append(img)
            self._hm_cbs.append(cb)

    def _create_metrics_artists(self):
        ax = self._ax_metrics
        cols = [DANGER_COLOR_STR if False else DANGER, WARNING, ACCENT, TARGET_COL, SUCCESS, ACCENT2]
        names = ["Risk", "Memory", "Attention", "Cognitive", "Battery", "Speed"]
        self._metric_lines = []
        for c, n in zip(cols, names):
            ln = ax.plot([], [], color=c, linewidth=1.1, label=n, alpha=0.9)[0]
            self._metric_lines.append(ln)
        leg = ax.legend(
            loc="upper right", fontsize=6, frameon=True, framealpha=0.85,
            facecolor=BG_INNER, edgecolor=BORDER, labelcolor=TEXT, ncol=6,
        )
        for t in leg.get_texts():
            t.set_fontsize(6)
        ax.set_xlabel("Frame", color=TEXT_DIM, fontsize=6)
        ax.set_ylabel("Normalised", color=TEXT_DIM, fontsize=6)
        ax.tick_params(colors=TEXT_DIM, labelsize=6)

    # ── FPS ────────────────────────────────────────────────────────────

    def _fps_calc(self):
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now
        if dt > 0:
            self._fps += FPS_SMOOTH * (1.0 / dt - self._fps)
        return self._fps

    # ══════════════════════════════════════════════════════════════════
    # PUBLIC UPDATE
    # ══════════════════════════════════════════════════════════════════

    def update(self, **kw):
        """Update dashboard. Accepts all old draw() kwargs plus new ones."""
        fps = self._fps_calc()
        self._frame_count += 1

        world = kw.get("world")
        drone = kw.get("drone")
        target = kw.get("target", (0, 0))
        path = kw.get("path")
        occ = kw.get("occupancy_grid")
        perception = kw.get("perception_map")
        risk = kw.get("risk_map")
        memory = kw.get("memory_map")
        context = kw.get("context_map")
        cognitive = kw.get("cognitive_map")
        sensor_r = kw.get("sensor_radius", 8)
        beh = kw.get("behavior_state", "---")
        mis = kw.get("mission_state", "---")
        plan = kw.get("planner_name", "---")
        emerg = kw.get("emergency_state", "NORMAL")
        bat = kw.get("battery_percentage")
        mem_d = kw.get("memory_density")
        act_c = kw.get("active_cells")
        exp_p = kw.get("explored_percent", 0.0)

        if world is None:
            return

        ww = getattr(world, "width", 100)
        wh = getattr(world, "height", 100)
        dx = getattr(drone, "x", 0)
        dy = getattr(drone, "y", 0)
        tx = target[0] if target else 0
        ty = target[1] if target else 1

        # ── Header ──
        self._update_header(fps, mis, emerg, world)

        # ── World map ──
        self._update_world_map(world, drone, target, path, dx, dy, tx, ty, sensor_r)

        # ── Sidebar ──
        self._update_sidebar(world, drone, target, path, beh, mis, plan, emerg,
                             bat, mem_d, act_c, exp_p, dx, dy, tx, ty)

        # ── Heatmaps ──
        self._update_heatmaps(world, perception, memory, context, cognitive)

        # ── Metrics ──
        self._update_metrics(world, drone, target, bat, exp_p, mem_d)

        # ── Blit ──
        self._blit()

    # ── Header ──

    def _update_header(self, fps, mis, emerg, world):
        emerg_s = str(emerg)
        if "CRITICAL" in emerg_s:
            scol, stxt = DANGER, "CRITICAL"
        elif "LOW" in emerg_s:
            scol, stxt = WARNING, "LOW BAT"
        elif "NO_PATH" in emerg_s or "STUCK" in emerg_s:
            scol, stxt = WARNING, emerg_s
        else:
            scol, stxt = SUCCESS, "NOMINAL"
        mcol = SUCCESS if "COMPLETE" in str(mis) else (DANGER if "FAIL" in str(mis) else ACCENT)

        # Get weather/time info
        weather_str = "--"
        tod_str = "--"
        if hasattr(world, "weather"):
            weather_str = world.weather.get_weather_display()[:8]
            tod_str = world.weather.atmosphere.time_of_day.name[:6]

        vals = [
            f"{fps:.0f}", str(mis)[:12], stxt,
            time.strftime("%H:%M:%S"), weather_str, tod_str,
        ]
        cols = [ACCENT, mcol, scol, TEXT_DIM, ACCENT2, WARNING]
        for i, badge in enumerate(self._hdr_badges):
            if i < len(vals):
                badge["val"].set_text(vals[i])
                badge["val"].set_color(cols[i])

    # ── World Map ──

    def _update_world_map(self, world, drone, target, path, dx, dy, tx, ty, sensor_r):
        ax = self._ax_world
        ww = getattr(world, "width", 100)
        wh = getattr(world, "height", 100)
        ax.set_xlim(-0.5, ww - 0.5)
        ax.set_ylim(-0.5, wh - 0.5)

        # ── Terrain background ──
        if hasattr(world, "terrain"):
            terrain_img = world.terrain.get_terrain_color_array()
            # Apply ambient lighting
            if hasattr(world, "weather"):
                light = world.weather.atmosphere.ambient_light
                terrain_img = (terrain_img * (0.3 + 0.7 * light)).clip(0, 1)
            self._terrain_img.set_data(terrain_img)
            self._terrain_img.set_extent([-0.5, ww - 0.5, -0.5, wh - 0.5])
            self._terrain_img.set_alpha(0.85)
        else:
            self._terrain_img.set_alpha(0.0)

        # ── Static obstacles (non-terrain) ──
        obstacles = getattr(world, "obstacles", set())
        # Filter out terrain obstacles (already rendered)
        non_terrain = []
        for pos in obstacles:
            if hasattr(world, "terrain"):
                tt = world.terrain.terrain_types[min(pos[1], world.height - 1), min(pos[0], world.width - 1)]
                from src.core.terrain import TerrainType
                if tt not in (TerrainType.BUILDING.value, TerrainType.TREE.value,
                              TerrainType.WATER.value, TerrainType.ROCK.value):
                    non_terrain.append(pos)
            else:
                non_terrain.append(pos)
        self._static_sc.set_offsets(_offsets(non_terrain) if non_terrain else np.empty((0, 2)))

        # ── Dynamic obstacles ──
        dyn = getattr(world, "dynamic_obstacles", [])
        self._dynamic_sc.set_offsets(_offsets((o.x, o.y) for o in dyn))

        # ── Enemy drones ──
        enemies = getattr(world, "enemy_drones", [])
        self._enemy_sc.set_offsets(_offsets((d.x, d.y) for d in enemies))

        # ── Convoys ──
        convoys = getattr(world, "convoys", [])
        convoy_pts = []
        for cv in convoys:
            for p in cv.positions:
                convoy_pts.append(p)
        self._convoy_sc.set_offsets(_offsets(convoy_pts) if convoy_pts else np.empty((0, 2)))

        # ── Military zones ──
        self._update_military_zones(world)

        # ── Path ──
        if path and len(path) > 0:
            pa = np.asarray(path)
            self._path_line.set_data(pa[:, 0], pa[:, 1])
        else:
            self._path_line.set_data([], [])

        # ── Trail ──
        self.trail.append((dx, dy))
        self.trail = self.trail[-MAX_TRAIL:]
        if self.trail:
            ta = np.asarray(self.trail)
            self._trail_line.set_data(ta[:, 0], ta[:, 1])

        # ── Sensor ring ──
        self._sensor_ring.center = (dx, dy)
        self._sensor_ring.set_radius(sensor_r)

        # ── Threat ring (larger circle around drone) ──
        self._threat_ring.center = (dx, dy)
        self._threat_ring.set_radius(sensor_r * 1.5)

        # ── Drone ──
        self._drone_sc.set_offsets([[dx, dy]])
        # Heading arrow
        heading = getattr(drone, "heading", 0)
        arr_len = 3
        self._drone_arrow.set_position((dx, dy))
        self._drone_arrow.xy = (dx + arr_len * math.cos(heading), dy + arr_len * math.sin(heading))

        # ── Target ──
        self._target_sc.set_offsets([[tx, ty]])

        # ── Weather effects ──
        if hasattr(world, "weather"):
            self._update_weather_effects(world)

    def _update_military_zones(self, world):
        zones = getattr(world, "military_zones", [])
        # Remove old patches
        for p in self._zone_patches:
            try:
                p.remove()
            except Exception:
                pass
        self._zone_patches.clear()

        color_map = {
            "landing": (LZ_COL, 0.12),
            "restricted": (RESTRICTED_COL, 0.08),
            "mission": (MISSION_COL, 0.06),
            "radar": (RADAR_COL, 0.04),
        }
        for zone in zones:
            col, alpha = color_map.get(zone.zone_type, (TEXT_DIM, 0.05))
            patch = mpatches.Circle(
                (zone.x, zone.y), zone.radius,
                facecolor=col, alpha=alpha,
                edgecolor=col, linewidth=0.8,
                linestyle="--" if zone.zone_type == "restricted" else "-",
                zorder=1,
            )
            self._ax_world.add_patch(patch)
            self._zone_patches.append(patch)
            # Zone label
            name = zone.metadata.get("name", zone.zone_type.upper())
            txt = self._ax_world.text(
                zone.x, zone.y + zone.radius + 1, name,
                fontsize=5, color=col, ha="center", va="bottom",
                fontweight="bold", alpha=0.8, zorder=13,
            )
            self._zone_patches.append(txt)

    def _update_weather_effects(self, world):
        weather = world.weather

        # ── Rain/Snow particles ──
        precip = weather.precipitation
        if precip.particle_positions:
            pts = np.asarray(precip.particle_positions)
            if weather.weather_type.name in ("RAIN", "HEAVY_RAIN", "STORM"):
                self._rain_sc.set_offsets(pts)
                self._rain_sc.set_color(RAIN_COL)
                self._rain_sc.set_alpha(0.25)
                self._rain_sc.set_sizes([2] * len(pts))
            elif weather.weather_type.name == "SNOW":
                self._rain_sc.set_offsets(pts)
                self._rain_sc.set_color(SNOW_COL)
                self._rain_sc.set_alpha(0.5)
                self._rain_sc.set_sizes([4] * len(pts))
            else:
                self._rain_sc.set_offsets(np.empty((0, 2)))
        else:
            self._rain_sc.set_offsets(np.empty((0, 2)))

        # ── Fog overlay ──
        if weather.atmosphere.fog_density > 0.1:
            import matplotlib.colors as mcolors
            fog_rgba = mcolors.to_rgba(FOG_COL, alpha=_clamp(weather.atmosphere.fog_density * 0.3, 0.0, 1.0))
            self._ax_world.set_facecolor(fog_rgba)
        else:
            self._ax_world.set_facecolor(BG_INNER)

        # ── Cloud shadows ──
        for cp in self._cloud_patches:
            try:
                cp.remove()
            except Exception:
                pass
        self._cloud_patches.clear()
        for cloud in weather.cloud_positions[:10]:
            c = mpatches.Ellipse(
                (cloud[0], cloud[1]), cloud[2] * 3, cloud[2] * 1.5,
                facecolor=CLOUD_COL, alpha=cloud[3] * 0.15,
                edgecolor="none", zorder=1,
            )
            self._ax_world.add_patch(c)
            self._cloud_patches.append(c)

        # ── Wind arrows (grid) ──
        for a in self._wind_arrows:
            try:
                a.remove()
            except Exception:
                pass
        self._wind_arrows.clear()
        wind = weather.wind.base_wind
        if wind.speed > 1.0:
            step = max(10, weather.width // 8)
            for gy in range(step, weather.height, step):
                for gx in range(step, weather.width, step):
                    w = weather.wind.get_wind_at(gx, gy)
                    if w.speed > 0.5:
                        arr = FancyArrowPatch(
                            (gx, gy),
                            (gx + w.dx * 1.5, gy + w.dy * 1.5),
                            arrowstyle="->", color=WIND_COL,
                            linewidth=0.6, alpha=min(0.5, w.speed / 10),
                            mutation_scale=6,
                        )
                        self._ax_world.add_patch(arr)
                        self._wind_arrows.append(arr)

        # ── Particle effects ──
        particles = weather.particles
        if particles:
            px = np.array([p.x for p in particles])
            py = np.array([p.y for p in particles])
            self._particle_sc.set_offsets(np.column_stack([px, py]))
            colors = [(p.color[0], p.color[1], p.color[2], p.alpha) for p in particles]
            self._particle_sc.set_facecolors(colors)
            self._particle_sc.set_sizes([p.size * 3 for p in particles])
        else:
            self._particle_sc.set_offsets(np.empty((0, 2)))

    # ── Sidebar ──

    def _update_sidebar(self, world, drone, target, path, beh, mis, plan, emerg,
                        bat, mem_d, act_c, exp_p, dx, dy, tx, ty):
        dist = math.hypot(tx - dx, ty - dy)
        pl = len(path) if path else 0
        sc = len(getattr(world, "obstacles", set()))
        dc = len(getattr(world, "dynamic_obstacles", []))
        ed = len(getattr(world, "enemy_drones", []))
        cv = sum(len(c.positions) for c in getattr(world, "convoys", []))

        bat_t = f"{bat:.1f}%" if bat is not None else "--"
        bat_c = _pct_color(bat) if bat is not None else TEXT
        em_s = str(emerg or "NORMAL")
        em_c = DANGER if "CRITICAL" in em_s else (WARNING if em_s != "NORMAL" else SUCCESS)

        risk_v = np.mean(self._hist_risk[-10:]) if self._hist_risk else 0

        # Terrain type
        terrain_str = "--"
        if hasattr(world, "terrain"):
            tt = world.terrain.get_terrain_type(int(dx), int(dy))
            terrain_str = tt.name[:10]

        # Weather
        weather_str = "--"
        tod_str = "--"
        wind_str = "--"
        if hasattr(world, "weather"):
            weather_str = world.weather.get_weather_display()[:10]
            tod_str = world.weather.atmosphere.time_of_day.name[:8]
            ws = world.weather.wind.base_wind.speed
            wind_str = f"{ws:.1f} m/s {world.weather.get_wind_display()}"

        vals = [
            str(mis or "--"),
            str(plan or "--"),
            (bat_t, bat_c),
            (f"({dx:.1f}, {dy:.1f})", TEXT),
            (f"({tx:.0f}, {ty:.0f})", TARGET_COL),
            (f"{dist:.1f}m", SUCCESS if dist < 30 else (WARNING if dist < 60 else DANGER)),
            (f"{pl}", TEXT),
            (f"{exp_p:.1f}%", ACCENT),
            (f"{sc}", TEXT),
            (f"{dc}", DYNAMIC_COL if dc > 0 else TEXT),
            (f"{ed}", ENEMY_COL if ed > 0 else TEXT),
            (f"{cv}", CONVOY_COL if cv > 0 else TEXT),
            (em_s[:10], em_c),
            (f"{mem_d:.1f}%" if mem_d is not None else "--", ACCENT),
            (f"{risk_v:.2f}", WARNING if risk_v > 0.5 else SUCCESS),
            (wind_str, WIND_COL),
            (terrain_str, TEXT),
            (weather_str, ACCENT2),
            (tod_str, WARNING),
        ]

        for i, v in enumerate(vals):
            if i < len(self._side_texts):
                _, vt = self._side_texts[i]
                if isinstance(v, tuple):
                    vt.set_text(v[0])
                    vt.set_color(v[1])
                else:
                    vt.set_text(str(v))

    # ── Heatmaps ──

    def _update_heatmaps(self, world, perception, memory, context, cognitive):
        ww = getattr(world, "width", 100)
        wh = getattr(world, "height", 100)
        empty = np.zeros((wh, ww), dtype=float)

        for img, data, ax in zip(
            self._hm_imgs,
            [perception, memory, context, cognitive],
            self._heat_axes,
        ):
            g = _safe_grid(data, empty)
            img.set_data(g)
            img.set_extent([-0.5, ww - 0.5, -0.5, wh - 0.5])
            ax.set_xlim(-0.5, ww - 0.5)
            ax.set_ylim(-0.5, wh - 0.5)

    # ── Metrics ──

    def _update_metrics(self, world, drone, target, bat, exp_p, mem_d):
        dyn = len(getattr(world, "dynamic_obstacles", []))
        obs = len(getattr(world, "obstacles", set()))
        risk = _clamp((dyn + obs) / 80.0, 0, 1)
        mem = (mem_d / 100.0) if mem_d is not None else 0.0
        cog = (exp_p / 100.0) if exp_p else 0.0
        bat_n = (bat / 100.0) if bat is not None else 1.0

        dx = getattr(drone, "x", 0)
        dy = getattr(drone, "y", 0)
        tx = target[0] if target else 0
        ty = target[1] if target else 1
        dist = math.hypot(tx - dx, ty - dy)
        max_d = math.hypot(getattr(world, "width", 100), getattr(world, "height", 100))
        att = 1.0 - _clamp(dist / max_d, 0, 1)

        speed = 0.0
        if len(self.trail) >= 2:
            p1, p2 = self.trail[-2], self.trail[-1]
            speed = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        speed_n = _clamp(speed / 3.0, 0, 1)

        self._hist_risk.append(risk)
        self._hist_mem.append(mem)
        self._hist_att.append(att)
        self._hist_cog.append(cog)
        self._hist_bat.append(bat_n)
        self._hist_speed.append(speed_n)

        for h in [self._hist_risk, self._hist_mem, self._hist_att,
                  self._hist_cog, self._hist_bat, self._hist_speed]:
            if len(h) > MAX_HIST:
                del h[:len(h) - MAX_HIST]

        n = len(self._hist_risk)
        x = np.arange(n)
        for ln, h in zip(self._metric_lines, [self._hist_risk, self._hist_mem,
                                               self._hist_att, self._hist_cog,
                                               self._hist_bat, self._hist_speed]):
            ln.set_data(x, h)
        self._ax_metrics.set_xlim(max(0, n - MAX_HIST), max(MAX_HIST, n))

    # ── Blit ──

    def _blit(self):
        if not self._init_done:
            return
        if self._bg_cache is not None:
            try:
                self.fig.canvas.restore_region(self._bg_cache)
                for ax in self._all_axes:
                    self.fig.canvas.blit(ax.bbox)
                for cb in self._hm_cbs:
                    self.fig.canvas.blit(cb.ax.bbox)
            except Exception:
                self.fig.canvas.draw_idle()
        else:
            self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()
        if "agg" not in plt.get_backend().lower():
            plt.pause(0.0001)

    def render_frame(self):
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()


# ══════════════════════════════════════════════════════════════════════════════
# Module-level draw() — Drop-in replacement
# ══════════════════════════════════════════════════════════════════════════════


def draw(
    world, drone, target,
    path=None, occupancy_grid=None, sensor_radius=8,
    perception_map=None, risk_map=None, memory_map=None,
    behavior_state=None, mission_state=None, planner_name=None,
    emergency_state=None, battery_percentage=None,
    memory_density=None, active_cells=None,
    context_map=None, cognitive_map=None, explored_percent=None,
) -> None:
    """Drop-in replacement for the old draw() function.

    Creates or reuses MilitaryDashboard singleton.
    Fully backward-compatible with all existing callers.
    """
    global _mil_dashboard
    if _mil_dashboard is None or not plt.fignum_exists(_mil_dashboard.fig.number):
        _mil_dashboard = MilitaryDashboard()

    _mil_dashboard.update(
        world=world, drone=drone, target=target,
        path=path, occupancy_grid=occupancy_grid,
        sensor_radius=sensor_radius,
        perception_map=perception_map, risk_map=risk_map,
        memory_map=memory_map, context_map=context_map,
        cognitive_map=cognitive_map,
        behavior_state=behavior_state, mission_state=mission_state,
        planner_name=planner_name, emergency_state=emergency_state,
        battery_percentage=battery_percentage,
        memory_density=memory_density, active_cells=active_cells,
        explored_percent=explored_percent or 0.0,
    )


def reset_dashboard() -> None:
    """Reset dashboard singleton."""
    global _mil_dashboard
    if _mil_dashboard is not None:
        try:
            plt.close(_mil_dashboard.fig)
        except Exception:
            pass
        _mil_dashboard = None


# Avoid name collision
DANGER_COLOR_STR = DANGER