"""Rumus geografi + format jarak untuk diucapkan."""
import math
import re

R_EARTH_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH_KM * math.asin(math.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def destination(lat, lon, bearing, dist_km):
    d = dist_km / R_EARTH_KM
    b = math.radians(bearing)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1),
                         math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540) % 360 - 180


def speak_distance(km: float) -> str:
    """Jarak dalam kalimat yang enak diucapkan, mis. '800 meter', '2,5 kilometer'."""
    m = km * 1000
    if m < 1000:
        return f"{max(50, int(round(m / 50.0)) * 50)} meter"
    if km < 10:
        v = round(km, 1)
        return (f"{int(v)}" if v == int(v) else f"{v:.1f}".replace(".", ",")) + " kilometer"
    return f"{int(round(km))} kilometer"


def speak_name(name: str) -> str:
    """'KM 49' dibaca 'kilometer 49' oleh TTS."""
    return re.sub(r"\bKM\s*", "kilometer ", name, flags=re.IGNORECASE)
