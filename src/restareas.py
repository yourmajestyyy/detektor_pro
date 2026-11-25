"""Data rest area (CSV) + pencarian yang terdekat di depan."""
import csv
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .geo import angle_diff, bearing_deg, destination, haversine_km


@dataclass
class RestArea:
    name: str
    lat: float
    lon: float
    kind: str = "rest_area"


def load_rest_areas(path: str) -> List[RestArea]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                out.append(RestArea(row["name"].strip(), float(row["lat"]), float(row["lon"]),
                                    (row.get("kind") or "rest_area").strip()))
            except (KeyError, ValueError):
                continue
    return out


def make_demo_csv(path: str, lat: float, lon: float, heading: float):
    """Buat 3 tempat istirahat DEMO di depan posisi awal (nama & lokasi fiktif)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    items = [(4.0, "Rest Area Demo KM 10", "rest_area"),
             (13.0, "SPBU Demo Sinar Jaya", "spbu"),
             (31.0, "Rest Area Demo KM 40", "rest_area")]
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["name", "lat", "lon", "kind"])
        for km, name, kind in items:
            la, lo = destination(lat, lon, heading, km)
            wr.writerow([name, f"{la:.6f}", f"{lo:.6f}", kind])


def nearest_area(areas: List[RestArea], fix, ahead_only: bool = True,
                 max_angle: float = 100.0) -> Optional[Tuple[RestArea, float]]:
    """Kembalikan (area, jarak_km garis lurus). Utamakan yang ada di depan arah jalan."""
    if not areas or not fix.valid:
        return None
    scored = [(haversine_km(fix.lat, fix.lon, a.lat, a.lon), a) for a in areas]
    if ahead_only and fix.heading is not None and fix.speed_kmh >= 5:
        ahead = [(d, a) for d, a in scored
                 if angle_diff(bearing_deg(fix.lat, fix.lon, a.lat, a.lon), fix.heading) <= max_angle]
        if ahead:
            scored = ahead
    d, a = min(scored, key=lambda x: x[0])
    return a, d
