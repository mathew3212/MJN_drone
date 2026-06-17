"""
Cinematic Camera System
=======================
10 camera modes for the autonomous drone simulation:

  1. PILOT_VIEW    - First-person from drone's perspective
  2. FPV           - First-person view with HUD overlay
  3. CHASE         - Following behind the drone
  4. ORBIT         - Circular orbit around the drone
  5. FREE          - Free-moving camera (drag/scroll)
  6. CINEMATIC     - Pre-programmed cinematic path
  7. TOP_VIEW      - Top-down orthographic
  8. SIDE_VIEW     - Side tracking view
  9. TRACKING      - Tracking a target point
  10. REPLAY        - Replay/review camera

All modes feature:
  - Smooth transitions (ease-in-out interpolation)
  - Configurable distance/height/offset
  - Automatic damping for cinematic feel
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Tuple, Callable

import numpy as np


class CameraMode(Enum):
    """All available camera modes."""
    PILOT_VIEW = auto()
    FPV = auto()
    CHASE = auto()
    ORBIT = auto()
    FREE = auto()
    CINEMATIC = auto()
    TOP_VIEW = auto()
    SIDE_VIEW = auto()
    TRACKING = auto()
    REPLAY = auto()


@dataclass
class CameraState:
    """Current camera position, target, and field of view."""
    x: float = 50.0
    y: float = 50.0
    zoom: float = 1.0
    rotation: float = 0.0  # radians
    target_x: float = 50.0
    target_y: float = 50.0
    fov: float = 60.0  # degrees
    height_offset: float = 0.0


@dataclass
class CameraTransition:
    """A smooth transition between camera states."""
    from_state: CameraState
    to_state: CameraState
    duration: float  # seconds
    elapsed: float = 0.0
    active: bool = False
    easing_fn: str = "ease_in_out"

    def update(self, dt: float) -> Optional[CameraState]:
        """Update transition, returning interpolated state or None if done."""
        if not self.active:
            return None

        self.elapsed += dt
        t = min(1.0, self.elapsed / self.duration)

        # Apply easing
        if self.easing_fn == "ease_in_out":
            t = t * t * (3.0 - 2.0 * t)
        elif self.easing_fn == "ease_out":
            t = 1.0 - (1.0 - t) ** 3
        elif self.easing_fn == "ease_in":
            t = t ** 3

        # Interpolate
        state = CameraState(
            x=self.from_state.x + (self.to_state.x - self.from_state.x) * t,
            y=self.from_state.y + (self.to_state.y - self.from_state.y) * t,
            zoom=self.from_state.zoom + (self.to_state.zoom - self.from_state.zoom) * t,
            rotation=self.from_state.rotation + (self.to_state.rotation - self.from_state.rotation) * t,
            target_x=self.from_state.target_x + (self.to_state.target_x - self.from_state.target_x) * t,
            target_y=self.from_state.target_y + (self.to_state.target_y - self.from_state.target_y) * t,
            fov=self.from_state.fov + (self.to_state.fov - self.from_state.fov) * t,
            height_offset=self.from_state.height_offset + (self.to_state.height_offset - self.from_state.height_offset) * t,
        )

        if t >= 1.0:
            self.active = False
            return self.to_state

        return state


class CameraSystem:
    """Professional multi-mode camera system for drone simulation.

    Supports 10 camera modes with smooth transitions, configurable
    parameters, and cinematic quality movements.
    """

    def __init__(self):
        self.current_mode = CameraMode.CHASE
        self.previous_mode = CameraMode.CHASE
        self.state = CameraState()
        self.desired_state = CameraState()

        # Transition
        self.transition: Optional[CameraTransition] = None
        self.transition_duration = 0.8  # Default transition time (seconds)

        # Mode-specific parameters
        self.chase_distance = 12.0
        self.chase_height = 4.0
        self.orbit_radius = 15.0
        self.orbit_speed = 0.3  # radians per second
        self.orbit_angle = 0.0
        self.free_pan_speed = 1.5
        self.free_zoom_speed = 0.1
        self.cinematic_time = 0.0
        self.cinematic_path: list = []  # List of (x, y, zoom) waypoints

        # Target tracking
        self.tracked_x: float = 50.0
        self.tracked_y: float = 50.0
        self.tracked_heading: float = 0.0

        # Smoothing
        self.smooth_factor = 0.08
        self.smoothed_x: float = 50.0
        self.smoothed_y: float = 50.0
        self.smoothed_zoom: float = 1.0

        # Window / viewport dimensions
        self.view_width: float = 100.0
        self.view_height: float = 100.0

        # Initialize cinematic path
        self._init_cinematic_path()

    # ══════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════

    def set_mode(self, mode: CameraMode, instant: bool = False):
        """Switch camera mode with smooth transition."""
        if mode == self.current_mode and not instant:
            return

        self.previous_mode = self.current_mode
        self.current_mode = mode
        self.desired_state = self._compute_desired_state()

        if instant:
            self.state = CameraState(
                x=self.desired_state.x,
                y=self.desired_state.y,
                zoom=self.desired_state.zoom,
                rotation=self.desired_state.rotation,
                target_x=self.desired_state.target_x,
                target_y=self.desired_state.target_y,
                fov=self.desired_state.fov,
                height_offset=self.desired_state.height_offset,
            )
            self.smoothed_x = self.state.x
            self.smoothed_y = self.state.y
            self.smoothed_zoom = self.state.zoom
        else:
            self.transition = CameraTransition(
                from_state=CameraState(
                    x=self.state.x, y=self.state.y,
                    zoom=self.state.zoom, rotation=self.state.rotation,
                    target_x=self.state.target_x, target_y=self.state.target_y,
                    fov=self.state.fov, height_offset=self.state.height_offset,
                ),
                to_state=self.desired_state,
                duration=self.transition_duration,
                active=True,
            )

    def update(
        self,
        drone_x: float, drone_y: float,
        drone_heading: float,
        dt: float = 0.016,
        target_x: Optional[float] = None,
        target_y: Optional[float] = None,
    ):
        """Update camera for the current frame."""
        self.tracked_x = drone_x
        self.tracked_y = drone_y
        self.tracked_heading = drone_heading

        # Handle transition
        if self.transition and self.transition.active:
            trans_state = self.transition.update(dt)
            if trans_state:
                self.state = trans_state
            return  # During transition, don't update mode logic

        # Update desired state based on current mode
        self.desired_state = self._compute_desired_state()

        # Smooth interpolate towards desired state
        sf = self.smooth_factor
        self.smoothed_x += (self.desired_state.x - self.smoothed_x) * sf
        self.smoothed_y += (self.desired_state.y - self.smoothed_y) * sf
        self.smoothed_zoom += (self.desired_state.zoom - self.smoothed_zoom) * sf

        # Update state with smoothing
        self.state.x = self.smoothed_x
        self.state.y = self.smoothed_y
        self.state.zoom = self.smoothed_zoom
        self.state.rotation = self.desired_state.rotation
        self.state.target_x = self.desired_state.target_x
        self.state.target_y = self.desired_state.target_y
        self.state.fov = self.desired_state.fov
        self.state.height_offset = self.desired_state.height_offset

        # Mode-specific per-frame updates
        self._update_mode_specific(dt)

    def get_view_limits(self) -> Tuple[float, float, float, float]:
        """Return (x_min, x_max, y_min, y_max) for the current camera view."""
        cx = self.state.x
        cy = self.state.y
        zoom = self.state.zoom
        vw = self.view_width / zoom
        vh = self.view_height / zoom

        return (cx - vw / 2, cx + vw / 2, cy - vh / 2, cy + vh / 2)

    def set_viewport(self, width: float, height: float):
        """Set the viewport dimensions."""
        self.view_width = width
        self.view_height = height

    def zoom_in(self, factor: float = 0.1):
        """Zoom in by factor."""
        new_zoom = self.state.zoom + factor * self.state.zoom
        self.state.zoom = min(5.0, max(0.2, new_zoom))
        self.smoothed_zoom = self.state.zoom

    def zoom_out(self, factor: float = 0.1):
        """Zoom out by factor."""
        new_zoom = self.state.zoom - factor * self.state.zoom
        self.state.zoom = min(5.0, max(0.2, new_zoom))
        self.smoothed_zoom = self.state.zoom

    def pan(self, dx: float, dy: float):
        """Pan the free camera."""
        self.state.x += dx / self.state.zoom
        self.state.y += dy / self.state.zoom
        self.smoothed_x = self.state.x
        self.smoothed_y = self.state.y

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL
    # ══════════════════════════════════════════════════════════════════

    def _compute_desired_state(self) -> CameraState:
        """Compute the desired camera state for the current mode."""
        dx = self.tracked_x
        dy = self.tracked_y
        heading = self.tracked_heading

        if self.current_mode == CameraMode.PILOT_VIEW:
            # Behind and slightly above drone
            bx = dx - self.chase_distance * 0.5 * math.cos(heading)
            by = dy - self.chase_distance * 0.5 * math.sin(heading)
            return CameraState(
                x=dx, y=dy,
                zoom=2.0,
                rotation=heading,
                target_x=bx, target_y=by,
                fov=75.0,
                height_offset=1.0,
            )

        elif self.current_mode == CameraMode.FPV:
            # Drone's exact viewpoint
            return CameraState(
                x=dx, y=dy,
                zoom=3.0,
                rotation=heading,
                target_x=dx + 20 * math.cos(heading),
                target_y=dy + 20 * math.sin(heading),
                fov=90.0,
                height_offset=0.0,
            )

        elif self.current_mode == CameraMode.CHASE:
            # Classic chase: behind and above
            bx = dx - self.chase_distance * math.cos(heading)
            by = dy - self.chase_distance * math.sin(heading)
            return CameraState(
                x=bx, y=by,
                zoom=1.2,
                rotation=0.0,
                target_x=dx, target_y=dy,
                fov=60.0,
                height_offset=self.chase_height,
            )

        elif self.current_mode == CameraMode.ORBIT:
            # Circular orbit around drone
            ox = dx + self.orbit_radius * math.cos(self.orbit_angle)
            oy = dy + self.orbit_radius * math.sin(self.orbit_angle)
            return CameraState(
                x=ox, y=oy,
                zoom=1.0,
                rotation=0.0,
                target_x=dx, target_y=dy,
                fov=55.0,
                height_offset=2.0,
            )

        elif self.current_mode == CameraMode.FREE:
            return CameraState(
                x=self.state.x,
                y=self.state.y,
                zoom=self.state.zoom,
                rotation=0.0,
                target_x=dx, target_y=dy,
                fov=60.0,
                height_offset=0.0,
            )

        elif self.current_mode == CameraMode.CINEMATIC:
            return self._get_cinematic_state()

        elif self.current_mode == CameraMode.TOP_VIEW:
            return CameraState(
                x=self.view_width / 2,
                y=self.view_height / 2,
                zoom=1.2,
                rotation=0.0,
                target_x=dx, target_y=dy,
                fov=45.0,
                height_offset=20.0,
            )

        elif self.current_mode == CameraMode.SIDE_VIEW:
            sx = dx + self.chase_distance * math.cos(heading + math.pi / 2)
            sy = dy + self.chase_distance * math.sin(heading + math.pi / 2)
            return CameraState(
                x=sx, y=sy,
                zoom=1.0,
                rotation=heading - math.pi / 2,
                target_x=dx, target_y=dy,
                fov=50.0,
                height_offset=1.0,
            )

        elif self.current_mode == CameraMode.TRACKING:
            # Fixed tracking from a distance
            return CameraState(
                x=dx + 10, y=dy + 8,
                zoom=1.3,
                rotation=0.0,
                target_x=dx, target_y=dy,
                fov=55.0,
                height_offset=3.0,
            )

        elif self.current_mode == CameraMode.REPLAY:
            # High angle overview
            return CameraState(
                x=dx, y=dy,
                zoom=0.5,
                rotation=0.0,
                target_x=dx, target_y=dy,
                fov=70.0,
                height_offset=15.0,
            )

        # Default: chase
        return CameraState(x=dx - 8, y=dy - 8, zoom=1.0)

    def _update_mode_specific(self, dt: float):
        """Update mode-specific parameters each frame."""
        if self.current_mode == CameraMode.ORBIT:
            self.orbit_angle += self.orbit_speed * dt
            if self.orbit_angle > 2 * math.pi:
                self.orbit_angle -= 2 * math.pi

        elif self.current_mode == CameraMode.CINEMATIC:
            self.cinematic_time += dt

        elif self.current_mode == CameraMode.REPLAY:
            # Slow zoom out for dramatic effect
            self.state.zoom = max(0.3, self.state.zoom - 0.02 * dt)

    def _init_cinematic_path(self):
        """Initialize a pre-programmed cinematic camera path."""
        # Create a figure-8 path
        path = []
        for i in range(101):
            t = i / 100.0
            angle = t * 2 * math.pi
            cx = 50 + 20 * math.sin(angle)
            cy = 50 + 15 * math.sin(angle * 2)
            zoom = 0.8 + 0.4 * math.sin(angle * 3)
            path.append((cx, cy, zoom))
        self.cinematic_path = path

    def _get_cinematic_state(self) -> CameraState:
        """Get camera state along the cinematic path."""
        if not self.cinematic_path:
            return CameraState(x=50, y=50, zoom=1.0)

        # Cycle through path based on time
        cycle_time = 15.0  # seconds to complete full path
        t = (self.cinematic_time % cycle_time) / cycle_time
        idx = int(t * len(self.cinematic_path))
        idx = min(idx, len(self.cinematic_path) - 1)
        cx, cy, zoom = self.cinematic_path[idx]

        return CameraState(
            x=cx, y=cy,
            zoom=zoom,
            rotation=0.0,
            target_x=self.tracked_x,
            target_y=self.tracked_y,
            fov=60.0,
            height_offset=2.0,
        )

    def cycle_mode(self, direction: int = 1):
        """Cycle to next/previous camera mode."""
        modes = list(CameraMode)
        current_idx = modes.index(self.current_mode)
        next_idx = (current_idx + direction) % len(modes)
        self.set_mode(modes[next_idx])

    def get_mode_name(self) -> str:
        """Return human-readable mode name."""
        names = {
            CameraMode.PILOT_VIEW: "PILOT VIEW",
            CameraMode.FPV: "FPV",
            CameraMode.CHASE: "CHASE",
            CameraMode.ORBIT: "ORBIT",
            CameraMode.FREE: "FREE CAMERA",
            CameraMode.CINEMATIC: "CINEMATIC",
            CameraMode.TOP_VIEW: "TOP VIEW",
            CameraMode.SIDE_VIEW: "SIDE VIEW",
            CameraMode.TRACKING: "TRACKING",
            CameraMode.REPLAY: "REPLAY",
        }
        return names.get(self.current_mode, "UNKNOWN")

    def get_mode_color(self) -> str:
        """Return a colour associated with the current mode."""
        colors = {
            CameraMode.PILOT_VIEW: "#38BDF8",
            CameraMode.FPV: "#22C55E",
            CameraMode.CHASE: "#F59E0B",
            CameraMode.ORBIT: "#8B5CF6",
            CameraMode.FREE: "#EC4899",
            CameraMode.CINEMATIC: "#EF4444",
            CameraMode.TOP_VIEW: "#06B6D4",
            CameraMode.SIDE_VIEW: "#84CC16",
            CameraMode.TRACKING: "#14B8A6",
            CameraMode.REPLAY: "#F97316",
        }
        return colors.get(self.current_mode, "#FFFFFF")
