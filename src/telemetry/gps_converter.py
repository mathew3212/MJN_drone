"""
GPS Coordinate Converter
========================
Converts local simulation coordinates (100x100m grid) to real-world GPS coordinates.
Centered on Bangalore, India (12.9716°N, 77.5946°E).
"""

import math
from typing import Tuple

# ── Constants ──────────────────────────────────────────────────────────────
EARTH_RADIUS_M = 6371000  # meters
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi

# Bangalore reference point
BANGALORE_LAT = 12.9716
BANGALORE_LNG = 77.5946
BANGALORE_LAT_RAD = BANGALORE_LAT * DEG_TO_RAD

# Simulation grid: 100x100 meters, origin at (0, 0)
SIM_WIDTH = 100
SIM_HEIGHT = 100

# Altitude offset: sea level in Bangalore is ~920m
BANGALORE_ALTITUDE = 920


class GPSConverter:
    """
    Bidirectional converter between local simulation coordinates and GPS coordinates.
    
    Local System:
    - Origin (0, 0) at bottom-left
    - X increases East
    - Y increases North
    - Units: meters
    
    GPS System:
    - Latitude/Longitude on WGS84 ellipsoid
    - Altitude: meters above sea level
    """

    @staticmethod
    def local_to_gps(
        x_m: float,
        y_m: float,
        altitude_m: float = 0
    ) -> Tuple[float, float, float]:
        """
        Convert local simulation coordinates to GPS (latitude, longitude, altitude).
        
        Args:
            x_m: X position in meters (East)
            y_m: Y position in meters (North)
            altitude_m: Altitude in meters (above local ground)
            
        Returns:
            (latitude, longitude, altitude_msl)
        """
        # Offset from Bangalore center (in radians)
        lat_offset_rad = (y_m / EARTH_RADIUS_M)
        lng_offset_rad = (x_m / EARTH_RADIUS_M) / math.cos(BANGALORE_LAT_RAD)
        
        # Convert back to degrees
        latitude = BANGALORE_LAT + (lat_offset_rad * RAD_TO_DEG)
        longitude = BANGALORE_LNG + (lng_offset_rad * RAD_TO_DEG)
        altitude = BANGALORE_ALTITUDE + altitude_m
        
        return (latitude, longitude, altitude)

    @staticmethod
    def gps_to_local(
        latitude: float,
        longitude: float,
        altitude_msl: float
    ) -> Tuple[float, float, float]:
        """
        Convert GPS coordinates to local simulation coordinates.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            altitude_msl: Altitude in meters (above sea level)
            
        Returns:
            (x_m, y_m, altitude_local)
        """
        # Offset in degrees
        lat_offset_deg = latitude - BANGALORE_LAT
        lng_offset_deg = longitude - BANGALORE_LNG
        
        # Convert to radians
        lat_offset_rad = lat_offset_deg * DEG_TO_RAD
        lng_offset_rad = lng_offset_deg * DEG_TO_RAD
        
        # Convert to meters
        y_m = lat_offset_rad * EARTH_RADIUS_M
        x_m = lng_offset_rad * EARTH_RADIUS_M * math.cos(BANGALORE_LAT_RAD)
        
        # Altitude relative to ground
        altitude_local = altitude_msl - BANGALORE_ALTITUDE
        
        return (x_m, y_m, altitude_local)

    @staticmethod
    def get_reference_point() -> Tuple[float, float, float]:
        """Return the reference GPS point (Bangalore center)."""
        return (BANGALORE_LAT, BANGALORE_LNG, BANGALORE_ALTITUDE)

    @staticmethod
    def get_sim_bounds() -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Get GPS bounds of the simulation area.
        
        Returns:
            ((min_lat, max_lat), (min_lng, max_lng))
        """
        sw = GPSConverter.local_to_gps(0, 0)
        ne = GPSConverter.local_to_gps(SIM_WIDTH, SIM_HEIGHT)
        
        min_lat = min(sw[0], ne[0])
        max_lat = max(sw[0], ne[0])
        min_lng = min(sw[1], ne[1])
        max_lng = max(sw[1], ne[1])
        
        return ((min_lat, max_lat), (min_lng, max_lng))
