"""
Living World Engine — Digital Twin Environment
================================================
A persistent virtual world that continuously exists and evolves.

Features:
  - World memory (previous flights, damaged areas, weather history)
  - Intelligent objects (vehicles obey roads, pedestrians avoid drones)
  - World evolution (traffic patterns change, weather affects terrain)
  - Dynamic obstacle generation based on events
  - Mission history tracking
  - Charging station awareness

The world never feels scripted — every moment is unique.
"""

from __future__ import annotations

import math
import random as _rand
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from collections import deque
from enum import Enum, auto

import numpy as np


class EntityType(Enum):
    VEHICLE = auto()
    PEDESTRIAN = auto()
    BIRD_FLOCK = auto()
    DELIVERY_DRONE = auto()
    CONSTRUCTION = auto()
    EMERGENCY = auto()


class EventSeverity(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class WorldEvent:
    """A dynamic event in the world."""
    event_type: str
    x: float
    y: float
    radius: float
    severity: EventSeverity
    duration: int  # steps remaining
    description: str
    affects_path: bool = True
    created_step: int = 0


@dataclass
class FlightRecord:
    """Record of a completed flight."""
    start_pos: Tuple[float, float]
    end_pos: Tuple[float, float]
    path: List[Tuple[float, float]]
    duration: int
    obstacles_encountered: int
    battery_used: float
    timestamp: float = 0.0


@dataclass
class WeatherState:
    """Current weather state with full parameters."""
    temperature: float = 22.0  # Celsius
    wind_speed: float = 2.0  # m/s
    wind_angle: float = 0.0  # radians
    humidity: float = 0.5
    visibility: float = 1.0  # 0-1
    precipitation: float = 0.0  # 0-1
    cloud_cover: float = 0.3  # 0-1
    fog_density: float = 0.0  # 0-1
    storm_intensity: float = 0.0  # 0-1
    dust_level: float = 0.0  # 0-1
    time_of_day: float = 0.5  # 0=midnight, 0.5=noon, 1=midnight
    day_count: int = 0

    def get_visibility_factor(self) -> float:
        """Compute effective visibility from all factors."""
        vis = self.visibility
        vis *= max(0.3, 1.0 - self.fog_density * 0.7)
        vis *= max(0.2, 1.0 - self.precipitation * 0.6)
        vis *= max(0.1, 1.0 - self.storm_intensity * 0.8)
        vis *= max(0.4, 1.0 - self.dust_level * 0.6)
        # Night reduces visibility
        night_factor = abs(math.cos(self.time_of_day * 2 * math.pi))
        vis *= max(0.3, night_factor)
        return max(0.1, min(1.0, vis))

    def get_battery_drain_modifier(self) -> float:
        """Battery drain modifier from weather."""
        mod = 1.0
        mod += self.wind_speed * 0.05
        mod += self.precipitation * 0.1
        mod += self.storm_intensity * 0.2
        # Cold weather reduces battery efficiency
        if self.temperature < 5:
            mod += (5 - self.temperature) * 0.02
        return mod

    def get_flight_speed_modifier(self) -> float:
        """Speed modifier from weather conditions."""
        mod = 1.0
        mod -= self.wind_speed * 0.03
        mod -= self.precipitation * 0.1
        mod -= self.storm_intensity * 0.3
        return max(0.3, mod)


class IntelligentObject:
    """Base class for objects with autonomous behavior."""

    def __init__(self, x: float, y: float, speed: float = 0.5):
        self.x = x
        self.y = y
        self.speed = speed
        self.heading = _rand.uniform(0, 2 * math.pi)
        self.active = True
        self.state = "IDLE"

    def update(self, world_width: int, world_height: int, 
               drone_pos: Optional[Tuple[float, float]] = None,
               obstacles: Optional[Set] = None):
        pass


class SmartVehicle(IntelligentObject):
    """Vehicle that obeys roads, stops at intersections, accelerates naturally."""

    def __init__(self, x, y, road_segments=None, speed=0.4):
        super().__init__(x, y, speed)
        self.road_segments = road_segments or []
        self.current_segment = 0
        self.acceleration = 0.0
        self.max_speed = speed
        self.target_speed = speed
        self.waiting = False
        self.wait_timer = 0
        self.color = _rand.choice(["#CC2222", "#2266CC", "#CCCCCC", "#222222", "#FFFFFF"])
        self.vehicle_type = _rand.choice(["car", "truck", "van"])

    def update(self, world_width, world_height, drone_pos=None, obstacles=None):
        if self.wait_timer > 0:
            self.wait_timer -= 1
            return

        # Natural acceleration/deceleration
        if self.speed < self.target_speed:
            self.speed = min(self.target_speed, self.speed + 0.02)
        elif self.speed > self.target_speed:
            self.speed = max(self.target_speed, self.speed - 0.03)

        # Move along heading
        self.x += math.cos(self.heading) * self.speed
        self.y += math.sin(self.heading) * self.speed

        # Boundary wrapping
        if self.x < -5: self.x = world_width + 5
        if self.x > world_width + 5: self.x = -5
        if self.y < -5: self.y = world_height + 5
        if self.y > world_height + 5: self.y = -5

        # Random turns
        if _rand.random() < 0.02:
            self.heading += _rand.uniform(-0.3, 0.3)

        # Stop near drone
        if drone_pos:
            dist = math.hypot(drone_pos[0] - self.x, drone_pos[1] - self.y)
            if dist < 5:
                self.target_speed = 0
                self.wait_timer = _rand.randint(10, 30)
            else:
                self.target_speed = self.max_speed


class SmartPedestrian(IntelligentObject):
    """Pedestrian that walks, avoids drones, crosses roads."""

    def __init__(self, x, y, speed=0.15):
        super().__init__(x, y, speed)
        self.wander_timer = _rand.randint(30, 100)
        self.avoiding_drone = False
        self.clothing_color = _rand.choice([
            "#6A8AD4", "#D46A8A", "#8AD46A", "#D4A46A",
            "#8A6AD4", "#D4D46A", "#6AD4D4", "#D48A6A",
        ])

    def update(self, world_width, world_height, drone_pos=None, obstacles=None):
        # Avoid drone if too close
        if drone_pos:
            dist = math.hypot(drone_pos[0] - self.x, drone_pos[1] - self.y)
            if dist < 8:
                # Walk away from drone
                away_angle = math.atan2(self.y - drone_pos[1], self.x - drone_pos[0])
                self.heading = away_angle + _rand.uniform(-0.3, 0.3)
                self.avoiding_drone = True
            else:
                self.avoiding_drone = False

        # Wander randomly
        self.wander_timer -= 1
        if self.wander_timer <= 0 and not self.avoiding_drone:
            self.heading += _rand.uniform(-0.8, 0.8)
            self.wander_timer = _rand.randint(30, 100)

        self.x += math.cos(self.heading) * self.speed
        self.y += math.sin(self.heading) * self.speed

        # Boundary reflection
        margin = 3
        if self.x < margin or self.x > world_width - margin:
            self.heading = math.pi - self.heading + _rand.uniform(-0.2, 0.2)
            self.x = max(margin, min(world_width - margin, self.x))
        if self.y < margin or self.y > world_height - margin:
            self.heading = -self.heading + _rand.uniform(-0.2, 0.2)
            self.y = max(margin, min(world_height - margin, self.y))


class BirdFlock(IntelligentObject):
    """Bird flock that flies in formation, avoids collisions."""

    def __init__(self, x, y, count=5):
        super().__init__(x, y, speed=0.8)
        self.count = count
        self.members = []
        for _ in range(count):
            mx = x + _rand.uniform(-3, 3)
            my = y + _rand.uniform(-3, 3)
            self.members.append((mx, my))
        self.circling = False
        self.circle_center = (x, y)
        self.circle_angle = 0.0

    def update(self, world_width, world_height, drone_pos=None, obstacles=None):
        # Avoid drone
        if drone_pos:
            dist = math.hypot(drone_pos[0] - self.x, drone_pos[1] - self.y)
            if dist < 12:
                away = math.atan2(self.y - drone_pos[1], self.x - drone_pos[0])
                self.heading = away
                self.speed = 1.2
            else:
                self.speed = 0.8
        else:
            self.speed = 0.8

        # Move flock center
        self.x += math.cos(self.heading) * self.speed
        self.y += math.sin(self.heading) * self.speed

        # Random heading changes
        if _rand.random() < 0.03:
            self.heading += _rand.uniform(-0.5, 0.5)

        # Update members to follow with slight offset
        for i in range(len(self.members)):
            angle = (2 * math.pi * i) / len(self.members)
            target_x = self.x + 2 * math.cos(angle + self.heading)
            target_y = self.y + 2 * math.sin(angle + self.heading)
            mx, my = self.members[i]
            self.members[i] = (mx + (target_x - mx) * 0.3, my + (target_y - my) * 0.3)

        # Boundary
        margin = 15
        if self.x < margin or self.x > world_width - margin:
            self.heading = math.pi - self.heading
        if self.y < margin or self.y > world_height - margin:
            self.heading = -self.heading


@dataclass
class SmartBuilding:
    """Building with full metadata for indoor/outdoor missions."""
    x: float
    y: float
    width: float
    height: float
    floors: int
    has_rooftop: bool = True
    has_landing_pad: bool = False
    has_loading_dock: bool = False
    has_elevator: bool = False
    has_entrance: bool = True
    delivery_zones: List[Tuple[float, float]] = field(default_factory=list)
    is_damaged: bool = False
    damage_level: float = 0.0
    power_status: str = "ON"  # ON, OFF, BACKUP
    occupancy: float = 0.5  # 0-1
    building_type: str = "commercial"  # commercial, residential, industrial, warehouse


class LivingWorld:
    """
    A persistent digital twin world that continuously evolves.
    
    Features:
      - History tracking (flights, events, weather)
      - Intelligent objects with autonomous behavior
      - Dynamic weather with real effects
      - World events that affect missions
      - Smart buildings with metadata
    """

    def __init__(self, width: int = 100, height: int = 100, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed
        _rand.seed(seed)

        # World state
        self.step_count: int = 0
        self.weather = WeatherState()
        self.events: List[WorldEvent] = []

        # History
        self.flight_history: List[FlightRecord] = []
        self.weather_history: deque = deque(maxlen=500)
        self.event_history: List[WorldEvent] = []
        self.delivery_count: int = 0
        self.missions_completed: int = 0

        # Intelligent objects
        self.vehicles: List[SmartVehicle] = []
        self.pedestrians: List[SmartPedestrian] = []
        self.bird_flocks: List[BirdFlock] = []

        # Smart buildings
        self.buildings: List[SmartBuilding] = []

        # Charging stations
        self.charging_stations: List[Tuple[float, float]] = []

        # Traffic patterns (updated based on time of day)
        self.traffic_density: float = 0.5
        self.pedestrian_density: float = 0.5

        # Initialize
        self._generate_smart_buildings()
        self._generate_vehicles(20)
        self._generate_pedestrians(30)
        self._generate_bird_flocks(5)
        self._generate_charging_stations()

    def _generate_smart_buildings(self):
        """Generate buildings with full metadata."""
        # City center area
        for bx in range(25, 55, 5):
            for by in range(25, 55, 5):
                floors = _rand.randint(1, 12)
                btype = _rand.choice([
                    "commercial", "commercial", "residential",
                    "industrial", "warehouse",
                ])
                bld = SmartBuilding(
                    x=float(bx), y=float(by),
                    width=_rand.uniform(2, 4), height=_rand.uniform(2, 4),
                    floors=floors,
                    has_rooftop=floors >= 3,
                    has_landing_pad=floors >= 5 and _rand.random() < 0.4,
                    has_loading_dock=btype == "warehouse",
                    has_elevator=floors >= 4,
                    building_type=btype,
                    occupancy=_rand.uniform(0.1, 0.9),
                )
                if bld.has_landing_pad:
                    bld.delivery_zones.append((bx + 1, by + 1))
                self.buildings.append(bld)

        # Industrial zone
        for ix in range(70, 90, 6):
            for iy in range(70, 90, 5):
                bld = SmartBuilding(
                    x=float(ix), y=float(iy),
                    width=_rand.uniform(3, 5), height=_rand.uniform(3, 5),
                    floors=1, building_type="warehouse",
                    has_loading_dock=True,
                    has_landing_pad=_rand.random() < 0.3,
                    delivery_zones=[(ix + 2, iy + 2)],
                )
                self.buildings.append(bld)

    def _generate_vehicles(self, count: int):
        """Generate smart vehicles on road network."""
        for _ in range(count):
            x = _rand.uniform(5, self.width - 5)
            y = _rand.uniform(5, self.height - 5)
            speed = _rand.uniform(0.2, 0.6)
            vehicle = SmartVehicle(x, y, speed=speed)
            vehicle.heading = _rand.uniform(0, 2 * math.pi)
            self.vehicles.append(vehicle)

    def _generate_pedestrians(self, count: int):
        """Generate smart pedestrians."""
        for _ in range(count):
            x = _rand.uniform(3, self.width - 3)
            y = _rand.uniform(3, self.height - 3)
            ped = SmartPedestrian(x, y, speed=_rand.uniform(0.08, 0.2))
            self.pedestrians.append(ped)

    def _generate_bird_flocks(self, count: int):
        """Generate bird flocks."""
        for _ in range(count):
            x = _rand.uniform(10, self.width - 10)
            y = _rand.uniform(10, self.height - 10)
            flock = BirdFlock(x, y, count=_rand.randint(3, 8))
            self.bird_flocks.append(flock)

    def _generate_charging_stations(self):
        """Generate charging stations at building rooftops."""
        for bld in self.buildings:
            if bld.has_landing_pad and _rand.random() < 0.3:
                self.charging_stations.append(
                    (bld.x + bld.width / 2, bld.y + bld.height / 2)
                )
        # Add some ground stations
        for _ in range(3):
            x = _rand.uniform(10, self.width - 10)
            y = _rand.uniform(10, self.height - 10)
            self.charging_stations.append((x, y))

    def update(self, drone_pos: Optional[Tuple[float, float]] = None):
        """Update the living world one step."""
        self.step_count += 1

        # Update weather (gradual changes)
        self._update_weather()

        # Update traffic based on time of day
        self._update_traffic()

        # Update intelligent objects
        for v in self.vehicles:
            v.update(self.width, self.height, drone_pos)
        for p in self.pedestrians:
            p.update(self.width, self.height, drone_pos)
        for f in self.bird_flocks:
            f.update(self.width, self.height, drone_pos)

        # Update events
        self._update_events()

        # Randomly generate new events
        if _rand.random() < 0.005:
            self._generate_random_event()

        # Record weather
        if self.step_count % 10 == 0:
            self.weather_history.append(WeatherState(
                temperature=self.weather.temperature,
                wind_speed=self.weather.wind_speed,
                visibility=self.weather.get_visibility_factor(),
                precipitation=self.weather.precipitation,
            ))

    def _update_weather(self):
        """Gradually evolve weather."""
        w = self.weather
        # Slow temperature drift
        w.temperature += _rand.uniform(-0.1, 0.1)
        w.temperature = max(-10, min(40, w.temperature))

        # Wind gusts
        w.wind_speed += _rand.uniform(-0.1, 0.1)
        w.wind_speed = max(0, min(15, w.wind_speed))
        w.wind_angle += _rand.uniform(-0.05, 0.05)

        # Precipitation
        w.precipitation += _rand.uniform(-0.01, 0.01)
        w.precipitation = max(0, min(1, w.precipitation))

        # Fog
        w.fog_density += _rand.uniform(-0.005, 0.005)
        w.fog_density = max(0, min(0.8, w.fog_density))

        # Storm
        if _rand.random() < 0.001:
            w.storm_intensity = min(1, w.storm_intensity + 0.1)
        else:
            w.storm_intensity = max(0, w.storm_intensity - 0.005)

        # Day/night cycle
        w.time_of_day += 0.001
        if w.time_of_day >= 1.0:
            w.time_of_day -= 1.0
            w.day_count += 1

    def _update_traffic(self):
        """Adjust traffic based on time of day."""
        hour = self.weather.time_of_day * 24
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            self.traffic_density = 0.9
            self.pedestrian_density = 0.8
        elif 10 <= hour <= 16:
            self.traffic_density = 0.6
            self.pedestrian_density = 0.5
        elif 20 <= hour <= 23:
            self.traffic_density = 0.3
            self.pedestrian_density = 0.2
        else:
            self.traffic_density = 0.1
            self.pedestrian_density = 0.1

    def _update_events(self):
        """Update active events."""
        for event in self.events[:]:
            event.duration -= 1
            if event.duration <= 0:
                self.events.remove(event)

    def _generate_random_event(self):
        """Generate a random world event."""
        event_types = [
            ("CONSTRUCTION", "Road construction", EventSeverity.MEDIUM, 200, 8),
            ("ROAD_CLOSURE", "Road closed for maintenance", EventSeverity.HIGH, 500, 6),
            ("FALLEN_TREE", "Tree fallen on road", EventSeverity.LOW, 100, 3),
            ("POWER_OUTAGE", "Power outage in area", EventSeverity.MEDIUM, 300, 4),
            ("VEHICLE_ACCIDENT", "Vehicle accident", EventSeverity.HIGH, 400, 5),
            ("NO_FLY_ZONE", "Temporary no-fly zone", EventSeverity.CRITICAL, 600, 10),
            ("CROWDED_AREA", "Crowded area event", EventSeverity.LOW, 200, 7),
            ("WIND_ZONE", "Strong wind zone", EventSeverity.MEDIUM, 400, 4),
            ("SMOKE", "Smoke from fire", EventSeverity.HIGH, 350, 5),
            ("EMERGENCY", "Emergency landing request", EventSeverity.CRITICAL, 500, 3),
        ]

        etype, desc, severity, radius, duration = _rand.choice(event_types)
        x = _rand.uniform(10, self.width - 10)
        y = _rand.uniform(10, self.height - 10)

        event = WorldEvent(
            event_type=etype, x=x, y=y,
            radius=radius / 10, severity=severity,
            duration=duration, description=desc,
            affects_path=severity in (EventSeverity.HIGH, EventSeverity.CRITICAL),
            created_step=self.step_count,
        )
        self.events.append(event)
        self.event_history.append(event)

    def record_flight(self, record: FlightRecord):
        """Record a completed flight."""
        self.flight_history.append(record)
        self.missions_completed += 1

    def get_nearest_charging_station(self, x: float, y: float) -> Optional[Tuple[float, float]]:
        """Find nearest charging station."""
        if not self.charging_stations:
            return None
        return min(self.charging_stations, key=lambda s: math.hypot(s[0] - x, s[1] - y))

    def get_weather_effects(self) -> Dict:
        """Get current weather effects as a dictionary."""
        return {
            "visibility_factor": self.weather.get_visibility_factor(),
            "battery_drain_mod": self.weather.get_battery_drain_modifier(),
            "speed_mod": self.weather.get_flight_speed_modifier(),
            "wind_dx": self.weather.wind_speed * math.cos(self.weather.wind_angle),
            "wind_dy": self.weather.wind_speed * math.sin(self.weather.wind_angle),
            "turbulence": self.weather.storm_intensity * 2 + self.weather.wind_speed * 0.1,
            "precipitation": self.weather.precipitation,
            "temperature": self.weather.temperature,
        }

    def is_in_event_zone(self, x: float, y: float) -> List[WorldEvent]:
        """Check if position is inside any event zone."""
        affected = []
        for event in self.events:
            dist = math.hypot(event.x - x, event.y - y)
            if dist < event.radius:
                affected.append(event)
        return affected