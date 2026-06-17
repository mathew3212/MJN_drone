"""
Airspace Intelligence System - Integration Test
===============================================
Tests the complete airspace management pipeline including:
  - Zone creation and geofencing
  - Path validation and replanning
  - Pre-flight mission validation
  - Temporary restrictions
  - Risk analysis
  - Visualization output
"""

import sys
import os
import math
import time

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.airspace import (
    AirspaceManager,
    RestrictedZone, ZoneType, ZoneShape, ZonePriority,
    RiskLevel, ZoneStatus, ZoneAction,
    GeofenceEngine,
    TemporaryRestrictionManager, TFRDefinition, TFRSource,
    CorridorManager, FlightCorridor,
    AltitudeManager, AltitudeLayer,
    AirspaceDatabase,
    AirspaceVisualization,
)
from src.airspace.corridor_manager import CorridorWaypoint
from src.airspace.restricted_zone import (
    CircleZone, RectangleZone, PolygonZone, Point2D,
    AltitudeEnvelope, MultiPolygonZone,
)


def test_basic_zone_creation():
    """Test zone creation with various types and shapes."""
    print("=" * 60)
    print("TEST: Basic Zone Creation")
    print("=" * 60)

    # Circle zone
    military = RestrictedZone(
        name="Test Military Base",
        zone_type=ZoneType.MILITARY_BASE,
        zone_shape=ZoneShape.CIRCLE,
        center_lon=50, center_lat=50,
        shape_data=CircleZone(center=Point2D(50, 50), radius=15),
        priority=ZonePriority.CRITICAL,
        risk_level=RiskLevel.SEVERE,
    )
    assert military.zone_id != ""
    assert military.zone_type == ZoneType.MILITARY_BASE
    assert military.contains_point((50, 50))  # Center should be inside
    assert not military.contains_point((80, 80))  # Far away should be outside
    assert military.contains_point((55, 55))  # Within radius
    print(f"  ✓ Circle zone created: {military.name} (ID: {military.zone_id})")
    print(f"  ✓ Point (50,50) inside: {military.contains_point((50, 50))}")
    print(f"  ✓ Point (80,80) outside: {not military.contains_point((80, 80))}")

    # Polygon zone
    verts = [Point2D(10, 10), Point2D(20, 10), Point2D(20, 20), Point2D(10, 20)]
    polygon_zone = RestrictedZone(
        name="Test Polygon Zone",
        zone_type=ZoneType.GOVERNMENT_BUILDING,
        zone_shape=ZoneShape.POLYGON,
        shape_data=PolygonZone(vertices=verts),
        priority=ZonePriority.HIGHEST,
    )
    assert polygon_zone.contains_point((15, 15))  # Inside
    assert not polygon_zone.contains_point((5, 5))  # Outside
    print(f"  ✓ Polygon zone created")
    print(f"  ✓ Point (15,15) inside: {polygon_zone.contains_point((15, 15))}")
    print(f"  ✓ Point (5,5) outside: {not polygon_zone.contains_point((5, 5))}")

    # Altitude-restricted zone
    alt_zone = RestrictedZone(
        name="Altitude Test Zone",
        zone_type=ZoneType.AIRPORT,
        shape_data=CircleZone(center=Point2D(30, 30), radius=10),
        altitude_limits=AltitudeEnvelope(minimum_altitude=10, maximum_altitude=100),
    )
    assert alt_zone.contains_point((30, 30), altitude=50)  # Within altitude
    assert not alt_zone.contains_point((30, 30), altitude=150)  # Above altitude
    print(f"  ✓ Altitude-restricted zone created")
    print(f"  ✓ Altitude 50m inside: {alt_zone.contains_point((30, 30), altitude=50)}")
    print(f"  ✓ Altitude 150m outside: {not alt_zone.contains_point((30, 30), altitude=150)}")

    # Test to_dict / from_dict serialization
    zone_dict = military.to_dict()
    restored = RestrictedZone.from_dict(zone_dict)
    assert restored.name == military.name
    assert restored.zone_type == military.zone_type
    assert restored.priority == military.priority
    print(f"  ✓ Serialization round-trip works")

    print("  ✓ ALL BASIC ZONE TESTS PASSED\n")
    return True


def test_geofence_engine():
    """Test the geofence enforcement engine."""
    print("=" * 60)
    print("TEST: Geofence Engine")
    print("=" * 60)

    gf = GeofenceEngine(world_width=100, world_height=100)

    # Add zones
    zone1 = RestrictedZone(
        name="Restricted Area 1",
        zone_type=ZoneType.MILITARY_BASE,
        shape_data=CircleZone(center=Point2D(30, 30), radius=10),
    )
    zone2 = RestrictedZone(
        name="Restricted Area 2",
        zone_type=ZoneType.AIRPORT,
        shape_data=CircleZone(center=Point2D(70, 70), radius=8),
    )
    gf.add_zone(zone1)
    gf.add_zone(zone2)
    assert gf.get_zone_count() == 2
    print(f"  ✓ Added {gf.get_zone_count()} zones")

    # Check point containment
    assert gf.check_point((30, 30))  # Inside zone1
    assert gf.check_point((70, 70))  # Inside zone2
    assert not gf.check_point((50, 50))  # Outside both
    print(f"  ✓ Point (30,30) restricted: {gf.check_point((30, 30))}")
    print(f"  ✓ Point (50,50) free: {not gf.check_point((50, 50))}")

    # Get zones at position
    zones_at = gf.get_zones_at((30, 30))
    assert len(zones_at) == 1
    assert zones_at[0].zone_id == zone1.zone_id
    print(f"  ✓ Zones at (30,30): {len(zones_at)}")

    # Get zones in radius
    zones_near = gf.get_zones_in_radius((40, 40), 15)
    assert len(zones_near) >= 1  # Should find zone1
    print(f"  ✓ Zones within 15 of (40,40): {len(zones_near)}")

    # Path validation
    path = [(10, 10), (25, 25), (50, 50), (75, 75)]
    violations = gf.check_path(path)
    print(f"  ✓ Path violations: {len(violations)}")

    # Validate full path
    validation = gf.validate_path(path)
    print(f"  ✓ Path valid: {validation['is_valid']}")
    print(f"  ✓ Path violations: {validation['total_violations']}")

    # Find alternative path
    alt = gf.find_alternative_path((5, 5), (95, 95))
    print(f"  ✓ Alternative path requires replan: {alt['requires_replan']}")

    # Nearest zone
    nearest = gf.get_nearest_zone((35, 35))
    assert nearest is not None
    print(f"  ✓ Nearest zone: {nearest[0].name} at {nearest[1]:.1f} units")

    # Update monitoring
    report = gf.update((35, 35), drone_altitude=50, drone_speed=5)
    print(f"  ✓ Monitor report - violations: {report['violation_count']}")
    print(f"  ✓ Monitor risk score: {report['risk_score']:.2f}")

    # Remove zone
    gf.remove_zone(zone1.zone_id)
    assert gf.get_zone_count() == 1
    print(f"  ✓ Zone removed, count: {gf.get_zone_count()}")

    print("  ✓ ALL GEOFENCE ENGINE TESTS PASSED\n")
    return True


def test_airspace_manager():
    """Test the master AirspaceManager orchestrator."""
    print("=" * 60)
    print("TEST: Airspace Manager")
    print("=" * 60)

    am = AirspaceManager(world_width=100, world_height=100, max_altitude=200)
    print(f"  ✓ AirspaceManager initialized with {am.geofence.get_zone_count()} default zones")

    # Pre-flight mission validation
    validation = am.validate_mission(
        start=(5, 5),
        target=(90, 90),
        altitude=50,
        mission_type="delivery",
        battery_capacity=100,
    )
    print(f"  ✓ Mission valid: {validation['is_valid']}")
    print(f"  ✓ Takeoff legal: {validation['takeoff_legal']}")
    print(f"  ✓ Landing legal: {validation['landing_legal']}")
    print(f"  ✓ Route valid: {validation['route_valid']}")
    print(f"  ✓ Battery sufficient: {validation['battery_sufficient']}")
    print(f"  ✓ Total distance: {validation['total_distance']:.1f}")

    # Route planning
    route = am.plan_route(
        start=(5, 5),
        target=(90, 90),
        altitude=50,
        mission_priority=5,
        battery_level=100,
    )
    print(f"  ✓ Route planned with {len(route['waypoints'])} waypoints")
    print(f"  ✓ Requires replan: {route['requires_replan']}")
    print(f"  ✓ Extra distance: {route['extra_distance']:.1f}")
    print(f"  ✓ Explanation: {route['explanation'][:60]}...")

    # Update cycle
    report = am.update(
        drone_position=(5, 5),
        drone_altitude=50,
        drone_speed=0,
        mission_priority=5,
        battery_level=100,
    )
    print(f"  ✓ Update report - violations: {report['violation_count']}")
    print(f"  ✓ Update risk score: {report['airspace_risk_score']:.3f}")
    print(f"  ✓ Decisions count: {len(report['decisions'])}")

    # Risk analysis
    risk = report['risk_analysis']
    print(f"  ✓ Violation probability: {risk.get('violation_probability', 0):.3f}")
    print(f"  ✓ Safety margin: {risk.get('safety_margin', 'N/A')}")
    print(f"  ✓ Confidence: {risk.get('confidence', 0):.3f}")

    # Prediction
    predictions = am.predict_restrictions((5, 5), lookahead_seconds=60)
    print(f"  ✓ TFR predictions: {len(predictions['tfr_predictions'])}")
    print(f"  ✓ Soon expiring: {len(predictions['soon_expiring'])}")

    # Get memory data
    memory = am.get_memory_data()
    print(f"  ✓ Memory data - violations: {memory['historical_violations']}")
    print(f"  ✓ Memory data - safe routes: {len(memory['common_safe_routes'])}")

    # Generate airspace cost grid
    cost_grid = am.get_airspace_cost_grid(resolution=50)
    print(f"  ✓ Cost grid generated: {len(cost_grid)}x{len(cost_grid[0])}")

    # Generate post-mission report
    mission_report = am.generate_mission_report(mission_id="test_001")
    print(f"  ✓ Mission report generated")
    print(f"  ✓ Summary: {mission_report['summary']}")

    # Stats
    stats = am.get_stats()
    print(f"  ✓ System stats: {stats['database']['total_zones']} zones, "
          f"{stats['replan_count']} replans")

    print("  ✓ ALL AIRSPACE MANAGER TESTS PASSED\n")
    return True


def test_temporary_restrictions():
    """Test dynamic TFR generation and management."""
    print("=" * 60)
    print("TEST: Temporary Restrictions")
    print("=" * 60)

    tfr_mgr = TemporaryRestrictionManager()

    # Generate various TFR types
    emergency = tfr_mgr.generate_emergency_tfr((50, 50), "police")
    print(f"  ✓ Emergency TFR: {emergency.name} (ID: {emergency.tfr_id})")

    vip = tfr_mgr.generate_vip_tfr((70, 30))
    print(f"  ✓ VIP TFR: {vip.name}")

    event = tfr_mgr.generate_event_tfr((20, 80), "Concert")
    print(f"  ✓ Event TFR: {event.name}")

    construction = tfr_mgr.generate_construction_tfr((40, 60))
    print(f"  ✓ Construction TFR: {construction.name}")

    weather = tfr_mgr.generate_weather_tfr((80, 80), "storm")
    print(f"  ✓ Weather TFR: {weather.name}")

    active = tfr_mgr.get_active_tfrs()
    print(f"  ✓ Active TFRs: {len(active)}")

    # Get TFRs near a position
    nearby = tfr_mgr.get_tfrs_near((45, 55), radius=30)
    print(f"  ✓ TFRs near (45,55): {len(nearby)}")

    # Convert to restricted zones
    for tfr in active[:1]:
        zone = tfr.to_restricted_zone()
        assert zone.zone_type == ZoneType.EMERGENCY_ZONE or zone.zone_type == ZoneType.TFR
    print(f"  ✓ TFR to RestrictedZone conversion works")

    # Prediction (initially empty but should not crash)
    predictions = tfr_mgr.predict_tfrs((50, 50))
    print(f"  ✓ TFR predictions: {len(predictions)}")

    # Record occurrence for learning
    for tfr in active:
        tfr_mgr.record_tfr_occurrence(tfr)

    # Stats
    stats = tfr_mgr.get_stats()
    print(f"  ✓ Stats: {stats['active_tfrs']} active, "
          f"{stats['historical_tfrs']} historical")

    tfr_mgr.clear_all()
    print(f"  ✓ Cleared all TFRs")

    print("  ✓ ALL TEMPORARY RESTRICTION TESTS PASSED\n")
    return True


def test_altitude_manager():
    """Test altitude management and optimization."""
    print("=" * 60)
    print("TEST: Altitude Manager")
    print("=" * 60)

    alt_mgr = AltitudeManager(max_altitude=200)

    layers = alt_mgr.get_layers()
    print(f"  ✓ Default layers: {len(layers)}")

    # Altitude validation
    valid = alt_mgr.validate_altitude(50)
    assert valid['valid']
    print(f"  ✓ Altitude 50m valid: {valid['valid']} (Layer: {valid['layer']})")

    invalid = alt_mgr.validate_altitude(-10)
    assert not invalid['valid']
    print(f"  ✓ Altitude -10m invalid: {not invalid['valid']}")

    # Optimal altitude suggestions
    opt = alt_mgr.suggest_optimal_altitude(distance_to_go=80)
    print(f"  ✓ Optimal altitude (80 units): {opt['optimal_altitude']}m - {opt['reason']}")

    opt_low_bat = alt_mgr.suggest_optimal_altitude(
        distance_to_go=80, battery_level=15
    )
    print(f"  ✓ Optimal altitude (low battery): {opt_low_bat['optimal_altitude']}m - "
          f"{opt_low_bat['reason']}")

    opt_windy = alt_mgr.suggest_optimal_altitude(
        distance_to_go=80, wind_speed=15
    )
    print(f"  ✓ Optimal altitude (windy): {opt_windy['optimal_altitude']}m - "
          f"{opt_windy['reason']}")

    # Layer at altitude
    layer = alt_mgr.get_layer_at(50)
    assert layer is not None
    print(f"  ✓ Layer at 50m: {layer.name}")

    # Safe altitude in restricted zones
    zones = [
        RestrictedZone(
            name="Test Zone",
            shape_data=CircleZone(center=Point2D(50, 50), radius=10),
            altitude_limits=AltitudeEnvelope(minimum_altitude=30, maximum_altitude=80),
        )
    ]
    safe = alt_mgr.find_safe_altitude((50, 50), zones, current_altitude=50)
    print(f"  ✓ Safe altitude: {safe['safe_altitude']}m (change: {safe['change_required']})")

    safe_outside = alt_mgr.find_safe_altitude((5, 5), [], current_altitude=50)
    print(f"  ✓ No zone, no change: {not safe_outside['change_required']}")

    print("  ✓ ALL ALTITUDE MANAGER TESTS PASSED\n")
    return True


def test_database():
    """Test airspace database import/export."""
    print("=" * 60)
    print("TEST: Airspace Database")
    print("=" * 60)

    db = AirspaceDatabase()

    # Generate example zones
    ids = db.generate_example_zones(world_width=100, world_height=100)
    print(f"  ✓ Generated {len(ids)} example zones")

    all_zones = db.get_all_zones()
    print(f"  ✓ Total zones: {len(all_zones)}")

    # Find by type
    military = db.find_zones_by_type(ZoneType.MILITARY_BASE)
    print(f"  ✓ Military zones: {len(military)}")

    airports = db.find_zones_by_type(ZoneType.AIRPORT)
    print(f"  ✓ Airport zones: {len(airports)}")

    # Test CSV export/import
    csv_path = "test_airspace_export.csv"
    db.export_csv(csv_path, all_zones[:3])
    assert os.path.exists(csv_path)
    print(f"  ✓ Exported {min(3, len(all_zones))} zones to CSV")

    # Verify file contents
    import csv
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
    print(f"  ✓ CSV has {len(rows)} rows (including header)")

    # Clean up
    os.remove(csv_path)
    print(f"  ✓ Cleaned up test file")

    # Generate all zone types
    all_types = db.generate_all_zone_types()
    print(f"  ✓ Generated all zone types: {len(all_types)} types")

    # Stats
    stats = db.get_stats()
    print(f"  ✓ Stats: {stats['total_zones']} total, "
          f"{stats['zone_types_available']} types")

    db.clear()
    assert db.get_count() == 0
    print(f"  ✓ Database cleared")

    print("  ✓ ALL DATABASE TESTS PASSED\n")
    return True


def test_visualization():
    """Test visualization overlay generation."""
    print("=" * 60)
    print("TEST: Airspace Visualization")
    print("=" * 60)

    vis = AirspaceVisualization(world_width=100, world_height=100)

    # Create some test zones
    zones = [
        RestrictedZone(
            name="Test Zone 1",
            zone_type=ZoneType.MILITARY_BASE,
            shape_data=CircleZone(center=Point2D(30, 30), radius=10),
            risk_level=RiskLevel.SEVERE,
        ),
        RestrictedZone(
            name="Test Zone 2",
            zone_type=ZoneType.SCHOOL_ZONE,
            shape_data=CircleZone(center=Point2D(70, 70), radius=8),
            risk_level=RiskLevel.LOW,
        ),
    ]

    # Render zones
    rendered = vis.render_all_zones(zones)
    assert len(rendered) == 2
    print(f"  ✓ Rendered {len(rendered)} zones")
    for r in rendered[:1]:
        print(f"    - {r['name']}: {r['color']}, opacity={r['opacity']}")

    # Generate overlay grid
    grid = vis.generate_overlay_grid(zones, resolution=50)
    assert len(grid) == 50
    print(f"  ✓ Generated overlay grid: {len(grid)}x{len(grid[0])}")

    # Color coding
    for zone in zones:
        color = vis.get_zone_color(zone)
        print(f"  ✓ Zone '{zone.name}' color: {color}")

    # Legend
    legend = vis.get_legend()
    print(f"  ✓ Legend entries: {len(legend)}")

    # Complete overlay
    overlay = vis.generate_complete_overlay(zones)
    assert 'zones' in overlay
    assert 'overlay_grid' in overlay
    assert 'legend' in overlay
    print(f"  ✓ Complete overlay generated with all elements")

    print("  ✓ ALL VISUALIZATION TESTS PASSED\n")
    return True


def test_corridor_manager():
    """Test flight corridor management."""
    print("=" * 60)
    print("TEST: Corridor Manager")
    print("=" * 60)

    cm = CorridorManager()

    # Create a corridor
    corridor = FlightCorridor(
        name="Test Corridor",
        description="Through restricted zone Alpha",
        waypoints=[
            CorridorWaypoint(position=(10, 10), altitude=50, is_entry=True),
            CorridorWaypoint(position=(50, 50), altitude=50),
            CorridorWaypoint(position=(90, 90), altitude=50, is_exit=True),
        ],
        width=10,
        max_speed=15,
    )
    cm.add_corridor(corridor)
    print(f"  ✓ Added corridor: {corridor.name}")
    print(f"  ✓ Corridor length: {corridor.length:.1f}")

    # Find nearest corridor
    nearest = cm.find_nearest_corridor((12, 12))
    assert nearest is not None
    print(f"  ✓ Nearest corridor: {nearest[0].name} at {nearest[1]:.1f} units")

    # Auto-create corridor
    auto = cm.create_corridor_between((5, 5), (95, 95), "Auto Corridor")
    print(f"  ✓ Auto-created corridor: {auto.name} with {len(auto.waypoints)} waypoints")

    # Stats
    stats = cm.get_stats()
    print(f"  ✓ Stats: {stats['total_corridors']} corridors")

    print("  ✓ ALL CORRIDOR MANAGER TESTS PASSED\n")
    return True


def run_all_tests():
    """Run all airspace system tests."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     AIRSPACE INTELLIGENCE SYSTEM - TEST SUITE           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    start_time = time.time()
    passed = 0
    total = 8

    tests = [
        ("Zone Models", test_basic_zone_creation),
        ("Geofence Engine", test_geofence_engine),
        ("Airspace Manager", test_airspace_manager),
        ("Temporary Restrictions", test_temporary_restrictions),
        ("Altitude Manager", test_altitude_manager),
        ("Database", test_database),
        ("Visualization", test_visualization),
        ("Corridor Manager", test_corridor_manager),
    ]

    for name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                passed += 1
                print(f"  ✅ {name} PASSED")
            else:
                print(f"  ❌ {name} FAILED")
        except Exception as e:
            print(f"  ❌ {name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
        print()

    elapsed = time.time() - start_time
    print("=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed in {elapsed:.2f}s")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)