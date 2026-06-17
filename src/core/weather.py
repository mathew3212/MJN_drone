"""
Military-Grade Weather & Atmospheric Simulation System
========================================================
Dynamic weather with wind fields, precipitation, fog,
day/night cycle, and atmospheric effects.

Provides real-time weather state for rendering and physics.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import numpy as np


# ── Weather Types ────────────────────────────────────────────────────────────


class WeatherType(Enum):
    """Supported weather conditions."""
    CLEAR = auto()
    CLOUDY = auto()
    OVERCAST = auto()
    RAIN = auto()
    HEAVY_RAIN = auto()
    FOG = auto()
    SNOW = auto()
    STORM = auto()
    SANDSTORM = auto()


class TimeOfDay(Enum):
    """Day/night cycle phases."""
    DAWN = auto()
    MORNING = auto()
    NOON = auto()
    AFTERNOON = auto()
    DUSK = auto()
    NIGHT = auto()
    MIDNIGHT = auto()
    PRE_DAWN = auto()


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class WindState:
    """Current wind conditions."""
    speed: float = 2.0        # m/s
    direction: float = 0.0    # radians (0 = east, pi/2 = north)
    gust_strength: float = 0.0
    turbulence: float = 0.1   # 0-1

    @property
    def dx(self) -> float:
        return math.cos(self.direction) * self.speed

    @property
    def dy(self) -> float:
        return math.sin(self.direction) * self.speed


@dataclass
class PrecipitationState:
    """Current precipitation."""
    intensity: float = 0.0   # 0-1
    particle_count: int = 0
    particle_positions: list[tuple[float, float]] = field(default_factory=list)
    particle_velocities: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class AtmosphericState:
    """Lighting and atmospheric conditions."""
    sun_angle: float = 0.0           # radians above horizon
    sun_direction: tuple[float, float] = (0.5, 0.5)  # normalized 2D
    ambient_light: float = 1.0       # 0-1
    fog_density: float = 0.0         # 0-1
    fog_color: tuple[float, float, float] = (0.5, 0.5, 0.6)
    cloud_cover: float = 0.0         # 0-1
    cloud_positions: list[tuple[float, float, float]] = field(default_factory=list)
    temperature: float = 20.0        # celsius
    humidity: float = 0.5            # 0-1
    visibility: float = 1.0          # 0-1 (1 = full visibility)
    time_of_day: TimeOfDay = TimeOfDay.NOON
    day_progress: float = 0.5        # 0-1 (0 = midnight, 0.5 = noon)


@dataclass
class ParticleEffect:
    """A visual particle effect (smoke, dust, explosion)."""
    x: float
    y: float
    vx: float
    vy: float
    life: float = 1.0
    max_life: float = 1.0
    size: float = 2.0
    color: tuple[float, float, float] = (0.5, 0.5, 0.5)
    alpha: float = 0.7
    effect_type: str = "dust"


# ── Wind Field ───────────────────────────────────────────────────────────────


class WindField:
    """Spatially-varying wind field for realistic atmospheric simulation."""

    def __init__(self, width: int = 100, height: int = 100):
        self.width = width
        self.height = height
        self.base_wind = WindState(speed=3.0, direction=0.0)
        self._variation = np.zeros((height, width, 2), dtype=np.float32)
        self._generate_field()

    def _generate_field(self) -> None:
        """Generate spatial wind variation."""
        rng = random.Random(42)
        for y in range(self.height):
            for x in range(self.width):
                # Perlin-like variation
                vx = math.sin(x * 0.1 + rng.uniform(0, 0.5)) * 0.3
                vy = math.cos(y * 0.1 + rng.uniform(0, 0.5)) * 0.3
                self._variation[y, x] = [vx, vy]

    def get_wind_at(self, x: float, y: float) -> WindState:
        """Get wind at a specific position."""
        ix = max(0, min(self.width - 1, int(x)))
        iy = max(0, min(self.height - 1, int(y)))
        vx = self.base_wind.dx + self._variation[iy, ix, 0]
        vy = self.base_wind.dy + self._variation[iy, ix, 1]
        speed = math.sqrt(vx * vx + vy * vy)
        direction = math.atan2(vy, vx)
        return WindState(
            speed=speed,
            direction=direction,
            turbulence=self.base_wind.turbulence,
        )

    def update(self, dt: float = 1.0) -> None:
        """Slowly shift wind patterns over time."""
        self.base_wind.direction += random.uniform(-0.02, 0.02)
        self.base_wind.speed = max(
            0, self.base_wind.speed + random.uniform(-0.1, 0.1)
        )
        self.base_wind.speed = min(15.0, self.base_wind.speed)


# ── Weather System ───────────────────────────────────────────────────────────


class WeatherSystem:
    """Dynamic weather simulation for military drone operations.

    Simulates:
      - Day/night cycle with sun position
      - Wind fields with spatial variation
      - Precipitation (rain, snow)
      - Fog and visibility
      - Cloud movement
      - Particle effects (dust, smoke)
    """

    def __init__(self, width: int = 100, height: int = 100,
                 seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed

        # Time
        self.sim_time: float = 0.0
        self.day_speed: float = 0.002  # Day cycle speed (radians per tick)

        # Weather state
        self.weather_type: WeatherType = WeatherType.CLEAR
        self.wind = WindField(width, height)
        self.precipitation = PrecipitationState()
        self.atmosphere = AtmosphericState()
        self.cloud_positions: list[list[float]] = []

        # Particle effects
        self.particles: list[ParticleEffect] = []

        # Weather zones (areas with different weather)
        self.weather_zones: list[dict] = []

        # Transition
        self._target_weather: Optional[WeatherType] = None
        self._transition_progress: float = 0.0

        # Initialize clouds
        self._init_clouds()

    def _init_clouds(self) -> None:
        """Generate initial cloud positions."""
        rng = random.Random(self.seed + 500)
        self.cloud_positions = [
            [
                rng.uniform(0, self.width),
                rng.uniform(self.height * 0.6, self.height * 0.95),
                rng.uniform(3.0, 8.0),  # size
                rng.uniform(0.3, 0.7),  # opacity
            ]
            for _ in range(25)
        ]

    def update(self, dt: float = 1.0) -> None:
        """Update all weather systems."""
        self.sim_time += dt

        # Day/night cycle
        self._update_day_night(dt)

        # Wind evolution
        self.wind.update(dt)

        # Cloud movement
        self._update_clouds(dt)

        # Precipitation
        self._update_precipitation(dt)

        # Fog
        self._update_fog(dt)

        # Particles
        self._update_particles(dt)

    def _update_day_night(self, dt: float) -> None:
        """Advance day/night cycle."""
        self.atmosphere.day_progress += self.day_speed * dt
        if self.atmosphere.day_progress >= 1.0:
            self.atmosphere.day_progress -= 1.0

        # Sun angle: 0 at midnight, pi/2 at noon
        self.atmosphere.sun_angle = (
            math.sin(self.atmosphere.day_progress * math.pi * 2 - math.pi / 2)
            * math.pi / 2
        )

        # Determine time of day
        p = self.atmosphere.day_progress
        if p < 0.05:
            self.atmosphere.time_of_day = TimeOfDay.PRE_DAWN
        elif p < 0.15:
            self.atmosphere.time_of_day = TimeOfDay.DAWN
        elif p < 0.3:
            self.atmosphere.time_of_day = TimeOfDay.MORNING
        elif p < 0.45:
            self.atmosphere.time_of_day = TimeOfDay.NOON
        elif p < 0.6:
            self.atmosphere.time_of_day = TimeOfDay.AFTERNOON
        elif p < 0.75:
            self.atmosphere.time_of_day = TimeOfDay.DUSK
        elif p < 0.9:
            self.atmosphere.time_of_day = TimeOfDay.NIGHT
        else:
            self.atmosphere.time_of_day = TimeOfDay.MIDNIGHT

        # Ambient light (sinusoidal)
        sun_elev = max(0, math.sin(self.atmosphere.day_progress * math.pi * 2 - math.pi / 2))
        self.atmosphere.ambient_light = 0.15 + 0.85 * sun_elev

        # Sun direction
        angle = self.atmosphere.day_progress * math.pi * 2
        self.atmosphere.sun_direction = (
            math.cos(angle),
            math.sin(angle),
        )

        # Temperature varies with time
        base_temp = 25.0
        self.atmosphere.temperature = (
            base_temp - 10 * math.cos(self.atmosphere.day_progress * math.pi * 2)
        )

    def _update_clouds(self, dt: float) -> None:
        """Move clouds and update coverage."""
        wind = self.wind.base_wind
        for cloud in self.cloud_positions:
            cloud[0] += wind.dx * 0.05 * dt
            cloud[1] += wind.dy * 0.02 * dt

            # Wrap around
            if cloud[0] > self.width + 10:
                cloud[0] = -10
            elif cloud[0] < -10:
                cloud[0] = self.width + 10

        self.atmosphere.cloud_cover = min(1.0, len(self.cloud_positions) / 30.0)

    def _update_precipitation(self, dt: float) -> None:
        """Update rain/snow particles."""
        if self.weather_type in (WeatherType.RAIN, WeatherType.HEAVY_RAIN, WeatherType.STORM):
            self._update_rain(dt)
        elif self.weather_type == WeatherType.SNOW:
            self._update_snow(dt)
        else:
            self.precipitation.particle_positions.clear()
            self.precipitation.particle_velocities.clear()
            self.precipitation.intensity = 0.0

    def _update_rain(self, dt: float) -> None:
        """Simulate rain particles."""
        if self.weather_type == WeatherType.HEAVY_RAIN:
            self.precipitation.intensity = 0.8 + 0.2 * random.random()
            target_count = 150
        elif self.weather_type == WeatherType.STORM:
            self.precipitation.intensity = 1.0
            target_count = 200
        else:
            self.precipitation.intensity = 0.3 + 0.2 * random.random()
            target_count = 80

        self.precipitation.particle_count = target_count
        wind = self.wind.base_wind

        # Add new particles
        while len(self.precipitation.particle_positions) < target_count:
            x = random.uniform(0, self.width)
            y = random.uniform(self.height * 0.5, self.height)
            self.precipitation.particle_positions.append((x, y))
            vx = wind.dx * 0.1 + random.uniform(-0.2, 0.2)
            vy = -random.uniform(3.0, 6.0)  # Rain falls downward in screen coords
            self.precipitation.particle_velocities.append((vx, vy))

        # Update existing
        new_positions = []
        new_velocities = []
        for i, (x, y) in enumerate(self.precipitation.particle_positions):
            if i < len(self.precipitation.particle_velocities):
                vx, vy = self.precipitation.particle_velocities[i]
            else:
                vx, vy = 0, -4
            x += vx * dt
            y += vy * dt
            if 0 <= y < self.height and 0 <= x < self.width:
                new_positions.append((x, y))
                new_velocities.append((vx + wind.dx * 0.01, vy))

        self.precipitation.particle_positions = new_positions
        self.precipitation.particle_velocities = new_velocities

    def _update_snow(self, dt: float) -> None:
        """Simulate snow particles."""
        self.precipitation.intensity = 0.3 + 0.1 * random.random()
        target_count = 60
        wind = self.wind.base_wind

        while len(self.precipitation.particle_positions) < target_count:
            x = random.uniform(0, self.width)
            y = random.uniform(self.height * 0.6, self.height)
            self.precipitation.particle_positions.append((x, y))
            vx = random.uniform(-0.5, 0.5)
            vy = -random.uniform(0.5, 1.5)
            self.precipitation.particle_velocities.append((vx, vy))

        new_positions = []
        new_velocities = []
        for i, (x, y) in enumerate(self.precipitation.particle_positions):
            if i < len(self.precipitation.particle_velocities):
                vx, vy = self.precipitation.particle_velocities[i]
            else:
                vx, vy = 0, -1
            x += (vx + wind.dx * 0.05) * dt
            y += vy * dt
            if 0 <= y < self.height and 0 <= x < self.width:
                new_positions.append((x, y))
                new_velocities.append((vx + random.uniform(-0.05, 0.05), vy))

        self.precipitation.particle_positions = new_positions
        self.precipitation.particle_velocities = new_velocities

    def _update_fog(self, dt: float) -> None:
        """Update fog density and visibility."""
        if self.weather_type == WeatherType.FOG:
            self.atmosphere.fog_density = 0.6 + 0.2 * math.sin(self.sim_time * 0.05)
            self.atmosphere.visibility = 0.3
        elif self.weather_type == WeatherType.SANDSTORM:
            self.atmosphere.fog_density = 0.7
            self.atmosphere.visibility = 0.2
        elif self.weather_type in (WeatherType.HEAVY_RAIN, WeatherType.STORM):
            self.atmosphere.fog_density = 0.3
            self.atmosphere.visibility = 0.5
        else:
            self.atmosphere.fog_density = max(
                0.0, self.atmosphere.fog_density - 0.01 * dt
            )
            self.atmosphere.visibility = min(
                1.0, self.atmosphere.visibility + 0.01 * dt
            )

    def _update_particles(self, dt: float) -> None:
        """Update visual particle effects (dust, smoke, etc.)."""
        alive = []
        for p in self.particles:
            p.life -= dt / p.max_life
            if p.life > 0:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.alpha = max(0, p.alpha - 0.02 * dt)
                p.size *= 1.02
                alive.append(p)
        self.particles = alive

    # ── Public API ──────────────────────────────────────────────────────

    def set_weather(self, weather: WeatherType) -> None:
        """Set weather type."""
        self.weather_type = weather
        if weather in (WeatherType.HEAVY_RAIN, WeatherType.STORM):
            self.wind.base_wind.speed = 8.0
            self.wind.base_wind.gust_strength = 4.0
        elif weather == WeatherType.SANDSTORM:
            self.wind.base_wind.speed = 12.0
            self.wind.base_wind.gust_strength = 6.0
        elif weather == WeatherType.CLEAR:
            self.wind.base_wind.speed = 2.0
            self.wind.base_wind.gust_strength = 0.0

    def spawn_dust(self, x: float, y: float, count: int = 10) -> None:
        """Spawn dust particles at position."""
        for _ in range(count):
            self.particles.append(ParticleEffect(
                x=x + random.uniform(-2, 2),
                y=y + random.uniform(-2, 2),
                vx=random.uniform(-0.5, 0.5),
                vy=random.uniform(0.2, 0.8),
                life=1.0,
                max_life=random.uniform(1.0, 3.0),
                size=random.uniform(1.0, 3.0),
                color=(0.6, 0.5, 0.3),
                alpha=0.5,
                effect_type="dust",
            ))

    def spawn_smoke(self, x: float, y: float, count: int = 15) -> None:
        """Spawn smoke particles at position."""
        for _ in range(count):
            self.particles.append(ParticleEffect(
                x=x + random.uniform(-1, 1),
                y=y + random.uniform(-1, 1),
                vx=random.uniform(-0.3, 0.3),
                vy=random.uniform(0.5, 1.5),
                life=1.0,
                max_life=random.uniform(2.0, 5.0),
                size=random.uniform(2.0, 5.0),
                color=(0.4, 0.4, 0.4),
                alpha=0.6,
                effect_type="smoke",
            ))

    def spawn_explosion(self, x: float, y: float, count: int = 30) -> None:
        """Spawn explosion particles at position."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 4.0)
            self.particles.append(ParticleEffect(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=1.0,
                max_life=random.uniform(0.5, 2.0),
                size=random.uniform(1.0, 4.0),
                color=(
                    random.uniform(0.8, 1.0),
                    random.uniform(0.3, 0.7),
                    0.0,
                ),
                alpha=0.9,
                effect_type="explosion",
            ))

    def get_sky_color(self) -> tuple[float, float, float]:
        """Get current sky/background color based on time of day."""
        p = self.atmosphere.day_progress
        # Sky gradient: dark blue at night, light blue at day, orange at dawn/dusk
        if 0.15 < p < 0.6:  # Daytime
            brightness = 0.15 + 0.1 * math.sin((p - 0.15) / 0.45 * math.pi)
            return (brightness * 0.8, brightness, brightness * 1.2)
        elif 0.05 < p < 0.15:  # Dawn
            t = (p - 0.05) / 0.1
            return (0.1 + 0.05 * t, 0.05 + 0.1 * t, 0.08 + 0.12 * t)
        elif 0.6 < p < 0.75:  # Dusk
            t = (p - 0.6) / 0.15
            return (0.15 - 0.08 * t, 0.15 - 0.1 * t, 0.2 - 0.12 * t)
        else:  # Night
            return (0.02, 0.02, 0.05)

    def get_wind_display(self) -> str:
        """Get human-readable wind status."""
        speed = self.wind.base_wind.speed
        if speed < 2:
            return "CALM"
        elif speed < 5:
            return "LIGHT"
        elif speed < 8:
            return "MODERATE"
        elif speed < 12:
            return "STRONG"
        return "SEVERE"

    def get_weather_display(self) -> str:
        """Get weather status string."""
        return self.weather_type.name.replace("_", " ")