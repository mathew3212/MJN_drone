"""
Theme Manager
=============
Professional theme switching for the Mission Control Workspace.

Supports:
  - Dark (default)
  - Light
  - Midnight
  - Blueprint
  - Graphite
  - Arctic
  - Operator
  - Custom theme editor
"""

from __future__ import annotations

import copy
from typing import Dict, Optional, Any
from enum import Enum

from .widget_base import ThemePreset


# Professional color themes
THEMES: Dict[ThemePreset, Dict[str, str]] = {
    ThemePreset.DARK: {
        "bg_dark": "#05070B", "bg_panel": "#0B0E14", "bg_inner": "#11151F",
        "bg_card": "#0D1019", "border": "#1A2035", "border_glow": "#00D4FF",
        "primary": "#00D4FF", "secondary": "#9D6CFF", "success": "#00FF88",
        "warning": "#FFC857", "danger": "#FF4D5A", "info": "#06B6D4",
        "text_main": "#FFFFFF", "text_value": "#E8EDFF", "text_label": "#6B7FA0",
        "text_dim": "#4A5A78", "accent": "#00D4FF",
    },
    ThemePreset.LIGHT: {
        "bg_dark": "#F5F7FA", "bg_panel": "#FFFFFF", "bg_inner": "#F0F2F5",
        "bg_card": "#E8ECF0", "border": "#D0D5DD", "border_glow": "#0066CC",
        "primary": "#0066CC", "secondary": "#7C3AED", "success": "#059669",
        "warning": "#D97706", "danger": "#DC2626", "info": "#0891B2",
        "text_main": "#111827", "text_value": "#374151", "text_label": "#6B7280",
        "text_dim": "#9CA3AF", "accent": "#0066CC",
    },
    ThemePreset.MIDNIGHT: {
        "bg_dark": "#020617", "bg_panel": "#0F172A", "bg_inner": "#1E293B",
        "bg_card": "#172033", "border": "#334155", "border_glow": "#38BDF8",
        "primary": "#38BDF8", "secondary": "#818CF8", "success": "#34D399",
        "warning": "#FBBF24", "danger": "#F87171", "info": "#22D3EE",
        "text_main": "#F1F5F9", "text_value": "#E2E8F0", "text_label": "#94A3B8",
        "text_dim": "#64748B", "accent": "#38BDF8",
    },
    ThemePreset.BLUEPRINT: {
        "bg_dark": "#0A1929", "bg_panel": "#0D253F", "bg_inner": "#132F4C",
        "bg_card": "#102A43", "border": "#1E3A5F", "border_glow": "#64B5F6",
        "primary": "#64B5F6", "secondary": "#42A5F5", "success": "#81C784",
        "warning": "#FFB74D", "danger": "#E57373", "info": "#4FC3F7",
        "text_main": "#E3F2FD", "text_value": "#BBDEFB", "text_label": "#90CAF9",
        "text_dim": "#64B5F6", "accent": "#64B5F6",
    },
    ThemePreset.GRAPHITE: {
        "bg_dark": "#0F0F0F", "bg_panel": "#1A1A1A", "bg_inner": "#242424",
        "bg_card": "#1E1E1E", "border": "#333333", "border_glow": "#888888",
        "primary": "#CCCCCC", "secondary": "#999999", "success": "#4CAF50",
        "warning": "#FF9800", "danger": "#F44336", "info": "#2196F3",
        "text_main": "#EEEEEE", "text_value": "#CCCCCC", "text_label": "#999999",
        "text_dim": "#666666", "accent": "#CCCCCC",
    },
    ThemePreset.ARCTIC: {
        "bg_dark": "#E8F4F8", "bg_panel": "#FFFFFF", "bg_inner": "#F0F8FF",
        "bg_card": "#E6F2FF", "border": "#B0D4E8", "border_glow": "#0077B6",
        "primary": "#0077B6", "secondary": "#023E8A", "success": "#2D6A4F",
        "warning": "#B8860B", "danger": "#9D4EDD", "info": "#0096C7",
        "text_main": "#03045E", "text_value": "#1D3557", "text_label": "#457B9D",
        "text_dim": "#A8DADC", "accent": "#0077B6",
    },
    ThemePreset.OPERATOR: {
        "bg_dark": "#0C0C0C", "bg_panel": "#141414", "bg_inner": "#1C1C1C",
        "bg_card": "#181818", "border": "#2A2A2A", "border_glow": "#FF6600",
        "primary": "#FF6600", "secondary": "#FFAA00", "success": "#00CC66",
        "warning": "#FFD700", "danger": "#FF0044", "info": "#00CCFF",
        "text_main": "#FFFFFF", "text_value": "#FFEEDD", "text_label": "#AA8866",
        "text_dim": "#665544", "accent": "#FF6600",
    },
}


class ThemeManager:
    """Manages theme switching and custom themes."""

    def __init__(self):
        self._current: ThemePreset = ThemePreset.DARK
        self._custom: Dict[str, str] = {}
        self._history: list = []

    def get_colors(self) -> Dict[str, str]:
        if self._custom:
            return {**THEMES[self._current], **self._custom}
        return dict(THEMES[self._current])

    def get_color(self, key: str) -> str:
        colors = self.get_colors()
        return colors.get(key, "#FFFFFF")

    def set_theme(self, preset: ThemePreset):
        self._history.append(self._current)
        self._current = preset
        self._custom = {}

    def apply_custom(self, overrides: Dict[str, str]):
        self._custom.update(overrides)

    def reset_custom(self):
        self._custom = {}

    def export_theme(self) -> Dict[str, Any]:
        return {
            "preset": self._current.value,
            "custom": dict(self._custom),
            "colors": self.get_colors(),
        }

    def import_theme(self, data: Dict[str, Any]):
        preset = data.get("preset", "dark")
        try:
            self._current = ThemePreset(preset)
        except ValueError:
            self._current = ThemePreset.DARK
        self._custom = dict(data.get("custom", {}))

    def list_presets(self) -> list:
        return [(p.value, p.name.title()) for p in ThemePreset]

    def get_current_preset(self) -> ThemePreset:
        return self._current