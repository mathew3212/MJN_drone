"""
Premium Dashboard v4 — Airspace Intelligence Command Center
============================================================
24x24 GridSpec — Zero overlapping — Airspace zones rendered live.
All static obstacles removed — Replaced by dynamic airspace visualization.
"""

from __future__ import annotations

import math
import time
from typing import Optional, List, Tuple, Any

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import (
    FancyBboxPatch, Circle, FancyArrowPatch, Rectangle, Arc, Wedge,
)

from .camera_system import CameraSystem, CameraMode
from .vision_engine import VisionEngine

_premium_dashboard: Optional["PremiumDashboard"] = None


class PColor:
    BG_DARK = "#05070B"
    BG_PANEL = "#0B0E14"
    BG_INNER = "#11151F"
    BG_GLASS = "#11151F"
    BG_CARD = "#0D1019"
    BORDER = "#1A2035"
    BORDER_GLOW = "#00D4FF"
    BORDER_ACTIVE = "#0A1A2A"
    PRIMARY = "#00D4FF"
    SECONDARY = "#9D6CFF"
    SUCCESS = "#00FF88"
    WARNING = "#FFC857"
    DANGER = "#FF4D5A"
    INFO = "#06B6D4"
    PURPLE = "#9D6CFF"
    DRONE = "#FF8800"
    DRONE_GLOW = "#FF5500"
    TARGET = "#00FF88"
    PATH = "#00D4FF"
    PATH_GLOW = "#0088CC"
    TRAIL = "#FF6633"
    SENSOR = "#3366FF"
    LANDING = "#00CC66"
    TEXT_MAIN = "#FFFFFF"
    TEXT_BRIGHT = "#F0F4FF"
    TEXT_VALUE = "#E8EDFF"
    TEXT_SECTION = "#A0B0D0"
    TEXT_LABEL = "#6B7FA0"
    TEXT = "#E2E8F0"
    TEXT_ACCENT = "#00D4FF"
    TEXT_DIM = "#4A5A78"
    TEXT_MUTED = "#2A3A55"
    LINE_RISK = "#FF4D5A"
    LINE_MEMORY = "#FFC857"
    LINE_ATTENTION = "#00D4FF"
    LINE_COGNITIVE = "#00FF88"
    LINE_BATTERY = "#9D6CFF"
    LINE_SPEED = "#FF8800"
    LINE_CONFIDENCE = "#00FF88"
    LINE_AIRSPACE_RISK = "#FF6600"
    STATUS_OK = "#00FF88"
    STATUS_WARN = "#FFC857"
    STATUS_ERR = "#FF4D5A"
    STATUS_OFF = "#2A3A55"
    CARD_HEADER = "#141A2A"
    CARD_BODY = "#0D1119"

    # Airspace zone colors (matching airspace_visualization.py)
    ZONE_SAFE = "#00FF00"
    ZONE_CAUTION = "#FFFF00"
    ZONE_RESTRICTED = "#FF6600"
    ZONE_PROHIBITED = "#FF0000"
    ZONE_TEMPORARY = "#800080"
    ZONE_CORRIDOR = "#0066FF"
    ZONE_EMERGENCY = "#FF4500"
    ZONE_SENSITIVE = "#FFD700"
    ZONE_ENVIRONMENTAL = "#228B22"

MAX_TRAIL = 500
FPS_SMOOTH = 0.1
MAX_HISTORY = 300


class PremiumDashboard:
    """World-class autonomous drone command center — Premium v4 with Airspace."""

    def __init__(self, world_width=100, world_height=100, use_theme="dark"):
        plt.ion()
        self.fig = plt.figure(
            figsize=(24.0, 13.5),
            num="MJN DRONE - Airspace Intelligence Center",
            facecolor=PColor.BG_DARK, dpi=110,
        )
        self.world_width = world_width
        self.world_height = world_height
        self.theme = use_theme
        self.camera = CameraSystem()
        self.vision = VisionEngine()
        self.camera.set_viewport(world_width, world_height)
        self._setup_layout()
        self.trail = []
        self._fps = 60.0
        self._last_t = time.perf_counter()
        self._frame_count = 0
        self._init_done = False
        self._bg_cache = None
        self._actual_dt = 0.016
        self._h_risk = []
        self._h_mem = []
        self._h_att = []
        self._h_cog = []
        self._h_bat = []
        self._h_spd = []
        self._h_asp = []  # airspace risk history
        self.mission_progress = 0.0
        self.mission_eta = "--:--"
        self.mission_start_time = time.time()

        # Airspace visualization data
        self._airspace_zones_data = []
        self._airspace_risk_score = 0.0
        self._airspace_violations = 0
        self._airspace_active_tfrs = 0
        self._current_decision = "PROCEED"
        self._current_decision_color = PColor.SUCCESS
        self._airspace_legend_items = []

        self._create_artists()
        self.fig.canvas.draw()
        self._bg_cache = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        self._init_done = True
        self.vision.daynight_speed = 0.004

    def _setup_layout(self):
        """24x24 GridSpec — No overlapping — Full coverage."""
        gs = GridSpec(24, 24, figure=self.fig, left=0.002, right=0.998,
                       top=0.985, bottom=0.002, hspace=0.25, wspace=0.25)

        # Viewport: largest area (rows 0-11, cols 0-15) — 12x16
        self._ax_viewport = self.fig.add_subplot(gs[0:12, 0:16])

        # Legend: compact strip (row 12, cols 0-15) — 1x16
        self._ax_legend = self.fig.add_subplot(gs[12:13, 0:16])

        # Telemetry panels (rows 0-4, cols 16-24) — 5x8 top-right
        self._ax_telem1 = self.fig.add_subplot(gs[0:2, 16:24])
        self._ax_telem2 = self.fig.add_subplot(gs[2:4, 16:24])

        # Airspace & altimeter (rows 4-8, cols 16-24) — 4x8
        self._ax_airspace = self.fig.add_subplot(gs[4:7, 16:24])
        self._ax_altimeter = self.fig.add_subplot(gs[7:9, 16:24])

        # Metrics graph (rows 13-24, cols 0-14) — 11x15 bottom-left
        self._ax_metrics = self.fig.add_subplot(gs[13:24, 0:15])

        # Drone Brain cognitive (rows 9-24, cols 15-24) — 15x10 right column
        self._ax_cognitive = self.fig.add_subplot(gs[9:24, 15:24])

        self._all_axes = [
            self._ax_viewport, self._ax_legend,
            self._ax_telem1, self._ax_telem2,
            self._ax_airspace, self._ax_altimeter,
            self._ax_metrics, self._ax_cognitive,
        ]
        self._style_axes()

    def _style_axes(self):
        self._ax_viewport.set_facecolor(PColor.BG_DARK)
        self._ax_viewport.set_aspect("equal", adjustable="box")
        self._ax_viewport.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False)
        for s in self._ax_viewport.spines.values():
            s.set_color(PColor.BORDER); s.set_linewidth(0.4)

        self._ax_legend.set_facecolor(PColor.BG_PANEL)
        self._ax_legend.axis("off")
        for s in self._ax_legend.spines.values():
            s.set_color(PColor.BORDER); s.set_linewidth(0.3)

        for ax in [self._ax_telem1, self._ax_telem2]:
            ax.set_facecolor(PColor.BG_PANEL)
            ax.axis("off")
            ax.add_patch(FancyBboxPatch((0.03, 0.04), 0.94, 0.93,
                boxstyle=mpatches.BoxStyle("Round", pad=0.03),
                facecolor=PColor.BG_CARD, edgecolor=PColor.BORDER, linewidth=0.5,
                transform=ax.transAxes, zorder=0))

        self._ax_airspace.set_facecolor(PColor.BG_PANEL)
        self._ax_airspace.axis("off")
        self._ax_airspace.add_patch(FancyBboxPatch((0.03, 0.04), 0.94, 0.93,
            boxstyle=mpatches.BoxStyle("Round", pad=0.03),
            facecolor=PColor.BG_CARD, edgecolor=PColor.BORDER, linewidth=0.5,
            transform=self._ax_airspace.transAxes, zorder=0))

        self._ax_altimeter.set_facecolor(PColor.BG_PANEL)
        self._ax_altimeter.axis("off")
        self._ax_altimeter.add_patch(FancyBboxPatch((0.03, 0.04), 0.94, 0.93,
            boxstyle=mpatches.BoxStyle("Round", pad=0.03),
            facecolor=PColor.BG_CARD, edgecolor=PColor.BORDER, linewidth=0.5,
            transform=self._ax_altimeter.transAxes, zorder=0))

        self._ax_metrics.set_facecolor(PColor.BG_PANEL)
        self._ax_metrics.set_ylim(-0.05, 1.05)
        self._ax_metrics.set_xlim(0, MAX_HISTORY)
        self._ax_metrics.tick_params(colors=PColor.TEXT_DIM, labelsize=5.5)
        self._ax_metrics.grid(True, color=PColor.BORDER, linewidth=0.3, alpha=0.3)
        for s in self._ax_metrics.spines.values():
            s.set_color(PColor.BORDER); s.set_linewidth(0.3)
        self._ax_metrics.locator_params(axis='y', nbins=4)

        self._ax_cognitive.set_facecolor(PColor.BG_PANEL)
        self._ax_cognitive.axis("off")

    def _create_artists(self):
        self._create_viewport()
        self._create_legend()
        self._create_telem1()
        self._create_telem2()
        self._create_airspace_panel()
        self._create_altimeter()
        self._create_metrics()
        self._create_cognitive()

    def _create_viewport(self):
        ax = self._ax_viewport
        # Terrain background
        self._v_terrain = ax.imshow(np.zeros((10, 10, 3)), origin="lower",
            interpolation="bilinear", aspect="equal", alpha=0.9, zorder=0)
        self._v_topo = ax.imshow(np.zeros((10, 10)), origin="lower",
            interpolation="bilinear", aspect="equal", cmap="terrain", alpha=0.12, zorder=1)

        # World features (buildings, trees, pads, vehicles, pedestrians, birds)
        self._v_buildings = ax.scatter([], [], marker="s", s=25, c="#4A5568",
            edgecolors="#4A4A4A", linewidths=0.3, alpha=0.8, zorder=2)
        self._v_trees = ax.scatter([], [], marker="^", s=8, c="#1A4730", alpha=0.6, linewidths=0, zorder=2)
        self._v_pads = ax.scatter([], [], marker="H", s=80, c=PColor.LANDING,
            edgecolors="#14532D", linewidths=0.8, zorder=3)
        self._v_vehicles = ax.scatter([], [], marker="s", s=20, c=PColor.PRIMARY,
            edgecolors="#1E3A5F", linewidths=0.3, zorder=4)
        self._v_pedestrians = ax.scatter([], [], marker="o", s=6, c=PColor.WARNING, alpha=0.7, linewidths=0, zorder=4)
        self._v_birds = ax.scatter([], [], marker="v", s=10, c=PColor.TEXT_DIM, alpha=0.5, linewidths=0, zorder=3)

        # Airspace restricted zones — rendered as filled polygons
        self._v_airspace_patches: List[Any] = []

        # Flight path and trail
        self._v_path = ax.plot([], [], "-", linewidth=2, color=PColor.PATH, alpha=0.8, zorder=5)[0]
        self._v_path_glow = ax.plot([], [], "-", linewidth=5, color=PColor.PATH_GLOW, alpha=0.2, zorder=4)[0]
        self._v_trail = ax.plot([], [], "-", linewidth=1.5, color=PColor.TRAIL, alpha=0.6, zorder=5)[0]
        self._v_predicted = ax.plot([], [], ":", linewidth=1, color=PColor.PATH, alpha=0.3, zorder=4)[0]

        # Sensor range
        self._v_sensor = Circle((0, 0), 5, fill=False, linestyle="--", linewidth=0.8,
                                color=PColor.SENSOR, alpha=0.4, zorder=3)
        ax.add_patch(self._v_sensor)
        self._v_sensor_fill = Circle((0, 0), 5, fill=True, facecolor=PColor.SENSOR,
                                     alpha=0.04, edgecolor="none", zorder=2)
        ax.add_patch(self._v_sensor_fill)

        # Drone
        self._v_drone = Circle((0, 0), 1.0, fill=True, facecolor=PColor.DRONE,
            edgecolor=PColor.DRONE_GLOW, linewidth=1.5, alpha=0.95, zorder=10)
        ax.add_patch(self._v_drone)
        self._v_drone_glow = Circle((0, 0), 2.0, fill=True, facecolor=PColor.DRONE,
                                    alpha=0.12, edgecolor="none", zorder=9)
        ax.add_patch(self._v_drone_glow)
        self._v_heading = ax.plot([], [], "-", linewidth=2, color=PColor.DRONE_GLOW, alpha=0.9, zorder=11)[0]

        # Target
        self._v_target = ax.plot([], [], "+", markersize=14, markeredgewidth=2, color=PColor.TARGET, alpha=0.9, zorder=9)[0]
        self._v_target_glow = Circle((0, 0), 1.5, fill=True, facecolor=PColor.TARGET,
                                     alpha=0.2, edgecolor="none", zorder=8)
        ax.add_patch(self._v_target_glow)

        # Overlays
        self._v_cam = ax.text(0.01, 0.97, "CHASE", transform=ax.transAxes, fontsize=7,
            fontweight="bold", color=PColor.TEXT_BRIGHT, va="top", family="monospace",
            bbox=dict(boxstyle="round,pad=0.15", facecolor=PColor.BG_GLASS,
                      edgecolor=PColor.BORDER_GLOW, linewidth=0.8))
        self._v_fps = ax.text(0.01, 0.01, "60 FPS", transform=ax.transAxes, fontsize=7,
            fontweight="bold", color=PColor.TEXT_ACCENT, ha="left", va="bottom", family="monospace")
        self._v_coords = ax.text(0.99, 0.01, "(0,0)", transform=ax.transAxes, fontsize=5.5,
            color=PColor.TEXT_DIM, ha="right", va="bottom", family="monospace")
        self._v_airspace_status = ax.text(0.99, 0.97, "AIRSPACE: CLEAR", transform=ax.transAxes,
            fontsize=6, fontweight="bold", color=PColor.SUCCESS, ha="right", va="top",
            family="monospace", bbox=dict(boxstyle="round,pad=0.12", facecolor=PColor.BG_GLASS,
                                          edgecolor=PColor.ZONE_SAFE, linewidth=0.6))

    def _create_legend(self):
        ax = self._ax_legend
        # CORE legend
        core_items = [
            ("Drone", "o", PColor.DRONE),
            ("Target", "+", PColor.TARGET),
            ("Path", "-", PColor.PATH),
            ("Trail", "-", PColor.TRAIL),
            ("Building", "s", "#4A5568"),
            ("Tree", "^", "#1A4730"),
            ("Vehicle", "s", PColor.PRIMARY),
            ("Pedestrian", "o", PColor.WARNING),
            ("Pad", "H", PColor.LANDING),
        ]
        # AIRSPACE legend
        airspace_items = [
            ("Safe", "s", PColor.ZONE_SAFE),
            ("Caution", "s", PColor.ZONE_CAUTION),
            ("Restricted", "s", PColor.ZONE_RESTRICTED),
            ("Prohibited", "s", PColor.ZONE_PROHIBITED),
            ("TFR", "s", PColor.ZONE_TEMPORARY),
            ("Corridor", "s", PColor.ZONE_CORRIDOR),
            ("Emergency", "s", PColor.ZONE_EMERGENCY),
            ("Sensitive", "s", PColor.ZONE_SENSITIVE),
            ("Park", "s", PColor.ZONE_ENVIRONMENTAL),
        ]
        h = []
        for label, marker, color in core_items:
            if marker == "-":
                h.append(Line2D([0], [0], color=color, linewidth=2, label=label))
            else:
                h.append(Line2D([0], [0], marker=marker, color="w",
                                markerfacecolor=color, markersize=5, label=label, linestyle="None"))

        # Add airspace legend handles
        for label, marker, color in airspace_items:
            h.append(Line2D([0], [0], marker="s", color="w",
                            markerfacecolor=color, markersize=6, label=label, linestyle="None",
                            markeredgecolor=PColor.BORDER, markeredgewidth=0.5))

        leg = ax.legend(handles=h, loc="center", fontsize=5, ncol=9,
                        frameon=True, framealpha=0.90,
                        facecolor=PColor.BG_INNER, edgecolor=PColor.BORDER,
                        labelcolor=PColor.TEXT_SECTION,
                        columnspacing=1.2, handletextpad=0.4, borderpad=0.3)
        leg.get_frame().set_linewidth(0.3)

    def _create_telem1(self):
        ax = self._ax_telem1
        ax.text(0.06, 0.82, "FLIGHT DATA", fontsize=7, fontweight="bold",
                color=PColor.PRIMARY, transform=ax.transAxes, va="top", family="sans-serif")
        ax.plot([0.06, 0.94], [0.74, 0.74], transform=ax.transAxes, color=PColor.BORDER, linewidth=0.4)
        self._t1_l = []; self._t1_r = []
        left_labels = ["SPEED", "HEADING", "ALTITUDE", "VERT SPD"]
        right_labels = ["DIST TARGET", "FLIGHT TIME", "SIGNAL", "MODE"]
        for i in range(4):
            y_lbl = 0.68 - i * 0.160
            y_val = y_lbl - 0.045
            ax.text(0.06, y_lbl, left_labels[i], fontsize=4.5, color=PColor.TEXT_LABEL,
                    transform=ax.transAxes, va="top", family="sans-serif")
            v = ax.text(0.06, y_val, "--", fontsize=6.5, fontweight="bold",
                        color=PColor.TEXT_VALUE, transform=ax.transAxes, va="top", family="monospace")
            self._t1_l.append(v)
            ax.text(0.50, y_lbl, right_labels[i], fontsize=4.5, color=PColor.TEXT_LABEL,
                    transform=ax.transAxes, va="top", family="sans-serif")
            v = ax.text(0.50, y_val, "--", fontsize=6.5, fontweight="bold",
                        color=PColor.TEXT_VALUE, transform=ax.transAxes, va="top", family="monospace")
            self._t1_r.append(v)

    def _create_telem2(self):
        ax = self._ax_telem2
        ax.text(0.06, 0.80, "BATTERY & MISSION", fontsize=7, fontweight="bold",
                color=PColor.SUCCESS, transform=ax.transAxes, va="top", family="sans-serif")
        ax.plot([0.06, 0.94], [0.72, 0.72], transform=ax.transAxes, color=PColor.BORDER, linewidth=0.4)

        # Battery bar
        bg = FancyBboxPatch((0.12, 0.30), 0.76, 0.28,
            boxstyle=mpatches.BoxStyle("Round", pad=0.03),
            facecolor=PColor.BG_INNER, edgecolor=PColor.BORDER, linewidth=0.6, transform=ax.transAxes)
        ax.add_patch(bg)
        self._bat_fill = FancyBboxPatch((0.14, 0.33), 0.56, 0.22,
            boxstyle=mpatches.BoxStyle("Round", pad=0.02),
            facecolor=PColor.SUCCESS, edgecolor="none", transform=ax.transAxes, alpha=0.8)
        ax.add_patch(self._bat_fill)
        self._bat_pct = ax.text(0.50, 0.44, "100%", fontsize=11, fontweight="bold",
                                color=PColor.TEXT_MAIN, transform=ax.transAxes, ha="center", va="center", family="monospace")
        self._bat_em = ax.text(0.50, 0.72, "EMERGENCY: NORMAL", fontsize=4.5, color=PColor.SUCCESS,
                               transform=ax.transAxes, ha="center", va="center", family="monospace")
        self._bat_st = ax.text(0.50, 0.10, "SYSTEM NOMINAL", fontsize=5.5, fontweight="bold",
                               color=PColor.SUCCESS, transform=ax.transAxes, ha="center", va="center", family="monospace")

    def _create_airspace_panel(self):
        ax = self._ax_airspace
        ax.text(0.06, 0.88, "AIRSPACE INTELLIGENCE", fontsize=6.5, fontweight="bold",
                color=PColor.ZONE_RESTRICTED, transform=ax.transAxes, va="top", family="sans-serif")
        ax.plot([0.06, 0.94], [0.82, 0.82], transform=ax.transAxes, color=PColor.BORDER, linewidth=0.4)

        self._as_labels = []
        airspace_items = [
            ("ZONES ACTIVE", "--", PColor.ZONE_RESTRICTED),
            ("VIOLATIONS", "--", PColor.DANGER),
            ("TFR ACTIVE", "--", PColor.ZONE_TEMPORARY),
            ("RISK SCORE", "--", PColor.WARNING),
        ]
        for i, (lbl, _, clr) in enumerate(airspace_items):
            y = 0.76 - i * 0.150
            ax.text(0.06, y, lbl, fontsize=4.5, color=PColor.TEXT_LABEL,
                    transform=ax.transAxes, va="top", family="sans-serif")
            v = ax.text(0.55, y, "--", fontsize=6.5, fontweight="bold",
                        color=clr, transform=ax.transAxes, va="top", family="monospace")
            self._as_labels.append(v)

        # Decision banner
        bg_dec = FancyBboxPatch((0.06, 0.02), 0.88, 0.12,
            boxstyle=mpatches.BoxStyle("Round", pad=0.02),
            facecolor=PColor.BG_INNER, edgecolor=PColor.BORDER, linewidth=0.5, transform=ax.transAxes)
        ax.add_patch(bg_dec)
        self._as_decision = ax.text(0.50, 0.08, "DECISION: PROCEED", fontsize=5.5, fontweight="bold",
                                    color=PColor.SUCCESS, transform=ax.transAxes, ha="center", va="center",
                                    family="monospace")

    def _create_altimeter(self):
        ax = self._ax_altimeter
        ax.text(0.06, 0.80, "ALTITUDE LAYERS", fontsize=6, fontweight="bold",
                color=PColor.INFO, transform=ax.transAxes, va="top", family="sans-serif")
        ax.plot([0.06, 0.94], [0.72, 0.72], transform=ax.transAxes, color=PColor.BORDER, linewidth=0.4)

        self._alt_layers = []
        alt_data = [("GROUND", "0-5m"), ("LOW", "5-30m"), ("CRUISE", "30-100m"),
                     ("HIGH", "100-150m"), ("MAX", "150-200m")]
        for i, (nm, rng) in enumerate(alt_data):
            y = 0.66 - i * 0.120
            clr = [PColor.WARNING, PColor.WARNING, PColor.SUCCESS, PColor.PRIMARY, PColor.DANGER][i]
            ax.text(0.06, y, nm, fontsize=4.5, color=clr,
                    transform=ax.transAxes, va="top", family="monospace")
            v = ax.text(0.45, y, rng, fontsize=4.5, fontweight="bold", color=PColor.TEXT_DIM,
                        transform=ax.transAxes, va="top", family="monospace")
            self._alt_layers.append(v)
        self._alt_current = ax.text(0.06, 0.02, "CURRENT ALT: 0m", fontsize=5, fontweight="bold",
                                    color=PColor.TEXT_VALUE, transform=ax.transAxes, va="bottom", family="monospace")

    def _create_metrics(self):
        ax = self._ax_metrics
        ax.text(0.01, 0.94, "LIVE PERFORMANCE METRICS", fontsize=7, fontweight="bold",
                color=PColor.TEXT_ACCENT, transform=ax.transAxes, va="top", family="sans-serif")
        # 7 metrics now including Airspace Risk
        cols = [PColor.LINE_RISK, PColor.LINE_MEMORY, PColor.LINE_ATTENTION,
                PColor.LINE_COGNITIVE, PColor.LINE_BATTERY, PColor.LINE_SPEED,
                PColor.LINE_AIRSPACE_RISK]
        nms = ["Risk", "Memory", "Attention", "Cognitive", "Battery", "Speed", "Airspace"]
        self._m_lines = []
        for c, n in zip(cols, nms):
            ln = ax.plot([], [], color=c, linewidth=1.5, label=n, alpha=0.85)[0]
            self._m_lines.append(ln)
        leg = ax.legend(loc="upper right", fontsize=4.8, frameon=True, framealpha=0.85,
                        facecolor=PColor.BG_INNER, edgecolor=PColor.BORDER, labelcolor=PColor.TEXT, ncol=4)
        for t in leg.get_texts(): t.set_fontsize(4.8)
        ax.set_xlabel("Frame", color=PColor.TEXT_DIM, fontsize=5)
        ax.set_ylabel("Normalised", color=PColor.TEXT_DIM, fontsize=5)

    def _create_cognitive(self):
        ax = self._ax_cognitive
        ax.add_patch(FancyBboxPatch((0.02, 0.97), 0.96, 0.03,
            boxstyle=mpatches.BoxStyle("Round", pad=0.01),
            facecolor=PColor.CARD_HEADER, edgecolor="none", linewidth=0, transform=ax.transAxes, zorder=1))
        ax.text(0.50, 0.985, "DRONE BRAIN - LIVE", fontsize=7, fontweight="bold",
                color=PColor.DRONE, transform=ax.transAxes, ha="center", va="center", family="sans-serif")

        self._b_dec = ax.text(0.04, 0.950, "DECISION: PROCEED", fontsize=5, fontweight="bold",
                              color=PColor.SUCCESS, transform=ax.transAxes, va="top", family="monospace")
        self._b_mis = ax.text(0.52, 0.950, "MISSION: GO", fontsize=5, fontweight="bold",
                              color=PColor.INFO, transform=ax.transAxes, va="top", family="monospace")
        ax.plot([0.04, 0.96], [0.935, 0.935], color=PColor.BORDER, linewidth=0.4, transform=ax.transAxes)

        engines = [
            ("PERCEPTION", PColor.PRIMARY), ("BEHAVIOR", PColor.WARNING),
            ("MEMORY", PColor.LINE_MEMORY), ("EMERGENCY", PColor.DANGER),
            ("PLANNING", PColor.SUCCESS), ("RISK", PColor.DANGER),
            ("FUSION", PColor.INFO), ("MOTION", PColor.SUCCESS),
            ("GEOFENCE", PColor.ZONE_RESTRICTED), ("ALTITUDE", PColor.INFO),
        ]
        self._b_eng = []
        for i, (nm, clr) in enumerate(engines):
            col, row = i % 2, i // 2
            x = 0.04 + col * 0.46
            y = 0.920 - row * 0.090
            ax.text(x, y, nm, fontsize=4.2, fontweight="bold", color=PColor.TEXT_SECTION,
                    transform=ax.transAxes, va="top", family="sans-serif")
            d = ax.plot(x + 0.15, y - 0.012, "o", markersize=2.5, color=PColor.STATUS_OK, transform=ax.transAxes)[0]
            bg = FancyBboxPatch((x + 0.19, y - 0.024), 0.18, 0.016,
                boxstyle=mpatches.BoxStyle("Round", pad=0.003),
                facecolor=PColor.BG_INNER, edgecolor=PColor.BORDER, linewidth=0.3, transform=ax.transAxes)
            ax.add_patch(bg)
            fl = FancyBboxPatch((x + 0.195, y - 0.022), 0.10, 0.012,
                boxstyle=mpatches.BoxStyle("Round", pad=0.002),
                facecolor=clr, edgecolor="none", transform=ax.transAxes, alpha=0.8)
            ax.add_patch(fl)
            p = ax.text(x + 0.40, y - 0.012, "95%", fontsize=3.8, fontweight="bold",
                        color=PColor.TEXT_VALUE, transform=ax.transAxes, va="center", family="monospace")
            self._b_eng.append((nm, d, fl, p))

        # Explanations
        ax.plot([0.04, 0.96], [0.42, 0.42], color=PColor.BORDER, linewidth=0.4, transform=ax.transAxes)
        explanations = [
            ("DRONE BRAIN ENGINES:", True),
            ("GEOFENCE: Airspace zone monitoring & violation detection", False),
            ("ALTITUDE: Altitude layer adherence & optimization", False),
            ("All others: Standard drone cognitive stack", False),
        ]
        for i, (tx, hd) in enumerate(explanations):
            y = 0.400 - i * 0.035
            clr = PColor.DRONE if hd else PColor.TEXT_MUTED
            fw = "bold" if hd else "normal"
            fs = 4.5 if hd else 3.8
            ax.text(0.04, y, tx, fontsize=fs, fontweight=fw, color=clr,
                    transform=ax.transAxes, va="top", family="monospace")

    # ── Update methods ───────────────────────────────────────────

    def _update_fps(self):
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now
        if dt > 0:
            self._fps += FPS_SMOOTH * (1.0 / dt - self._fps)
        self._actual_dt = max(0.016, min(dt, 0.5))

    def update(self, world=None, drone=None, target=None, path=None, smooth_path=None,
               occupancy_grid=None, perception_map=None, risk_map=None, memory_map=None,
               context_map=None, cognitive_map=None, premium_world=None,
               behavior_state="--", mission_state="--", planner_name="--",
               emergency_state="NORMAL", battery_percentage=100.0,
               memory_density=0.0, active_cells=0, explored_percent=0.0,
               camera_mode=None, brain_log=None, drone_speed=None, drone_altitude=None,
               battery_drain_rate=None, visible_obstacles=None, weather_fx=None,
               # New: Airspace data
               airspace_manager=None, **kwargs):
        self._update_fps()
        self._frame_count += 1
        dt = self._actual_dt
        self.vision.update(dt)
        dx = float(getattr(drone, "x", 50.0)) if drone else 50.0
        dy = float(getattr(drone, "y", 50.0)) if drone else 50.0
        dh = float(getattr(drone, "heading", 0.0)) if drone else 0.0
        if camera_mode is not None:
            self.camera.set_mode(camera_mode, instant=False)
        self.camera.update(dx, dy, dh, dt)
        if target is not None:
            tx, ty = (float(target[0]), float(target[1])) if hasattr(target, '__getitem__') else (50.0, 50.0)
        else:
            tx, ty = 50.0, 50.0

        # Get airspace altitude if available
        altitude = drone_altitude or 50.0

        self._update_viewport(world, premium_world, dx, dy, tx, ty, dh,
                              smooth_path, path, airspace_manager, altitude)
        self._update_telem1(drone, dx, dy, tx, ty, dt)
        self._update_telem2(battery_percentage, emergency_state)
        self._update_airspace_panel(airspace_manager, dx, dy, altitude)
        self._update_altimeter(altitude)
        self._update_metrics_graph(battery_percentage, explored_percent, memory_density, airspace_manager)
        self._update_brain(brain_log, behavior_state, mission_state, emergency_state, visible_obstacles, airspace_manager)
        self._v_cam.set_text(self.camera.get_mode_name())
        self._v_fps.set_text(f"{self._fps:.0f} FPS  |  {self._frame_count}")
        self._v_coords.set_text(f"({dx:.0f},{dy:.0f})")
        self._blit()

    def _update_viewport(self, world, pw, dx, dy, tx, ty, heading,
                          smooth_path=None, path=None, airspace_manager=None, altitude=50.0):
        ax = self._ax_viewport
        ww = self.world_width; wh = self.world_height
        ax.set_xlim(-1, ww + 1); ax.set_ylim(-1, wh + 1)

        # ── Update terrain and world features ──
        if pw is not None:
            try:
                t = pw.get_terrain_array(); self._v_terrain.set_data(t)
                self._v_terrain.set_extent([-0.5, ww - 0.5, -0.5, wh - 0.5])
                e = pw.get_elevation_array(); self._v_topo.set_data(e)
                self._v_topo.set_extent([-0.5, ww - 0.5, -0.5, wh - 0.5])
            except: pass
            bld = [(b.x + b.width / 2, b.y + b.height / 2) for b in pw.buildings]
            self._v_buildings.set_offsets(np.array(bld) if bld else np.empty((0, 2)))
            sz = [max(5, b.width * b.height * 8) for b in pw.buildings] if bld else [20]
            self._v_buildings.set_sizes(sz)
            trees = sum([list(f.tree_positions) for f in pw.forests], [])
            self._v_trees.set_offsets(np.array(trees) if trees else np.empty((0, 2)))
            pads = [(p.x, p.y) for p in pw.landing_pads]
            self._v_pads.set_offsets(np.array(pads) if pads else np.empty((0, 2)))
            vehs = [(v.x, v.y) for v in pw.vehicles]
            self._v_vehicles.set_offsets(np.array(vehs) if vehs else np.empty((0, 2)))
            peds = [(p.x, p.y) for p in pw.pedestrians]
            self._v_pedestrians.set_offsets(np.array(peds) if peds else np.empty((0, 2)))
            brds = [(b.x, b.y) for b in pw.birds]
            self._v_birds.set_offsets(np.array(brds) if brds else np.empty((0, 2)))
        else:
            for s in [self._v_buildings, self._v_trees, self._v_pads,
                       self._v_vehicles, self._v_pedestrians, self._v_birds]:
                s.set_offsets(np.empty((0, 2)))

        # ── Remove old airspace zone patches ──
        for patch in self._v_airspace_patches:
            try:
                patch.remove()
            except:
                pass
        self._v_airspace_patches = []

        # ── Render airspace zones ──
        if airspace_manager is not None:
            zones = airspace_manager.geofence.get_active_zones()
            from src.airspace.airspace_visualization import AirspaceVisualization
            vis = AirspaceVisualization(ww, wh)
            rendered = vis.render_all_zones(zones)
            self._airspace_zones_data = rendered

            for zone_data in rendered:
                verts = zone_data.get('vertices', [])
                zone_color = zone_data.get('color', '#FF6600')
                zone_opacity = zone_data.get('opacity', 0.2)
                if not verts:
                    continue
                # Draw filled polygon
                poly = plt.Polygon(verts, closed=True, fill=True,
                                   facecolor=zone_color, edgecolor='white',
                                   linewidth=0.8, alpha=zone_opacity, zorder=3)
                ax.add_patch(poly)
                self._v_airspace_patches.append(poly)

                # Draw safety buffer if available
                buffer_verts = zone_data.get('buffer_vertices')
                if buffer_verts:
                    buf_poly = plt.Polygon(buffer_verts, closed=True, fill=True,
                                           facecolor=zone_color, edgecolor='none',
                                           linewidth=0, alpha=zone_opacity * 0.3, zorder=2)
                    ax.add_patch(buf_poly)
                    self._v_airspace_patches.append(buf_poly)

                # Draw zone label
                cx, cy = zone_data.get('center', (0, 0))
                label = zone_data.get('name', '')
                ax.text(cx, cy, label, fontsize=4.5, color='white', alpha=0.7,
                        ha='center', va='center', fontweight='bold', zorder=6,
                        bbox=dict(boxstyle="round,pad=0.1", facecolor='#000000',
                                  edgecolor='none', alpha=0.4))

            # Update airspace status overlay
            report = airspace_manager.update((dx, dy), altitude, 0)
            has_violations = report.get('has_violations', False)
            v_count = report.get('violation_count', 0)
            risk_score = report.get('airspace_risk_score', 0.0)

            if has_violations:
                status_text = f"AIRSPACE: {v_count} VIOLATION(S)"
                status_color = PColor.DANGER
                border_color = PColor.ZONE_PROHIBITED
            elif risk_score > 0.5:
                status_text = f"AIRSPACE: RISK {risk_score:.2f}"
                status_color = PColor.WARNING
                border_color = PColor.ZONE_RESTRICTED
            else:
                status_text = "AIRSPACE: CLEAR"
                status_color = PColor.SUCCESS
                border_color = PColor.ZONE_SAFE

            self._v_airspace_status.set_text(status_text)
            self._v_airspace_status.set_color(status_color)
            self._v_airspace_status.set_bbox(dict(boxstyle="round,pad=0.12",
                facecolor=PColor.BG_GLASS, edgecolor=border_color, linewidth=0.8))

        # ── Drone, trail, path ──
        self._v_sensor.center = (dx, dy); self._v_sensor_fill.center = (dx, dy)
        self._v_drone.center = (dx, dy); self._v_drone_glow.center = (dx, dy)
        hl = 2.0
        self._v_heading.set_data([dx, dx + hl * math.cos(heading)], [dy, dy + hl * math.sin(heading)])
        self._v_target.set_data([tx], [ty]); self._v_target_glow.center = (tx, ty)
        self.trail.append((dx, dy)); self.trail = self.trail[-MAX_TRAIL:]
        if self.trail:
            ta = np.asarray(self.trail); self._v_trail.set_data(ta[:, 0], ta[:, 1])
        dp = smooth_path or path
        if dp is not None:
            arr = np.asarray(dp)
            self._v_path.set_data(arr[:, 0], arr[:, 1])
            self._v_path_glow.set_data(arr[:, 0], arr[:, 1])
        else:
            self._v_path.set_data([], []); self._v_path_glow.set_data([], [])

    def _update_telem1(self, drone, dx, dy, tx, ty, dt):
        speed = float(getattr(drone, "speed", 0.0)) if drone else 0.0
        hdg_deg = (float(getattr(drone, "heading", 0.0)) * 180.0 / math.pi) % 360.0 if drone else 0.0
        dist = math.hypot(tx - dx, ty - dy)
        if len(self.trail) >= 2:
            vs = math.hypot(self.trail[-2][0] - dx, self.trail[-2][1] - dy) / max(dt, 0.001)
        else: vs = speed
        sig = max(50, int(100 - dist * 0.5))
        time_air = time.strftime("%M:%S", time.gmtime(time.time() - self.mission_start_time))
        mode = getattr(drone, 'flight_mode', 'NORMAL') if drone else 'NORMAL'
        mode_str = str(mode.value if hasattr(mode, 'value') else mode)[:8]
        deg = chr(176)
        vals = [f"{speed:.1f} m/s", f"{hdg_deg:.0f}{deg}", f"{dist:.1f} m", f"{vs:.1f} m/s",
                f"{tx:.0f},{ty:.0f}", time_air, f"{sig}%", mode_str]
        for i, v in enumerate(self._t1_l):
            if i < len(vals) and i < 4: v.set_text(vals[i])
        for i, v in enumerate(self._t1_r):
            j = i + 4
            if j < len(vals): v.set_text(vals[j])

    def _update_telem2(self, pct, emergency):
        pct = min(100, max(0, pct or 0))
        w = 0.72 * (pct / 100.0)
        col = PColor.SUCCESS if pct > 50 else (PColor.WARNING if pct > 20 else PColor.DANGER)
        st = "SYSTEM NOMINAL" if pct > 50 else ("LOW BATTERY" if pct > 20 else "CRITICAL")
        self._bat_fill.set_width(w); self._bat_fill.set_facecolor(col)
        self._bat_pct.set_text(f"{pct:.0f}%"); self._bat_pct.set_color(col)
        self._bat_st.set_text(st); self._bat_st.set_color(col)
        es = str(emergency or "NORMAL")
        ec = PColor.DANGER if "CRITICAL" in es else (PColor.WARNING if "LOW" in es else PColor.SUCCESS)
        self._bat_em.set_text(f"EMERGENCY: {es[:12]}"); self._bat_em.set_color(ec)

    def _update_airspace_panel(self, airspace_manager, dx, dy, altitude):
        if airspace_manager is None:
            for v in self._as_labels:
                v.set_text("--")
            self._as_decision.set_text("DECISION: N/A")
            return

        report = airspace_manager.update((dx, dy), altitude, 0)
        zones_active = airspace_manager.geofence.get_zone_count()
        violations = report.get('violation_count', 0)
        active_tfrs = report.get('active_tfrs', 0)
        risk = report.get('airspace_risk_score', 0.0)

        self._as_labels[0].set_text(f"{zones_active}")
        self._as_labels[1].set_text(f"{violations}")
        self._as_labels[2].set_text(f"{active_tfrs}")
        self._as_labels[3].set_text(f"{risk:.3f}")

        # Update decision
        decision = airspace_manager.get_active_decision() or "PROCEED"
        if decision in ("abort_mission", "return_home", "land"):
            dc = PColor.DANGER
        elif decision in ("avoid", "fly_around"):
            dc = PColor.WARNING
        else:
            dc = PColor.SUCCESS
        self._as_decision.set_text(f"DECISION: {decision.upper()}")
        self._as_decision.set_color(dc)
        self._current_decision = decision
        self._current_decision_color = dc

    def _update_altimeter(self, altitude):
        if altitude is None:
            altitude = 50.0
        self._alt_current.set_text(f"CURRENT ALT: {altitude:.0f}m")

    def _update_metrics_graph(self, bat_pct, explored, mem_d, airspace_manager=None):
        risk = 0.3
        mem = (mem_d or 0) / 100.0
        cog = (explored or 0) / 100.0
        bat = (bat_pct or 100) / 100.0
        spd = 0.5
        att = 0.75 + 0.15 * math.sin(self._frame_count * 0.05)
        asp = getattr(airspace_manager, '_airspace_risk_score', 0.0) if airspace_manager else 0.0

        self._h_risk.append(risk); self._h_mem.append(mem); self._h_att.append(att)
        self._h_cog.append(cog); self._h_bat.append(bat); self._h_spd.append(spd)
        self._h_asp.append(asp)

        for h in [self._h_risk, self._h_mem, self._h_att, self._h_cog, self._h_bat, self._h_spd, self._h_asp]:
            if len(h) > MAX_HISTORY: del h[:len(h) - MAX_HISTORY]

        n = len(self._h_risk); x = np.arange(n)
        data = [self._h_risk, self._h_mem, self._h_att, self._h_cog, self._h_bat, self._h_spd, self._h_asp]
        for ln, h in zip(self._m_lines, data):
            ln.set_data(x, h)
        self._ax_metrics.set_xlim(max(0, n - MAX_HISTORY), max(MAX_HISTORY, n))

    def _update_brain(self, brain_log, behavior, mission, emergency, obs, airspace_manager=None):
        if not brain_log:
            # Still show airspace engine status
            if airspace_manager:
                self._update_brain_engines(behavior, mission, emergency, obs, airspace_manager)
            return
        self._update_brain_engines(behavior, mission, emergency, obs, airspace_manager)

    def _update_brain_engines(self, behavior, mission, emergency, obs, airspace_manager=None):
        latest = {}
        dc = PColor.WARNING if behavior == "AVOID" else (PColor.SUCCESS if behavior == "NAVIGATE" else PColor.DANGER)
        self._b_dec.set_text(f"DECISION: {behavior}"); self._b_dec.set_color(dc)
        self._b_mis.set_text(f"MISSION: {mission}")
        path_len = latest.get("path_len", 0); ex = latest.get("explored", 0); oc = obs or 0

        # Get airspace metrics
        as_violations = 0
        as_zones = 0
        if airspace_manager:
            as_violations = airspace_manager.geofence.get_violation_count()
            as_zones = airspace_manager.geofence.get_zone_count()

        effs = {
            "PERCEPTION": min(99, max(30, 90 - oc * 2)),
            "BEHAVIOR": 98 if behavior == "NAVIGATE" else 85,
            "MEMORY": min(95, max(40, int(ex * 0.8 + 20))),
            "EMERGENCY": 99 if emergency == "NORMAL" else 60,
            "PLANNING": min(99, max(40, 95 if path_len > 0 else 10)),
            "RISK": min(95, max(50, 70 + oc * 3)),
            "FUSION": 92 if behavior != "IDLE" else 25,
            "MOTION": 90 if behavior == "NAVIGATE" else 70,
            "GEOFENCE": min(99, max(30, 95 - as_violations * 15)),
            "ALTITUDE": min(99, max(40, 90)),
        }
        for nm, dot, bar, pct in self._b_eng:
            eff = effs.get(nm, 80)
            c = PColor.SUCCESS if eff > 80 else (PColor.WARNING if eff > 50 else PColor.DANGER)
            dot.set_color(c); bar.set_width(0.18 * (eff / 100.0)); bar.set_facecolor(c)
            pct.set_text(f"{eff}%")

    def _blit(self):
        if not self._init_done: return
        try:
            if self._bg_cache is not None:
                self.fig.canvas.restore_region(self._bg_cache)
                for ax in self._all_axes: self.fig.canvas.blit(ax.bbox)
        except: self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def switch_camera(self): self.camera.cycle_mode()
    def close(self): plt.close(self.fig)


def draw_premium(world=None, drone=None, target=None, path=None, smooth_path=None,
                 occupancy_grid=None, sensor_radius=8, perception_map=None,
                 risk_map=None, memory_map=None, behavior_state=None,
                 mission_state=None, planner_name=None, emergency_state=None,
                 battery_percentage=None, memory_density=None, active_cells=None,
                 context_map=None, cognitive_map=None, explored_percent=None,
                 premium_world=None, camera_mode=None, living_world=None,
                 brain_log=None, drone_speed=None, drone_altitude=None,
                 battery_drain_rate=None, visible_obstacles=None,
                 weather_fx=None, airspace_manager=None) -> None:
    global _premium_dashboard
    if _premium_dashboard is None or not plt.fignum_exists(_premium_dashboard.fig.number):
        _premium_dashboard = PremiumDashboard()
    _premium_dashboard.update(
        world=world, drone=drone, target=target, path=path, smooth_path=smooth_path,
        occupancy_grid=occupancy_grid, perception_map=perception_map,
        risk_map=risk_map, memory_map=memory_map, context_map=context_map,
        cognitive_map=cognitive_map, premium_world=premium_world,
        behavior_state=behavior_state or "--", mission_state=mission_state or "--",
        planner_name=planner_name or "--", emergency_state=emergency_state or "NORMAL",
        battery_percentage=battery_percentage or 0,
        memory_density=memory_density or 0, active_cells=active_cells or 0,
        explored_percent=explored_percent or 0, camera_mode=camera_mode,
        living_world=living_world, brain_log=brain_log,
        drone_speed=drone_speed, drone_altitude=drone_altitude,
        battery_drain_rate=battery_drain_rate,
        visible_obstacles=visible_obstacles, weather_fx=weather_fx,
        airspace_manager=airspace_manager,
    )


def reset_premium_dashboard():
    global _premium_dashboard
    if _premium_dashboard is not None:
        try: plt.close(_premium_dashboard.fig)
        except: pass
        _premium_dashboard = None