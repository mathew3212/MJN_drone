"""
Mission Control Workspace
==========================
Top-level workspace orchestrator tying together the full customizable
dashboard system: widgets, drag-drop, command palette, layout profiles,
themes, graphs, keyboard shortcuts, and floating windows.

Now with full matplotlib rendering support:
  - Each widget gets its own axes on a dedicated figure
  - Users can drag widgets by clicking and moving
  - Users can resize widgets by dragging edges/corners
  - Graphs render live data on their axes
"""

from __future__ import annotations

import time
import json
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import matplotlib.patches as mpatches

from .widget_base import (
    Widget, WidgetState, WidgetConfig, WidgetGeometry, ResizeHandle, ThemePreset,
    WorldMapWidget, TelemetryWidget, BatteryWidget,
)
from .workspace_manager import WorkspaceGrid, DragDropEngine
from .command_palette import CommandPalette, Command
from .layout_profiles import LayoutManager, LayoutProfile
from .graph_registry import GraphRegistry, GraphWidget, GraphSpec
from .theme_manager import ThemeManager


class MissionControlWorkspace:
    """
    Full customizable Mission Control Workspace.

    Usage:
        ws = MissionControlWorkspace(figsize=(18, 10))
        ws.add_widget(WorldMapWidget())
        ws.add_widget(TelemetryWidget())
        ws.setup_figure()       # creates the matplotlib figure
        ws.render_all()          # draws all widgets to their axes
        ws.connect_events()      # enables mouse drag/resize
    """

    def __init__(self, world_width=100, world_height=100, theme=ThemePreset.DARK,
                 figsize=(18, 10), figure_name="Mission Control Workspace"):
        self.world_width = world_width
        self.world_height = world_height
        self.grid = WorkspaceGrid(rows=24, cols=24, cell_size=50.0)
        self.dragdrop = DragDropEngine(self.grid)
        self.palette = CommandPalette()
        self.layouts = LayoutManager()
        self.graphs = GraphRegistry()
        self.theme = ThemeManager()
        self.theme.set_theme(theme)
        self._widgets: Dict[str, Widget] = {}
        self._selected: Optional[str] = None
        self._mode = "grid"  # grid | free | snap
        self._running = False
        self._last_update = time.time()
        self._register_default_commands()

        # Matplotlib rendering attributes
        self._figsize = figsize
        self._figure_name = figure_name
        self.fig: Optional[Figure] = None
        self._widget_axes: Dict[str, Axes] = {}  # widget_id -> matplotlib Axes
        self._dragging_enabled = True
        self._resizing_enabled = True
        self._bg_cache = None

    # ── Figure Setup ────────────────────────────────────────────

    def setup_figure(self):
        """Create the matplotlib figure for rendering workspace widgets."""
        plt.ion()
        self.fig = plt.figure(
            figsize=self._figsize,
            num=self._figure_name,
            facecolor="#0B0E14",
            dpi=100,
        )
        self.fig.canvas.mpl_connect('button_press_event', self._on_fig_press)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_fig_move)
        self.fig.canvas.mpl_connect('button_release_event', self._on_fig_release)
        self.fig.canvas.mpl_connect('key_press_event', self._on_fig_key)
        self._bg_cache = None

    def connect_events(self):
        """Ensure canvas events are connected (idempotent)."""
        if self.fig is not None:
            self.fig.canvas.mpl_connect('button_press_event', self._on_fig_press)
            self.fig.canvas.mpl_connect('motion_notify_event', self._on_fig_move)
            self.fig.canvas.mpl_connect('button_release_event', self._on_fig_release)
            self.fig.canvas.mpl_connect('key_press_event', self._on_fig_key)

    def _on_fig_press(self, event):
        if event.inaxes is None:
            return
        # Convert figure coordinates to workspace grid coordinates
        x = event.xdata if event.xdata is not None else 0
        y = event.ydata if event.ydata is not None else 0
        # Find which widget this axes belongs to
        for wid, ax in self._widget_axes.items():
            if ax == event.inaxes:
                w = self._widgets.get(wid)
                if w:
                    # Map to widget-local coords
                    bbox = ax.get_position()
                    fig_x = event.x / self.fig.dpi
                    fig_y = (self.fig.get_window_extent().height - event.y) / self.fig.dpi
                    local_x = (event.xdata - ax.get_xlim()[0]) / (ax.get_xlim()[1] - ax.get_xlim()[0]) * w.geometry.width
                    local_y = (event.ydata - ax.get_ylim()[0]) / (ax.get_ylim()[1] - ax.get_ylim()[0]) * w.geometry.height
                    # Use the widget's geometry bounds
                    gx, gy, gx2, gy2 = w.get_bounds()
                    self.on_mouse_press(gx + local_x, gy + local_y)
                break

    def _on_fig_move(self, event):
        if event.inaxes is None:
            return
        x = event.xdata if event.xdata is not None else 0
        y = event.ydata if event.ydata is not None else 0
        # Find which widget
        for wid, ax in self._widget_axes.items():
            if ax == event.inaxes:
                w = self._widgets.get(wid)
                if w:
                    local_x = (event.xdata - ax.get_xlim()[0]) / (ax.get_xlim()[1] - ax.get_xlim()[0]) * w.geometry.width
                    local_y = (event.ydata - ax.get_ylim()[0]) / (ax.get_ylim()[1] - ax.get_ylim()[0]) * w.geometry.height
                    gx, gy, gx2, gy2 = w.get_bounds()
                    self.on_mouse_move(gx + local_x, gy + local_y)
                break

    def _on_fig_release(self, event):
        x = event.xdata if event.xdata is not None else 0
        y = event.ydata if event.ydata is not None else 0
        for wid, ax in self._widget_axes.items():
            if ax == event.inaxes:
                w = self._widgets.get(wid)
                if w:
                    local_x = (event.xdata - ax.get_xlim()[0]) / (ax.get_xlim()[1] - ax.get_xlim()[0]) * w.geometry.width
                    local_y = (event.ydata - ax.get_ylim()[0]) / (ax.get_ylim()[1] - ax.get_ylim()[0]) * w.geometry.height
                    gx, gy, gx2, gy2 = w.get_bounds()
                    self.on_mouse_release(gx + local_x, gy + local_y)
                break
        # After drag/resize, rebuild axes layout
        if self.dragdrop._dragging is not None or self.dragdrop._resizing is not None:
            self._rebuild_axes()

    def _on_fig_key(self, event):
        self.on_key_press(event.key)

    # ── Rendering ───────────────────────────────────────────────

    def render_all(self):
        """Render all visible widgets to their respective axes."""
        if self.fig is None:
            self.setup_figure()
        self._rebuild_axes()
        self._blit()

    def _rebuild_axes(self):
        """Remove all existing widget axes and recreate them from scratch."""
        if self.fig is None:
            return
        # Remove old axes that belong to widgets
        for wid, ax in list(self._widget_axes.items()):
            try:
                ax.remove()
            except Exception:
                pass
        self._widget_axes.clear()

        # Clear figure but keep the figure itself
        self.fig.clf()

        # Create axes for each visible docked widget
        total_cells = self.grid.rows * self.grid.cols
        if total_cells == 0:
            return

        cell_w = 1.0 / self.grid.cols
        cell_h = 1.0 / self.grid.rows

        for w in self._widgets.values():
            if not w.is_visible or w.state not in (WidgetState.DOCKED, WidgetState.FLOATING):
                continue
            g = w.geometry
            # Map grid position to figure coordinates (0-1 range)
            left = g.grid_col * cell_w
            bottom = 1.0 - (g.grid_row + g.grid_rowspan) * cell_h
            width = g.grid_colspan * cell_w
            height = g.grid_rowspan * cell_h

            # Clamp to valid range
            left = max(0.01, min(left, 0.98))
            bottom = max(0.01, min(bottom, 0.98))
            width = max(0.02, min(width, 0.98 - left))
            height = max(0.02, min(height, 0.98 - bottom))

            ax = self.fig.add_axes([left, bottom, width, height], label=w.id)
            ax.set_facecolor("#0D1019")
            ax.tick_params(colors="#4A5A78", labelsize=6)
            for spine in ax.spines.values():
                spine.set_color("#1A2035")
                spine.set_linewidth(0.5)
            if w.is_active:
                for spine in ax.spines.values():
                    spine.set_color("#00D4FF")
                    spine.set_linewidth(1.0)

            w.set_content(ax)
            self._widget_axes[w.id] = ax

            # Draw widget title label
            ax.text(0.5, 1.02, w.title, transform=ax.transAxes,
                    ha="center", va="bottom", fontsize=8, fontweight="bold",
                    color="#6B7FA0")

            # Render the widget content
            w.render()

        self.fig.canvas.draw()
        self._bg_cache = self.fig.canvas.copy_from_bbox(self.fig.bbox)

    def _blit(self):
        """Blit the figure for flicker-free updates."""
        if self.fig is None or not hasattr(self.fig.canvas, 'copy_from_bbox'):
            return
        try:
            if self._bg_cache is not None:
                self.fig.canvas.restore_region(self._bg_cache)
                for ax in self._widget_axes.values():
                    self.fig.canvas.blit(ax.bbox)
            self.fig.canvas.flush_events()
        except Exception:
            try:
                self.fig.canvas.draw_idle()
            except Exception:
                pass

    def update_and_render(self, data: Any = None):
        """Update all widgets with data and re-render them.
        
        Rebuilds axes if new widgets were added since last render.
        """
        # Rebuild axes if we have widgets without axes
        if len(self._widget_axes) != len(self._widgets):
            self._rebuild_axes()
            return

        for w in self._widgets.values():
            w.update(data)
        for wid, ax in self._widget_axes.items():
            w = self._widgets.get(wid)
            if w:
                w.render()
        self._blit()

    # ── Widget Management ───────────────────────────────────────

    def add_widget(self, widget: Widget, row=None, col=None) -> bool:
        wid = widget.id
        geo = widget.geometry
        if row is None:
            row = geo.grid_row
        if col is None:
            col = geo.grid_col
        rs, cs = geo.grid_rowspan, geo.grid_colspan
        if not self.grid.place_widget(widget, row, col, rs, cs):
            pos = self.grid.find_snap_position(row, col, rs, cs)
            if pos is None:
                return False
            row, col = pos
            self.grid.place_widget(widget, row, col, rs, cs)
        self._widgets[wid] = widget
        self._register_widget_commands(widget)
        return True

    def remove_widget(self, widget_id: str):
        if widget_id in self._widgets:
            self.grid.remove_widget(widget_id)
            if widget_id in self._widget_axes:
                try:
                    self._widget_axes[widget_id].remove()
                except Exception:
                    pass
                del self._widget_axes[widget_id]
            del self._widgets[widget_id]

    def get_widget(self, widget_id: str) -> Optional[Widget]:
        return self._widgets.get(widget_id)

    def list_widgets(self) -> List[Widget]:
        return list(self._widgets.values())

    def focus_widget(self, widget_id: str):
        self._selected = widget_id
        for wid, w in self._widgets.items():
            w.is_active = (wid == widget_id)

    # ── Drag / Drop / Resize ───────────────────────────────────

    def on_mouse_press(self, x: float, y: float):
        # Check resize handles first
        for w in self._widgets.values():
            if w.state == WidgetState.DOCKED and w.is_visible:
                handle = w.get_resize_handle(x, y)
                if handle != ResizeHandle.NONE:
                    self.dragdrop.start_resize(w, handle, x, y)
                    self.focus_widget(w.id)
                    return
        # Then check widget bodies for drag
        for w in reversed(list(self._widgets.values())):
            if w.state == WidgetState.DOCKED and w.is_visible and w.contains_point(x, y):
                self.dragdrop.start_drag(w, x, y)
                self.focus_widget(w.id)
                return

    def on_mouse_move(self, x: float, y: float):
        if self.dragdrop._dragging is not None:
            snap = self.dragdrop.update_drag(x, y)
            if snap:
                row, col = snap
                w = self.dragdrop._dragging
                g = w.geometry
                g.grid_row = row
                g.grid_col = col
                g.x = col * self.grid.cell_size
                g.y = row * self.grid.cell_size
        elif self.dragdrop._resizing is not None:
            self.dragdrop.update_resize(x, y)

    def on_mouse_release(self, x: float, y: float):
        if self.dragdrop._dragging is not None:
            w = self.dragdrop._dragging
            g = w.geometry
            self.dragdrop.end_drag(w, g.grid_row, g.grid_col)
        elif self.dragdrop._resizing is not None:
            w = self.dragdrop._resizing[0]
            self.dragdrop.end_resize(w)

    # ── Keyboard Shortcuts ─────────────────────────────────────

    def on_key_press(self, key: str, modifiers=None):
        k = key.lower()
        # Command palette
        if k == "p" and (modifiers or []).__contains__("ctrl"):
            if self.palette.is_open:
                self.palette.close()
            else:
                self.palette.open()
            return
        if self.palette.is_open:
            if k == "escape":
                self.palette.close()
                return
            if k == "return":
                self.palette.select_current()
                self.palette.close()
                return
            if k == "arrow_down":
                self.palette.navigate(1)
                return
            if k == "arrow_up":
                self.palette.navigate(-1)
                return
            if len(k) == 1:
                self.palette._query += k
                return
        # Widget-level shortcuts
        if k == "f" and self._selected:
            w = self._widgets.get(self._selected)
            if w:
                w.toggle_fullscreen()
        if k == "c" and self._selected:
            w = self._widgets.get(self._selected)
            if w:
                w.toggle_float()
        if k == "t" and self._selected:
            w = self._widgets.get(self._selected)
            if w:
                w.toggle_collapse()

    # ── Commands ───────────────────────────────────────────────

    def _register_default_commands(self):
        self.palette.register(Command("save_layout", "Save Layout", "Workspace", "Ctrl+Shift+S",
                                       self.layouts.save_current))
        self.palette.register(Command("theme_dark", "Theme: Dark", "Appearance", "",
                                       lambda: self.theme.set_theme(ThemePreset.DARK)))
        self.palette.register(Command("theme_light", "Theme: Light", "Appearance", "",
                                       lambda: self.theme.set_theme(ThemePreset.LIGHT)))
        self.palette.register(Command("theme_midnight", "Theme: Midnight", "Appearance", "",
                                       lambda: self.theme.set_theme(ThemePreset.MIDNIGHT)))
        self.palette.register(Command("theme_blueprint", "Theme: Blueprint", "Appearance", "",
                                       lambda: self.theme.set_theme(ThemePreset.BLUEPRINT)))
        self.palette.register(Command("theme_graphite", "Theme: Graphite", "Appearance", "",
                                       lambda: self.theme.set_theme(ThemePreset.GRAPHITE)))
        self.palette.register(Command("theme_arctic", "Theme: Arctic", "Appearance", "",
                                       lambda: self.theme.set_theme(ThemePreset.ARCTIC)))
        self.palette.register(Command("theme_operator", "Theme: Operator", "Appearance", "",
                                       lambda: self.theme.set_theme(ThemePreset.OPERATOR)))

    def _register_widget_commands(self, widget: Widget):
        wid = widget.id
        self.palette.register(Command(
            f"widget_close_{wid}", f"Close {widget.title}", "Widgets", "",
            lambda w=wid: self.remove_widget(w)))
        self.palette.register(Command(
            f"widget_fullscreen_{wid}", f"Fullscreen {widget.title}", "Widgets", "F",
            lambda w=wid: self._widgets.get(w) and self._widgets[w].toggle_fullscreen()))
        self.palette.register(Command(
            f"widget_float_{wid}", f"Float {widget.title}", "Widgets", "C",
            lambda w=wid: self._widgets.get(w) and self._widgets[w].toggle_float()))

    # ── Data Update ────────────────────────────────────────────

    def update_widget(self, widget_id: str, data: Any):
        w = self._widgets.get(widget_id)
        if w:
            w.update(data)

    def broadcast(self, data: Any):
        for w in self._widgets.values():
            w.update(data)

    # ── Serialization ──────────────────────────────────────────

    def serialize(self) -> dict:
        return {
            "grid": self.grid.to_dict(),
            "widgets": [w.serialize() for w in self._widgets.values()],
            "selected": self._selected,
            "theme": self.theme.get_current_preset().value,
            "mode": self._mode,
        }

    def save_layout(self, name: str):
        self.layouts.save_current(name, list(self._widgets.values()), self.grid.to_dict())

    def load_layout(self, name: str):
        profile = self.layouts.load(name)
        if not profile:
            return
        for wdict in profile.widgets:
            pass  # Reconstruct widget from dict

    def export_workspace(self) -> str:
        return json.dumps(self.serialize(), indent=2)

    def import_workspace(self, json_str: str):
        data = json.loads(json_str)
        self._mode = data.get("mode", "grid")
        self._selected = data.get("selected")

    # ── Stats ──────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "widgets": len(self._widgets),
            "selected": self._selected,
            "theme": self.theme.get_current_preset().value,
            "mode": self._mode,
            "grid_used": len(self.grid._cells),
        }