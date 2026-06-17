"""
Workspace Manager
=================
Grid-based layout engine with drag-drop, snap, dock, resize support.
"""

from __future__ import annotations

import math
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict

from .widget_base import Widget, WidgetState, WidgetGeometry, ResizeHandle


@dataclass
class GridCell:
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    widget_id: Optional[str] = None

    def overlaps(self, other: "GridCell") -> bool:
        r1, r2 = self.row, self.row + self.rowspan
        r3, r4 = other.row, other.row + other.rowspan
        c1, c2 = self.col, self.col + self.colspan
        c3, c4 = other.col, other.col + other.colspan
        return not (r2 <= r3 or r1 >= r4 or c2 <= c3 or c1 >= c4)


class WorkspaceGrid:
    """Responsive grid for widget placement and collision detection."""

    def __init__(self, rows: int = 24, cols: int = 24, cell_size: float = 50.0):
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self._cells: List[GridCell] = []

    def cell_at(self, row: int, col: int) -> Optional[GridCell]:
        for c in self._cells:
            if (c.row <= row < c.row + c.rowspan and
                c.col <= col < c.col + c.colspan):
                return c
        return None

    def place_widget(self, widget: Widget, row: int, col: int,
                     rowspan: int = 1, colspan: int = 1) -> bool:
        new_cell = GridCell(row, col, rowspan, colspan, widget.id)
        for existing in self._cells:
            if existing.widget_id and existing.widget_id != widget.id:
                if new_cell.overlaps(existing):
                    return False
        # Remove old cell for this widget
        self._cells = [c for c in self._cells if c.widget_id != widget.id]
        self._cells.append(new_cell)
        geo = widget.geometry
        geo.grid_row = row
        geo.grid_col = col
        geo.grid_rowspan = rowspan
        geo.grid_colspan = colspan
        geo.x = col * self.cell_size
        geo.y = row * self.cell_size
        geo.width = colspan * self.cell_size
        geo.height = rowspan * self.cell_size
        widget.set_geometry(geo)
        return True

    def find_snap_position(self, row: int, col: int, rowspan: int, colspan: int,
                            exclude_widget_id: Optional[str] = None) -> Optional[Tuple[int, int]]:
        """Find nearest valid grid position."""
        for dr in range(self.rows - rowspan + 1):
            for dc in range(self.cols - colspan + 1):
                candidate = GridCell(dr, dc, rowspan, colspan)
                valid = True
                for existing in self._cells:
                    if existing.widget_id == exclude_widget_id:
                        continue
                    if candidate.overlaps(existing):
                        valid = False
                        break
                if valid:
                    return (dr, dc)
        return None

    def remove_widget(self, widget_id: str):
        self._cells = [c for c in self._cells if c.widget_id != widget_id]

    def get_widget_cell(self, widget_id: str) -> Optional[GridCell]:
        for c in self._cells:
            if c.widget_id == widget_id:
                return c
        return None

    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "cell_size": self.cell_size,
            "cells": [asdict(c) for c in self._cells],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkspaceGrid":
        g = cls(d.get("rows", 24), d.get("cols", 24), d.get("cell_size", 50.0))
        for cd in d.get("cells", []):
            g._cells.append(GridCell(**cd))
        return g


class DragDropEngine:
    """Handles widget dragging, dropping, snapping, and swapping."""

    def __init__(self, grid: WorkspaceGrid):
        self.grid = grid
        self._dragging: Optional[Widget] = None
        self._drag_offset = (0.0, 0.0)
        self._drag_start_pos = (0.0, 0.0)
        self._resizing: Optional[Tuple[Widget, ResizeHandle]] = None
        self._resize_start: Dict[str, Any] = {}
        self._snap_threshold: float = 10.0
        self._on_widget_moved: List = []
        self._on_widget_resized: List = []

    def start_drag(self, widget: Widget, mx: float, my: float):
        self._dragging = widget
        g = widget.geometry
        self._drag_offset = (mx - g.x, my - g.y)
        self._drag_start_pos = (g.grid_row, g.grid_col)
        widget.is_active = True

    def update_drag(self, mx: float, my: float) -> Optional[Tuple[int, int]]:
        if self._dragging is None:
            return None
        w = self._dragging
        g = w.geometry
        new_x = mx - self._drag_offset[0]
        new_y = my - self._drag_offset[1]
        g.x = max(0, new_x)
        g.y = max(0, new_y)
        # Snap to grid
        snap_row = round(g.y / self.grid.cell_size)
        snap_col = round(g.x / self.grid.cell_size)
        snap_row = max(0, min(snap_row, self.grid.rows - g.grid_rowspan))
        snap_col = max(0, min(snap_col, self.grid.cols - g.grid_colspan))
        return (snap_row, snap_col)

    def end_drag(self, widget: Widget, row: int, col: int) -> bool:
        if self._dragging is None or self._dragging.id != widget.id:
            return False
        success = self.grid.place_widget(widget, row, col,
                                         widget.geometry.grid_rowspan,
                                         widget.geometry.grid_colspan)
        if not success:
            # Try to swap with existing widget
            target = self.grid.cell_at(row, col)
            if target and target.widget_id:
                # Swap
                old_cell = self.grid.get_widget_cell(widget.id)
                if old_cell:
                    self.grid.place_widget(widget, row, col,
                                           old_cell.rowspan, old_cell.colspan)
        for cb in self._on_widget_moved:
            try:
                cb(widget, row, col)
            except Exception:
                pass
        self._dragging = None
        widget.is_active = False
        return success

    def start_resize(self, widget: Widget, handle: ResizeHandle, mx: float, my: float):
        self._resizing = (widget, handle)
        g = widget.geometry
        self._resize_start = {
            "x": g.x, "y": g.y, "width": g.width, "height": g.height,
            "mx": mx, "my": my, "grid_row": g.grid_row, "grid_col": g.grid_col,
            "rowspan": g.grid_rowspan, "colspan": g.grid_colspan,
        }

    def update_resize(self, mx: float, my: float) -> Optional[Dict[str, Any]]:
        if self._resizing is None:
            return None
        widget, handle = self._resizing
        g = widget.geometry
        s = self._resize_start
        dx = mx - s["mx"]
        dy = my - s["my"]
        new_w = max(g.min_width, s["width"] + (dx if handle in (ResizeHandle.RIGHT, ResizeHandle.TOP_RIGHT, ResizeHandle.BOTTOM_RIGHT) else -dx))
        new_h = max(g.min_height, s["height"] + (dy if handle in (ResizeHandle.BOTTOM, ResizeHandle.BOTTOM_LEFT, ResizeHandle.BOTTOM_RIGHT) else -dy))
        # Snap to grid
        new_colspan = max(1, round(new_w / self.grid.cell_size))
        new_rowspan = max(1, round(new_h / self.grid.cell_size))
        new_w = new_colspan * self.grid.cell_size
        new_h = new_rowspan * self.grid.cell_size
        g.width = min(new_w, g.max_width)
        g.height = min(new_h, g.max_height)
        g.grid_colspan = new_colspan
        g.grid_rowspan = new_rowspan
        return {"width": g.width, "height": g.height, "colspan": new_colspan, "rowspan": new_rowspan}

    def end_resize(self, widget: Widget) -> bool:
        if self._resizing is None or self._resizing[0].id != widget.id:
            return False
        for cb in self._on_widget_resized:
            try:
                cb(widget)
            except Exception:
                pass
        self._resizing = None
        return True

    def cancel(self):
        self._dragging = None
        self._resizing = None