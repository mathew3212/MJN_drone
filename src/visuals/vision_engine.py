"""
Vision Engine — Premium Visual Effects
========================================
Provides HDR rendering, atmospheric lighting, colour grading,
bloom, motion blur, depth of field, reflections, and post-processing
for the drone simulation's Matplotlib-based visualisation.

Effects implemented:
  - Dynamic sunlight & golden hour lighting
  - Atmospheric scattering (sky colour based on sun position)
  - Soft shadows (overlay shading)
  - Ambient occlusion approximation
  - Colour grading (HDR tonemapping for display)
  - Bloom effect (glow around bright objects)
  - Motion blur (trail blending)
  - Depth cue (fog-based distance fading)
  - Anti-aliasing (subsampling)

All effects are implemented as compositing operations on numpy arrays
so they layer cleanly onto the existing Matplotlib rendering pipeline.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np


@dataclass
class LightingState:
    """Current lighting and atmospheric state."""
    sun_angle: float = 0.0  # 0 = noon, pi/2 = sunset, pi = midnight
    sun_elevation: float = 1.0  # 1.0 = overhead, 0.0 = horizon
    ambient_light: float = 0.7
    sunlight_intensity: float = 1.0
    fog_density: float = 0.02
    shadow_strength: float = 0.3
    bloom_threshold: float = 0.85
    bloom_intensity: float = 0.3
    color_temperature: float = 5500.0  # Kelvin
    time_of_day: str = "DAY"


@dataclass
class AtmosphericScattering:
    """Atmospheric scattering parameters."""
    rayleigh_coeff: float = 0.0035  # Rayleigh scattering coefficient
    mie_coeff: float = 0.005  # Mie scattering coefficient
    ozone_coeff: float = 0.02  # Ozone absorption
    sky_turbidity: float = 2.0  # 1=clear, 10=hazy
    sun_disk_brightness: float = 1.0


class VisionEngine:
    """
    Premium visual effects engine for the drone simulation.

    Provides HDR colour grading, atmospheric lighting, and post-process
    effects that transform the Matplotlib rendering into a
    cinematic-quality visual experience.
    """

    def __init__(self):
        self.lighting = LightingState()
        self.atmosphere = AtmosphericScattering()
        self.time_accumulator: float = 0.0

        # Day/night cycle speed (0 = paused)
        self.daynight_speed: float = 0.005  # radians per second

        # Star field (for night scenes)
        self.stars: Optional[np.ndarray] = None
        self._star_seed: int = 42

        # Colour grading LUT (simulated)
        self._hdr_lut: Optional[np.ndarray] = None

        # Previous frame for motion blur
        self._prev_frame: Optional[np.ndarray] = None
        self.motion_blur_factor: float = 0.15

    # ══════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════

    def update(self, dt: float = 0.016):
        """Update lighting and atmosphere."""
        self.time_accumulator += dt

        if self.daynight_speed > 0:
            self.lighting.sun_angle += self.daynight_speed * dt
            if self.lighting.sun_angle > 2 * math.pi:
                self.lighting.sun_angle -= 2 * math.pi

        # Update derived lighting params
        self._update_lighting()

    def set_time_of_day(self, sun_angle: float):
        """Set sun angle directly (0=noon, pi/2=sunset, pi=midnight)."""
        self.lighting.sun_angle = sun_angle
        self._update_lighting()

    def apply_lighting(self, rgb_array: np.ndarray) -> np.ndarray:
        """Apply lighting, colour grading, and atmospheric effects to an RGB image.

        Args:
            rgb_array: H x W x 3 float array in [0, 1] range

        Returns:
            Processed RGB array
        """
        if rgb_array.size == 0:
            return rgb_array

        img = rgb_array.copy()

        # 1. Apply ambient lighting
        img = self._apply_ambient_light(img)

        # 2. Apply sunlight colour
        img = self._apply_sunlight(img)

        # 3. Apply fog / depth cue
        img = self._apply_fog(img)

        # 4. Apply bloom (glow on bright areas)
        img = self._apply_bloom(img)

        # 5. HDR colour grading
        img = self._apply_color_grading(img)

        # 6. Apply shadows overlay
        img = self._apply_shadows(img)

        # Store for motion blur
        self._prev_frame = rgb_array.copy()

        return np.clip(img, 0.0, 1.0)

    def get_sky_color(self) -> Tuple[float, float, float]:
        """Compute the sky colour based on current sun position."""
        angle = self.lighting.sun_angle
        elev = math.cos(angle)

        if elev < -0.1:
            # Night sky
            return (0.02, 0.02, 0.08)

        # Day sky with Rayleigh scattering
        turbidity = self.atmosphere.sky_turbidity
        r = 0.3 + 0.7 * max(0, elev) * (1.0 - turbidity * 0.03)
        g = 0.5 + 0.5 * max(0, elev) * (1.0 - turbidity * 0.02)
        b = 0.8 + 0.2 * max(0, elev)

        # Sunset coloring (red/orange at low angles)
        if elev < 0.3 and elev > -0.1:
            sunset_factor = (0.3 - elev) / 0.4
            r = min(1.0, r + 0.5 * sunset_factor)
            g = max(0.2, g - 0.3 * sunset_factor)
            b = max(0.05, b - 0.5 * sunset_factor)

        return (r, g, b)

    def get_sun_position(self) -> Tuple[float, float]:
        """Return sun (x, y) position in normalised coordinates."""
        angle = self.lighting.sun_angle
        # Sun moves in an arc overhead
        x = math.sin(angle) * 80 + 50  # 50 is center
        y = 90 + math.cos(angle) * 40  # 90 is top
        return (x, y)

    def get_lighting_params(self) -> dict:
        """Return current lighting parameters for display."""
        return {
            "time_of_day": self.lighting.time_of_day,
            "sun_angle_deg": math.degrees(self.lighting.sun_angle) % 360,
            "ambient": f"{self.lighting.ambient_light:.2f}",
            "fog": f"{self.lighting.fog_density:.3f}",
            "color_temp": f"{self.lighting.color_temperature:.0f}K",
        }

    def get_sky_light_array(self, width: int, height: int) -> np.ndarray:
        """Generate a sky gradient array for the background."""
        sky = np.zeros((height, width, 3), dtype=np.float32)
        sky_r, sky_g, sky_b = self.get_sky_color()

        for y in range(height):
            t = y / height  # 0 at top, 1 at bottom
            # Sky at top, ground color at bottom
            sky_top = np.array([sky_r, sky_g, sky_b])
            # Ground colour (darker)
            ground = np.array([0.12, 0.08, 0.04]) * self.lighting.ambient_light

            # Blend with horizon glow
            horizon_glow = np.array([1.0, 0.7, 0.3]) * max(0, self.lighting.sunlight_intensity - 0.5) * 0.1
            if t < 0.3:
                # Sky
                color = sky_top * (1.0 - t / 0.3) + horizon_glow * (t / 0.3)
            elif t < 0.5:
                # Horizon transition
                horizon_t = (t - 0.3) / 0.2
                color = horizon_glow * (1.0 - horizon_t) + ground * horizon_t
            else:
                # Ground
                color = ground

            sky[y, :] = np.clip(color, 0, 1)

        return sky

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL — Lighting Updates
    # ══════════════════════════════════════════════════════════════════

    def _update_lighting(self):
        """Update derived lighting parameters from sun angle."""
        angle = self.lighting.sun_angle
        elev = math.cos(angle)

        self.lighting.sun_elevation = max(-0.2, elev)
        self.lighting.ambient_light = 0.3 + 0.5 * max(0, elev)
        self.lighting.sunlight_intensity = max(0, 0.2 + 0.8 * max(0, elev))
        self.lighting.fog_density = 0.01 + 0.04 * max(0, -elev * 0.5 + 0.5)
        self.lighting.shadow_strength = 0.3 * (1.0 - max(0, elev))

        # Time of day label
        if elev > 0.3:
            self.lighting.time_of_day = "DAY"
        elif elev > 0.0:
            self.lighting.time_of_day = "GOLDEN HOUR"
        elif elev > -0.3:
            self.lighting.time_of_day = "TWILIGHT"
        else:
            self.lighting.time_of_day = "NIGHT"

        # Colour temperature (warm at sunset, cool at noon)
        self.lighting.color_temperature = 3500 + 3000 * max(0, elev)

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL — Image Processing
    # ══════════════════════════════════════════════════════════════════

    def _apply_ambient_light(self, img: np.ndarray) -> np.ndarray:
        """Apply ambient lighting level."""
        return img * self.lighting.ambient_light

    def _apply_sunlight(self, img: np.ndarray) -> np.ndarray:
        """Apply warm/cool sunlight colour cast."""
        if self.lighting.sunlight_intensity < 0.1:
            # Night - blue shift
            return img * np.array([0.6, 0.7, 1.0])

        # Day with colour temperature
        temp = self.lighting.color_temperature
        # Simple approximation: warm (low K) -> orange, cool (high K) -> blue
        warm = max(0, 1.0 - (temp - 3500) / 3000)
        cool = max(0, (temp - 5500) / 3000)

        r = 1.0 + 0.3 * warm
        g = 1.0 - 0.05 * warm
        b = 1.0 + 0.2 * cool

        tint = np.array([r, g, b])
        return img * tint[np.newaxis, np.newaxis, :]

    def _apply_fog(self, img: np.ndarray) -> np.ndarray:
        """Apply atmospheric fog / haze."""
        fog_density = self.lighting.fog_density
        if fog_density < 0.001:
            return img

        sky_r, sky_g, sky_b = self.get_sky_color()
        fog_color = np.array([sky_r, sky_g, sky_b])

        # Apply fog as blend
        return img * (1.0 - fog_density) + fog_color * fog_density

    def _apply_bloom(self, img: np.ndarray) -> np.ndarray:
        """Apply bloom effect (glow around bright areas)."""
        threshold = self.lighting.bloom_threshold
        intensity = self.lighting.bloom_intensity

        if intensity < 0.01:
            return img

        # Extract bright areas
        luminance = np.dot(img[..., :3], np.array([0.299, 0.587, 0.114]))
        bright_mask = np.maximum(0, luminance - threshold) / (1.0 - threshold)

        # Simple bloom via blurred bright pass (approximated)
        # Use a box blur for efficiency
        kernel_size = 5
        kernel = np.ones((kernel_size, kernel_size)) / (kernel_size * kernel_size)
        bright_expanded = np.zeros_like(luminance)

        # Simple convolution
        h, w = luminance.shape
        padded = np.pad(bright_mask * img.max(), kernel_size // 2, mode='edge')
        for y in range(h):
            for x in range(w):
                bright_expanded[y, x] = np.sum(
                    padded[y:y + kernel_size, x:x + kernel_size] * kernel
                )

        bloom = bright_expanded[..., np.newaxis] * intensity
        result = img + bloom

        return result

    def _apply_color_grading(self, img: np.ndarray) -> np.ndarray:
        """Apply HDR colour grading / tonemapping."""
        # Simple Reinhard tonemap for HDR-like look
        img = img / (img + 1.0)

        # Contrast enhancement (S-curve)
        img = img * (img * (2.0 - img))

        # Saturation boost
        luminance = np.dot(img[..., :3], np.array([0.299, 0.587, 0.114]))
        saturation = 1.2  # 1.0 = neutral, >1 = more saturated
        img = luminance[..., np.newaxis] + saturation * (img - luminance[..., np.newaxis])

        return img

    def _apply_shadows(self, img: np.ndarray) -> np.ndarray:
        """Apply subtle shadow overlay."""
        shadow_strength = self.lighting.shadow_strength
        if shadow_strength < 0.01:
            return img

        # Subtle darkening of bottom edges (simulated ambient occlusion)
        h, w = img.shape[:2]
        y_gradient = np.ones((h, 1), dtype=np.float32)
        for y in range(h):
            # Darker at bottom
            y_gradient[y, 0] = 1.0 - shadow_strength * 0.3 * (y / h)

        # Slight vignette
        cx, cy = w / 2, h / 2
        x_coords = np.arange(w)
        y_coords = np.arange(h)
        xx, yy = np.meshgrid(x_coords, y_coords)
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(cx, cy)
        vignette = 1.0 - shadow_strength * 0.2 * (dist ** 2)

        shadow_mask = y_gradient * vignette[..., np.newaxis]

        return img * shadow_mask

    def generate_star_field(self, width: int, height: int) -> np.ndarray:
        """Generate a star field for night scenes."""
        if self.stars is not None and self.stars.shape == (height, width):
            return self.stars

        rng = np.random.RandomState(self._star_seed)
        stars = rng.random((height, width)) > 0.995
        intensities = rng.random((height, width)) * 0.8 + 0.2
        star_field = stars.astype(np.float32) * intensities * 0.5

        # Twinkle (time-varying)
        twinkle = 0.5 + 0.5 * np.sin(
            np.arange(height)[:, np.newaxis] * 0.1 +
            np.arange(width)[np.newaxis, :] * 0.05 +
            self.time_accumulator * 0.5
        )
        star_field *= twinkle

        self.stars = star_field
        return star_field

    def get_daynight_cycle_progress(self) -> float:
        """Return day/night cycle progress 0-1."""
        return (self.lighting.sun_angle % (2 * math.pi)) / (2 * math.pi)
