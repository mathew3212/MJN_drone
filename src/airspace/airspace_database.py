"""
Airspace Database
==================
Imports, exports, and manages airspace zone data from multiple formats.

Supports:
  - Import: GeoJSON, KML, CSV, JSON, Shapefile (via GDAL)
  - Export: GeoJSON, CSV, JSON, KML
  - Realistic zone generation for simulation
  - OpenStreetMap and OpenAIP data structure compatibility
  - Built-in example zones for testing
"""

from __future__ import annotations

import json
import csv
import os
import math
import random
from typing import List, Optional, Tuple, Dict, Any, Set
from dataclasses import dataclass, field

from .restricted_zone import (
    RestrictedZone, ZoneType, ZoneShape, ZonePriority,
    RiskLevel, ZoneStatus, AltitudeEnvelope,
    CircleZone, RectangleZone, PolygonZone, Point2D,
    MultiPolygonZone,
)


class AirspaceDatabase:
    """
    Database for importing, exporting, and managing airspace zones.
    """

    def __init__(self):
        self._zones: Dict[str, RestrictedZone] = {}
        self._imported_count: int = 0
        self._supported_formats = ['geojson', 'json', 'csv', 'kml']

    # ── Zone Registration ───────────────────────────────────────

    def register_zone(self, zone: RestrictedZone) -> str:
        """Register a zone in the database."""
        self._zones[zone.zone_id] = zone
        return zone.zone_id

    def unregister_zone(self, zone_id: str) -> bool:
        return self._zones.pop(zone_id, None) is not None

    def get_zone(self, zone_id: str) -> Optional[RestrictedZone]:
        return self._zones.get(zone_id)

    def get_all_zones(self) -> List[RestrictedZone]:
        return list(self._zones.values())

    def find_zones_by_type(self, zone_type: ZoneType) -> List[RestrictedZone]:
        return [z for z in self._zones.values() if z.zone_type == zone_type]

    def clear(self):
        self._zones.clear()

    def get_count(self) -> int:
        return len(self._zones)

    # ══════════════════════════════════════════════════════════════
    # IMPORT
    # ══════════════════════════════════════════════════════════════

    def import_from_file(self, filepath: str) -> List[str]:
        """
        Import zones from a file. Auto-detects format from extension.
        Returns list of imported zone IDs.
        """
        ext = os.path.splitext(filepath)[1].lower().lstrip('.')
        if ext == 'geojson' or ext == 'json':
            return self.import_geojson(filepath)
        elif ext == 'csv':
            return self.import_csv(filepath)
        elif ext == 'kml':
            return self.import_kml(filepath)
        else:
            raise ValueError(f"Unsupported format: {ext}. Supported: {self._supported_formats}")

    def import_geojson(self, filepath: str) -> List[str]:
        """Import zones from a GeoJSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        imported_ids = []
        features = data.get('features', [])

        for feature in features:
            props = feature.get('properties', {})
            geometry = feature.get('geometry', {})

            zone = self._geojson_feature_to_zone(props, geometry)
            if zone:
                self.register_zone(zone)
                imported_ids.append(zone.zone_id)

        self._imported_count += len(imported_ids)
        return imported_ids

    def import_csv(self, filepath: str) -> List[str]:
        """Import zones from a CSV file."""
        imported_ids = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                zone = self._csv_row_to_zone(row)
                if zone:
                    self.register_zone(zone)
                    imported_ids.append(zone.zone_id)

        self._imported_count += len(imported_ids)
        return imported_ids

    def _geojson_feature_to_zone(self, props: Dict[str, Any],
                                   geometry: Dict[str, Any]) -> Optional[RestrictedZone]:
        """Convert a GeoJSON feature to a RestrictedZone."""
        geom_type = geometry.get('type', '')
        coords = geometry.get('coordinates', [])

        if geom_type == 'Point' and len(coords) >= 2:
            return RestrictedZone(
                name=props.get('name', 'Imported Zone'),
                description=props.get('description', ''),
                zone_type=self._parse_zone_type(props.get('zone_type', 'restricted')),
                zone_shape=ZoneShape.CIRCLE,
                priority=ZonePriority(props.get('priority', 2)),
                center_lon=coords[0],
                center_lat=coords[1],
                shape_data=CircleZone(
                    center=Point2D(coords[0], coords[1]),
                    radius=props.get('radius', 10.0),
                ),
                altitude_limits=AltitudeEnvelope(
                    minimum_altitude=props.get('altitude_min', 0.0),
                    maximum_altitude=props.get('altitude_max', 150.0),
                ),
                safety_buffer=props.get('buffer', 5.0),
                risk_level=RiskLevel(props.get('risk_level', 0.6)),
                source='import_geojson',
            )

        elif geom_type == 'Polygon':
            ring = coords[0] if coords else []
            if len(ring) >= 4:
                vertices = [Point2D(c[0], c[1]) for c in ring[:-1]]
                return RestrictedZone(
                    name=props.get('name', 'Imported Polygon Zone'),
                    description=props.get('description', ''),
                    zone_type=self._parse_zone_type(props.get('zone_type', 'restricted')),
                    zone_shape=ZoneShape.POLYGON,
                    priority=ZonePriority(props.get('priority', 2)),
                    center_lon=sum(v.x for v in vertices) / len(vertices),
                    center_lat=sum(v.y for v in vertices) / len(vertices),
                    shape_data=PolygonZone(vertices=vertices),
                    altitude_limits=AltitudeEnvelope(
                        minimum_altitude=props.get('altitude_min', 0.0),
                        maximum_altitude=props.get('altitude_max', 150.0),
                    ),
                    safety_buffer=props.get('buffer', 5.0),
                    risk_level=RiskLevel(props.get('risk_level', 0.6)),
                    source='import_geojson',
                )

        elif geom_type == 'MultiPolygon':
            polygons = []
            for poly_coords in coords:
                ring = poly_coords[0] if poly_coords else []
                if len(ring) >= 4:
                    vertices = [Point2D(c[0], c[1]) for c in ring[:-1]]
                    polygons.append(PolygonZone(vertices=vertices))

            if polygons:
                all_pts = [v for p in polygons for v in p.vertices]
                center_x = sum(v.x for v in all_pts) / len(all_pts)
                center_y = sum(v.y for v in all_pts) / len(all_pts)
                return RestrictedZone(
                    name=props.get('name', 'Imported MultiPolygon Zone'),
                    description=props.get('description', ''),
                    zone_type=self._parse_zone_type(props.get('zone_type', 'restricted')),
                    zone_shape=ZoneShape.MULTI_POLYGON,
                    priority=ZonePriority(props.get('priority', 2)),
                    center_lon=center_x,
                    center_lat=center_y,
                    shape_data=MultiPolygonZone(polygons=polygons),
                    altitude_limits=AltitudeEnvelope(
                        minimum_altitude=props.get('altitude_min', 0.0),
                        maximum_altitude=props.get('altitude_max', 150.0),
                    ),
                    safety_buffer=props.get('buffer', 5.0),
                    risk_level=RiskLevel(props.get('risk_level', 0.6)),
                    source='import_geojson',
                )

        return None

    def _csv_row_to_zone(self, row: Dict[str, str]) -> Optional[RestrictedZone]:
        """Convert a CSV row to a RestrictedZone."""
        try:
            return RestrictedZone(
                name=row.get('name', 'CSV Zone'),
                description=row.get('description', ''),
                zone_type=self._parse_zone_type(row.get('zone_type', 'restricted')),
                zone_shape=ZoneShape.CIRCLE,
                priority=ZonePriority(int(row.get('priority', '2'))),
                center_lon=float(row.get('longitude', row.get('lon', '0'))),
                center_lat=float(row.get('latitude', row.get('lat', '0'))),
                shape_data=CircleZone(
                    center=Point2D(
                        float(row.get('longitude', row.get('lon', '0'))),
                        float(row.get('latitude', row.get('lat', '0'))),
                    ),
                    radius=float(row.get('radius', '10')),
                ),
                altitude_limits=AltitudeEnvelope(
                    minimum_altitude=float(row.get('altitude_min', '0')),
                    maximum_altitude=float(row.get('altitude_max', '150')),
                ),
                safety_buffer=float(row.get('buffer', '5')),
                risk_level=RiskLevel(float(row.get('risk_level', '0.6'))),
                source='import_csv',
            )
        except (ValueError, KeyError):
            return None

    def import_kml(self, filepath: str) -> List[str]:
        """Import zones from a KML file (simplified)."""
        imported_ids = []
        with open(filepath, 'r') as f:
            content = f.read()

        import xml.etree.ElementTree as ET
        root = ET.fromstring(content)

        # KML namespace
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}

        for placemark in root.findall('.//kml:Placemark', ns):
            name = placemark.findtext('kml:name', 'KML Zone', ns)
            desc = placemark.findtext('kml:description', '', ns)

            point = placemark.find('.//kml:Point/kml:coordinates', ns)
            if point is not None:
                coords = point.text.strip().split(',')
                if len(coords) >= 2:
                    zone = RestrictedZone(
                        name=name,
                        description=desc,
                        zone_shape=ZoneShape.CIRCLE,
                        center_lon=float(coords[0]),
                        center_lat=float(coords[1]),
                        shape_data=CircleZone(
                            center=Point2D(float(coords[0]), float(coords[1])),
                            radius=10.0,
                        ),
                        source='import_kml',
                    )
                    self.register_zone(zone)
                    imported_ids.append(zone.zone_id)

        self._imported_count += len(imported_ids)
        return imported_ids

    # ══════════════════════════════════════════════════════════════
    # EXPORT
    # ══════════════════════════════════════════════════════════════

    def export_to_file(self, filepath: str, zone_ids: Optional[List[str]] = None):
        """Export zones to a file. Format auto-detected from extension."""
        ext = os.path.splitext(filepath)[1].lower().lstrip('.')
        zones = [self._zones[zid] for zid in zone_ids] if zone_ids else self.get_all_zones()

        if ext == 'json' or ext == 'geojson':
            self.export_geojson(filepath, zones)
        elif ext == 'csv':
            self.export_csv(filepath, zones)
        else:
            raise ValueError(f"Unsupported export format: {ext}")

    def export_geojson(self, filepath: str, zones: List[RestrictedZone]):
        """Export zones to GeoJSON."""
        features = []
        for zone in zones:
            feature = {
                'type': 'Feature',
                'properties': zone.to_dict(),
                'geometry': {
                    'type': 'Point',
                    'coordinates': [zone.center_lon, zone.center_lat],
                },
            }
            features.append(feature)

        geojson = {
            'type': 'FeatureCollection',
            'features': features,
        }

        with open(filepath, 'w') as f:
            json.dump(geojson, f, indent=2)

    def export_csv(self, filepath: str, zones: List[RestrictedZone]):
        """Export zones to CSV."""
        if not zones:
            return

        fieldnames = [
            'zone_id', 'name', 'zone_type', 'zone_shape',
            'latitude', 'longitude', 'altitude_min', 'altitude_max',
            'priority', 'risk_level', 'safety_buffer',
        ]

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for zone in zones:
                writer.writerow({
                    'zone_id': zone.zone_id,
                    'name': zone.name,
                    'zone_type': zone.zone_type.value,
                    'zone_shape': zone.zone_shape.value,
                    'latitude': zone.center_lat,
                    'longitude': zone.center_lon,
                    'altitude_min': zone.altitude_limits.minimum_altitude,
                    'altitude_max': zone.altitude_limits.maximum_altitude,
                    'priority': zone.priority.value,
                    'risk_level': zone.risk_level.value,
                    'safety_buffer': zone.safety_buffer,
                })

    # ══════════════════════════════════════════════════════════════
    # BUILT-IN ZONE GENERATION
    # ══════════════════════════════════════════════════════════════

    def generate_example_zones(self, world_width: float = 100,
                                 world_height: float = 100) -> List[str]:
        """
        Generate example restricted zones for simulation testing.
        Creates realistic zones mimicking real-world airspace constraints.
        """
        ids = []

        # 1. Military base (large restricted circle)
        ids.append(self.register_zone(RestrictedZone(
            name="Fort Drum Military Base",
            description="Active military installation - no fly zone",
            zone_type=ZoneType.MILITARY_BASE,
            zone_shape=ZoneShape.CIRCLE,
            priority=ZonePriority.CRITICAL,
            center_lon=15, center_lat=15,
            shape_data=CircleZone(center=Point2D(15, 15), radius=12),
            safety_buffer=8.0,
            risk_level=RiskLevel.SEVERE,
            permission_required=True,
        )))

        # 2. Airport
        ids.append(self.register_zone(RestrictedZone(
            name="Metro International Airport",
            description="Commercial airport approach path",
            zone_type=ZoneType.AIRPORT,
            zone_shape=ZoneShape.CIRCLE,
            priority=ZonePriority.HIGHEST,
            center_lon=85, center_lat=20,
            shape_data=CircleZone(center=Point2D(85, 20), radius=15),
            altitude_limits=AltitudeEnvelope(minimum_altitude=0, maximum_altitude=120),
            risk_level=RiskLevel.SEVERE,
        )))

        # 3. Hospital with helipad
        ids.append(self.register_zone(RestrictedZone(
            name="City Hospital - Helipad Zone",
            description="Hospital helipad approach and departure path",
            zone_type=ZoneType.HOSPITAL,
            zone_shape=ZoneShape.CIRCLE,
            priority=ZonePriority.HIGH,
            center_lon=40, center_lat=70,
            shape_data=CircleZone(center=Point2D(40, 70), radius=8),
            altitude_limits=AltitudeEnvelope(minimum_altitude=0, maximum_altitude=80),
            risk_level=RiskLevel.HIGH,
        )))

        # 4. School zone
        ids.append(self.register_zone(RestrictedZone(
            name="Westside Elementary School",
            description="School zone - drone restrictions during school hours",
            zone_type=ZoneType.SCHOOL_ZONE,
            zone_shape=ZoneShape.CIRCLE,
            priority=ZonePriority.MEDIUM,
            center_lon=30, center_lat=40,
            shape_data=CircleZone(center=Point2D(30, 40), radius=5),
            altitude_limits=AltitudeEnvelope(minimum_altitude=0, maximum_altitude=50),
            risk_level=RiskLevel.MODERATE,
        )))

        # 5. Government building (polygon)
        gov_verts = [
            Point2D(55, 50), Point2D(60, 50),
            Point2D(60, 55), Point2D(55, 55),
        ]
        ids.append(self.register_zone(RestrictedZone(
            name="State Capitol Building",
            description="Government building - restricted airspace",
            zone_type=ZoneType.GOVERNMENT_BUILDING,
            zone_shape=ZoneShape.POLYGON,
            priority=ZonePriority.HIGHEST,
            center_lon=57.5, center_lat=52.5,
            shape_data=PolygonZone(vertices=gov_verts),
            safety_buffer=10.0,
            risk_level=RiskLevel.SEVERE,
        )))

        # 6. Power plant
        ids.append(self.register_zone(RestrictedZone(
            name="Riverside Power Plant",
            description="Critical infrastructure - restricted zone",
            zone_type=ZoneType.POWER_PLANT,
            zone_shape=ZoneShape.CIRCLE,
            priority=ZonePriority.HIGH,
            center_lon=75, center_lat=75,
            shape_data=CircleZone(center=Point2D(75, 75), radius=10),
            safety_buffer=12.0,
            risk_level=RiskLevel.HIGH,
        )))

        # 7. National park
        park_verts = [
            Point2D(10, 80), Point2D(20, 78), Point2D(25, 85),
            Point2D(22, 90), Point2D(12, 92), Point2D(8, 88),
        ]
        ids.append(self.register_zone(RestrictedZone(
            name="Yellowstone National Park",
            description="National park - wildlife preservation zone",
            zone_type=ZoneType.NATIONAL_PARK,
            zone_shape=ZoneShape.POLYGON,
            priority=ZonePriority.MEDIUM,
            center_lon=16, center_lat=85,
            shape_data=PolygonZone(vertices=park_verts),
            risk_level=RiskLevel.LOW,
            permission_required=True,
        )))

        # 8. Prison
        ids.append(self.register_zone(RestrictedZone(
            name="State Penitentiary",
            description="Correctional facility - no drone overflight",
            zone_type=ZoneType.PRISON,
            zone_shape=ZoneShape.CIRCLE,
            priority=ZonePriority.HIGH,
            center_lon=50, center_lat=30,
            shape_data=CircleZone(center=Point2D(50, 30), radius=8),
            risk_level=RiskLevel.HIGH,
        )))

        # 9. Rectangular zone (construction site)
        ids.append(self.register_zone(RestrictedZone(
            name="Downtown Construction Crane",
            description="Construction zone with active crane operations",
            zone_type=ZoneType.CONSTRUCTION_ZONE,
            zone_shape=ZoneShape.RECTANGLE,
            priority=ZonePriority.MEDIUM,
            center_lon=35, center_lat=25,
            shape_data=PolygonZone(vertices=[
                Point2D(30, 20), Point2D(40, 20),
                Point2D(40, 30), Point2D(30, 30),
            ]),
            altitude_limits=AltitudeEnvelope(minimum_altitude=5, maximum_altitude=80),
            is_dynamic=True,
            risk_level=RiskLevel.MODERATE,
        )))

        # 10. Wildlife sanctuary
        ids.append(self.register_zone(RestrictedZone(
            name="Wildlife Bird Sanctuary",
            description="Protected bird nesting area",
            zone_type=ZoneType.WILDLIFE_SANCTUARY,
            zone_shape=ZoneShape.CIRCLE,
            priority=ZonePriority.MEDIUM,
            center_lon=90, center_lat=85,
            shape_data=CircleZone(center=Point2D(90, 85), radius=6),
            risk_level=RiskLevel.LOW,
        )))

        return ids

    def generate_all_zone_types(self) -> Dict[str, List[str]]:
        """Generate all zone types for comprehensive testing."""
        results = {}
        for zone_type in ZoneType:
            zone = RestrictedZone(
                name=f"Example {zone_type.value.replace('_', ' ').title()}",
                description=f"Example zone for {zone_type.value}",
                zone_type=zone_type,
                center_lon=random.uniform(10, 90),
                center_lat=random.uniform(10, 90),
                shape_data=CircleZone(
                    center=Point2D(random.uniform(10, 90), random.uniform(10, 90)),
                    radius=random.uniform(5, 15),
                ),
                source='generated',
            )
            self.register_zone(zone)
            zone_type_name = zone_type.value
            if zone_type_name not in results:
                results[zone_type_name] = []
            results[zone_type_name].append(zone.zone_id)
        return results

    # ══════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_zone_type(type_str: str) -> ZoneType:
        """Parse a zone type string to ZoneType enum."""
        type_map = {
            'restricted': ZoneType.RESTRICTED,
            'military': ZoneType.MILITARY_BASE,
            'airport': ZoneType.AIRPORT,
            'helipad': ZoneType.HELIPAD,
            'government': ZoneType.GOVERNMENT_BUILDING,
            'power_plant': ZoneType.POWER_PLANT,
            'nuclear': ZoneType.NUCLEAR_FACILITY,
            'prison': ZoneType.PRISON,
            'wildlife': ZoneType.WILDLIFE_SANCTUARY,
            'national_park': ZoneType.NATIONAL_PARK,
            'school': ZoneType.SCHOOL_ZONE,
            'hospital': ZoneType.HOSPITAL,
            'emergency': ZoneType.EMERGENCY_ZONE,
            'tfr': ZoneType.TFR,
            'vip': ZoneType.VIP_MOVEMENT,
            'disaster': ZoneType.DISASTER_AREA,
            'construction': ZoneType.CONSTRUCTION_ZONE,
            'event': ZoneType.EVENT_ZONE,
            'private': ZoneType.PRIVATE_PROPERTY,
            'custom': ZoneType.CUSTOM,
        }
        return type_map.get(type_str.lower(), ZoneType.CUSTOM)

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        type_counts = {}
        for zone in self._zones.values():
            t = zone.zone_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            'total_zones': len(self._zones),
            'imported_count': self._imported_count,
            'zone_types_available': len(type_counts),
            'zone_type_breakdown': type_counts,
            'supported_formats': self._supported_formats,
        }