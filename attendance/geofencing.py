"""Haversine distance check used to validate a clock-in location against an
organisation's configured GeofenceZone(s)."""

from math import atan2, cos, radians, sin, sqrt

EARTH_RADIUS_METERS = 6_371_000


def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lng2 - lng1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return EARTH_RADIUS_METERS * 2 * atan2(sqrt(a), sqrt(1 - a))


def within_any_zone(lat: float, lng: float, zones) -> bool:
    return any(distance_meters(lat, lng, z.latitude, z.longitude) <= z.radius_meters for z in zones)
