"""Mission Control Workspace System.

Provides a fully customizable, drag-and-drop, resizable, dockable widget system
for the MJN Drone Premium Dashboard. Supports Unreal Engine / VS Code / Blender
style workspace management.
"""

from .widget_base import (
    Widget, WidgetState, WidgetConfig, WidgetGeometry, ResizeHandle, ThemePreset,
    WorldMapWidget, TelemetryWidget, BatteryWidget,
)
from .workspace_manager import WorkspaceGrid, DragDropEngine
from .command_palette import CommandPalette, Command
from .layout_profiles import LayoutManager, LayoutProfile
from .graph_registry import GraphRegistry, GraphWidget, GraphSpec
from .theme_manager import ThemeManager
from .workspace import MissionControlWorkspace
from .brain_integration import BrainIntegration, build_mission_snapshot

__all__ = [
    "Widget", "WidgetState", "WidgetConfig", "WidgetGeometry", "ResizeHandle", "ThemePreset",
    "WorldMapWidget", "TelemetryWidget", "BatteryWidget",
    "WorkspaceGrid", "DragDropEngine",
    "CommandPalette", "Command",
    "LayoutManager", "LayoutProfile",
    "GraphRegistry", "GraphWidget", "GraphSpec",
    "ThemeManager",
    "MissionControlWorkspace",
    "BrainIntegration",
    "build_mission_snapshot",
]
