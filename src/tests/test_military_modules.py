"""
Comprehensive Tests for Military Drone Simulation Modules
==========================================================
Tests for terrain, weather, enhanced world, and military visualization.
"""

import math
import pytest
import numpy as np

from src.core.terrain import (
    TerrainGenerator, TerrainType, PerlinNoise2D,
    Structure, WaterBody, Road,
)
from src.core.weather import (
    WeatherSystem, WeatherType, TimeOfDay,
    WindState, WindField, PrecipitationState,
    AtmosphericState, ParticleEffect,
)
from src.core.enhanced_world import (
    EnhancedWorld, MilitaryZone, Convoy,
)
from src.core.world import World, DynamicObstacle


# ══════════════════════════════════════════════════════════════════════════════
# Terrain Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestPerlinNoise:
    def test_noise_range(self):
        n = PerlinNoise2D(seed=42, scale=0.1)
        for x in range(0, 100, 5):
            for y in range(0, 100, 5):
                val = n.noise(x, y)
                assert -1.5 <= val <= 1.5, f"Noise out of range: {val}"

    def test_octave_noise_deterministic(self):
        n1 = PerlinNoise2D(seed=42, scale=0.1)
        n2 = PerlinNoise2D(seed=42, scale=0.1)
        for x in range(10):
            for y in range(10):
                assert n1.octave_noise(x, y) == pytest.approx(n2.octave_noise(x, y))

    def test_different_seeds_differ(self):
        n1 = PerlinNoise2D(seed=42, scale=0.08)
        n2 = PerlinNoise2D(seed=99, scale=0.08)
        vals1 = [n1.octave_noise(x + 1.5, y + 1.5) for x in range(0, 20, 2) for y in range(0, 20, 2)]
        vals2 = [n2.octave_noise(x + 1.5, y + 1.5) for x in range(0, 20, 2) for y in range(0, 20, 2)]
        assert vals1 != vals2


class TestTerrainGenerator:
    def test_generate_basic(self):
        tg = TerrainGenerator(50, 50, seed=42)
        data = tg.generate()
        assert "height_map" in data
        assert "terrain_types" in data
        assert "structures" in data
        assert "tree_positions" in data
        assert "obstacle_positions" in data
        assert data["height_map"].shape == (50, 50)
        assert data["terrain_types"].shape == (50, 50)

    def test_height_map_range(self):
        tg = TerrainGenerator(50, 50)
        tg.generate()
        assert tg.height_map.min() >= 0.0
        assert tg.height_map.max() <= 1.0

    def test_terrain_types_valid(self):
        tg = TerrainGenerator(50, 50)
        tg.generate()
        valid = {tt.value for tt in TerrainType}
        for y in range(50):
            for x in range(50):
                assert tg.terrain_types[y, x] in valid

    def test_structures_created(self):
        tg = TerrainGenerator(100, 100, seed=42)
        tg.generate()
        assert len(tg.structures) > 0
        for s in tg.structures:
            assert s.x >= 0
            assert s.y >= 0
            assert s.width > 0
            assert s.height > 0

    def test_trees_created(self):
        tg = TerrainGenerator(100, 100, seed=42)
        tg.generate()
        assert len(tg.tree_positions) > 0
        for x, y in tg.tree_positions:
            assert 0 <= x < 100
            assert 0 <= y < 100

    def test_obstacle_positions_comprehensive(self):
        tg = TerrainGenerator(50, 50)
        tg.generate()
        assert len(tg.obstacle_positions) > 0

    def test_get_terrain_type(self):
        tg = TerrainGenerator(50, 50)
        tg.generate()
        tt = tg.get_terrain_type(0, 0)
        assert isinstance(tt, TerrainType)
        # Out of bounds returns FLAT_GROUND
        assert tg.get_terrain_type(-1, -1) == TerrainType.FLAT_GROUND

    def test_get_height(self):
        tg = TerrainGenerator(50, 50)
        tg.generate()
        h = tg.get_height(25, 25)
        assert 0.0 <= h <= 1.0
        # Out of bounds returns 0
        assert tg.get_height(-1, -1) == 0.0

    def test_is_walkable(self):
        tg = TerrainGenerator(50, 50)
        tg.generate()
        # Out of bounds is not walkable
        assert not tg.is_walkable(-1, -1)

    def test_terrain_colors(self):
        tg = TerrainGenerator(50, 50)
        tg.generate()
        c = tg.get_terrain_color(0, 0)
        assert len(c) == 3
        assert all(0 <= v <= 1 for v in c)
        # Out of bounds
        c2 = tg.get_terrain_color(-1, -1)
        assert c2 == (0.1, 0.1, 0.1)

    def test_terrain_color_array(self):
        tg = TerrainGenerator(50, 50)
        tg.generate()
        arr = tg.get_terrain_color_array()
        assert arr.shape == (50, 50, 3)
        assert arr.dtype == np.float32

    def test_water_bodies(self):
        tg = TerrainGenerator(100, 100, seed=42)
        tg.generate()
        assert isinstance(tg.water_bodies, list)

    def test_roads(self):
        tg = TerrainGenerator(100, 100, seed=42)
        tg.generate()
        assert len(tg.roads) > 0
        for r in tg.roads:
            assert r.road_type in ("dirt", "paved", "highway")

    def test_difficulty_affects_trees(self):
        tg_easy = TerrainGenerator(100, 100, seed=42, difficulty="easy")
        tg_normal = TerrainGenerator(100, 100, seed=42, difficulty="normal")
        tg_easy.generate()
        tg_normal.generate()
        # Easy mode has more trees (higher density)
        assert len(tg_easy.tree_positions) >= len(tg_normal.tree_positions)


# ══════════════════════════════════════════════════════════════════════════════
# Weather Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestWindState:
    def test_defaults(self):
        w = WindState()
        assert w.speed == 2.0
        assert w.direction == 0.0

    def test_dx_dy(self):
        w = WindState(speed=5.0, direction=0)
        assert w.dx == pytest.approx(5.0)
        assert w.dy == pytest.approx(0.0)

    def test_direction_pi2(self):
        w = WindState(speed=5.0, direction=math.pi / 2)
        assert w.dx == pytest.approx(0.0, abs=0.01)
        assert w.dy == pytest.approx(5.0, abs=0.01)


class TestWindField:
    def test_creation(self):
        wf = WindField(50, 50)
        assert wf.base_wind.speed == 3.0

    def test_wind_at_position(self):
        wf = WindField(50, 50)
        w = wf.get_wind_at(25, 25)
        assert isinstance(w, WindState)
        assert w.speed >= 0

    def test_update_shifts(self):
        wf = WindField(50, 50)
        d1 = wf.base_wind.direction
        for _ in range(100):
            wf.update(1.0)
        # Should have shifted
        assert wf.base_wind.direction != d1


class TestWeatherSystem:
    def test_creation(self):
        ws = WeatherSystem(50, 50)
        assert ws.weather_type == WeatherType.CLEAR
        assert ws.sim_time == 0

    def test_update_advances_time(self):
        ws = WeatherSystem(50, 50)
        ws.update(1.0)
        assert ws.sim_time == 1.0

    def test_day_night_cycle(self):
        ws = WeatherSystem(50, 50)
        ws.update(1.0)
        assert 0 <= ws.atmosphere.day_progress <= 1.0
        assert isinstance(ws.atmosphere.time_of_day, TimeOfDay)

    def test_set_weather_clear(self):
        ws = WeatherSystem(50, 50)
        ws.set_weather(WeatherType.CLEAR)
        assert ws.weather_type == WeatherType.CLEAR
        assert ws.wind.base_wind.speed == 2.0

    def test_set_weather_storm(self):
        ws = WeatherSystem(50, 50)
        ws.set_weather(WeatherType.STORM)
        assert ws.wind.base_wind.speed == 8.0

    def test_set_weather_sandstorm(self):
        ws = WeatherSystem(50, 50)
        ws.set_weather(WeatherType.SANDSTORM)
        assert ws.wind.base_wind.speed == 12.0

    def test_rain_particles(self):
        ws = WeatherSystem(50, 50)
        ws.set_weather(WeatherType.RAIN)
        ws.update(5)
        assert len(ws.precipitation.particle_positions) > 0
        assert ws.precipitation.intensity > 0

    def test_snow_particles(self):
        ws = WeatherSystem(50, 50)
        ws.set_weather(WeatherType.SNOW)
        ws.update(5)
        assert len(ws.precipitation.particle_positions) > 0

    def test_fog_visibility(self):
        ws = WeatherSystem(50, 50)
        ws.set_weather(WeatherType.FOG)
        ws.update(1)
        assert ws.atmosphere.fog_density > 0.1
        assert ws.atmosphere.visibility < 0.5

    def test_sky_color(self):
        ws = WeatherSystem(50, 50)
        sky = ws.get_sky_color()
        assert len(sky) == 3
        assert all(0 <= v <= 1 for v in sky)

    def test_wind_display(self):
        ws = WeatherSystem(50, 50)
        assert ws.get_wind_display() in ("CALM", "LIGHT", "MODERATE", "STRONG", "SEVERE")

    def test_weather_display(self):
        ws = WeatherSystem(50, 50)
        assert ws.get_weather_display() == "CLEAR"

    def test_spawn_dust(self):
        ws = WeatherSystem(50, 50)
        ws.spawn_dust(25, 25, count=10)
        assert len(ws.particles) == 10

    def test_spawn_smoke(self):
        ws = WeatherSystem(50, 50)
        ws.spawn_smoke(25, 25, count=5)
        assert len(ws.particles) == 5

    def test_spawn_explosion(self):
        ws = WeatherSystem(50, 50)
        ws.spawn_explosion(25, 25, count=20)
        assert len(ws.particles) == 20

    def test_particles_decay(self):
        ws = WeatherSystem(50, 50)
        ws.spawn_dust(25, 25, count=5)
        initial = len(ws.particles)
        for _ in range(200):
            ws.update(1.0)
        assert len(ws.particles) < initial

    def test_cloud_movement(self):
        ws = WeatherSystem(50, 50)
        initial_pos = [c[0] for c in ws.cloud_positions[:5]]
        ws.wind.base_wind.speed = 5.0
        for _ in range(10):
            ws.update(1.0)
        new_pos = [c[0] for c in ws.cloud_positions[:5]]
        # At least some clouds should have moved
        assert any(abs(a - b) > 0.01 for a, b in zip(initial_pos, new_pos))

    def test_temperature_varies(self):
        ws = WeatherSystem(50, 50)
        temps = []
        for _ in range(50):
            ws.update(10)
            temps.append(ws.atmosphere.temperature)
        assert len(set([round(t, 1) for t in temps])) > 1

    def test_clear_resets_precipitation(self):
        ws = WeatherSystem(50, 50)
        ws.set_weather(WeatherType.RAIN)
        ws.update(5)
        assert len(ws.precipitation.particle_positions) > 0
        ws.set_weather(WeatherType.CLEAR)
        ws.update(5)
        assert ws.precipitation.intensity == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Enhanced World Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestEnhancedWorld:
    def test_creation(self):
        ew = EnhancedWorld(50, 50, 30)
        assert ew.width == 50
        assert ew.height == 50
        assert hasattr(ew, "terrain")
        assert hasattr(ew, "weather")

    def test_inherits_world(self):
        ew = EnhancedWorld(50, 50, 30)
        assert isinstance(ew, World)

    def test_backward_compatible(self):
        ew = EnhancedWorld(50, 50, 30)
        # World interface still works
        assert hasattr(ew, "obstacles")
        assert hasattr(ew, "dynamic_obstacles")
        assert hasattr(ew, "is_obstacle")
        assert hasattr(ew, "update")
        assert hasattr(ew, "width")
        assert hasattr(ew, "height")

    def test_military_zones(self):
        ew = EnhancedWorld(100, 100, 50)
        assert len(ew.military_zones) > 0
        types = {z.zone_type for z in ew.military_zones}
        assert "landing" in types or "restricted" in types or "mission" in types

    def test_enemy_drones(self):
        ew = EnhancedWorld(100, 100, 50)
        assert len(ew.enemy_drones) > 0
        for d in ew.enemy_drones:
            assert isinstance(d, DynamicObstacle)

    def test_convoys(self):
        ew = EnhancedWorld(100, 100, 50)
        assert len(ew.convoys) >= 0
        for c in ew.convoys:
            assert isinstance(c, Convoy)
            assert len(c.positions) > 0

    def test_terrain_data(self):
        ew = EnhancedWorld(50, 50, 30)
        assert ew.terrain_data is not None
        assert "height_map" in ew.terrain_data

    def test_update(self):
        ew = EnhancedWorld(50, 50, 30)
        ew.update()
        assert ew.frame_count == 1

    def test_get_weather_state(self):
        ew = EnhancedWorld(50, 50, 30)
        ws = ew.get_weather_state()
        assert "type" in ws
        assert "wind_speed" in ws
        assert "time_of_day" in ws

    def test_get_military_zone_at(self):
        ew = EnhancedWorld(50, 50, 30)
        # Place drone in middle
        if ew.military_zones:
            zone = ew.military_zones[0]
            found = ew.get_military_zone_at(zone.x, zone.y)
            assert found is not None

    def test_get_military_zone_outside(self):
        ew = EnhancedWorld(50, 50, 30)
        # Check a position far from all zones
        found = ew.get_military_zone_at(-999, -999)
        assert found is None

    def test_obstacle_categories(self):
        ew = EnhancedWorld(50, 50, 30)
        assert len(ew.obstacle_categories) > 0
        for pos, cat in list(ew.obstacle_categories.items())[:10]:
            assert cat in ("building", "tree", "water", "rock", "terrain", "convoy")

    def test_get_wind_at(self):
        ew = EnhancedWorld(50, 50, 30)
        w = ew.get_wind_at(25, 25)
        assert isinstance(w, WindState)

    def test_get_terrain_type_at(self):
        ew = EnhancedWorld(50, 50, 30)
        tt = ew.get_terrain_type_at(0, 0)
        assert isinstance(tt, TerrainType)

    def test_get_all_dynamic_positions(self):
        ew = EnhancedWorld(50, 50, 30)
        positions = ew.get_all_dynamic_positions()
        assert isinstance(positions, list)

    def test_full_update_cycle(self):
        ew = EnhancedWorld(50, 50, 30)
        for i in range(10):
            ew.update()
        assert ew.frame_count == 10
        # Weather should be advancing
        assert ew.weather.sim_time > 0


class TestMilitaryZone:
    def test_creation(self):
        z = MilitaryZone(x=10, y=10, radius=5, zone_type="landing")
        assert z.x == 10
        assert z.zone_type == "landing"


class TestConvoy:
    def test_creation(self):
        c = Convoy(positions=[(1, 1), (2, 1)], direction=(1, 0))
        assert len(c.positions) == 2
        assert c.convoy_type == "vehicle"


# ══════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    def test_enhanced_world_with_original_world(self):
        """Verify EnhancedWorld works anywhere World is expected."""
        ew = EnhancedWorld(50, 50, 30)
        # This simulates what main.py does
        assert ew.is_obstacle(0, 0) or not ew.is_obstacle(0, 0)  # no crash

    def test_world_update_with_enhanced(self):
        ew = EnhancedWorld(50, 50, 30)
        # Simulate several update cycles
        for _ in range(5):
            ew.update()
        # Should not crash

    def test_terrain_obstacle_merge(self):
        ew = EnhancedWorld(50, 50, 30)
        # Terrain obstacles should be in the obstacles set
        terrain_obs = ew.terrain_data["obstacle_positions"]
        for pos in list(terrain_obs)[:20]:
            assert pos in ew.obstacles

    def test_weather_and_terrain_interplay(self):
        ew = EnhancedWorld(50, 50, 30)
        ew.weather.set_weather(WeatherType.STORM)
        ew.update()
        ws = ew.get_weather_state()
        assert ws["type"] == WeatherType.STORM


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])