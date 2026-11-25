"""Sumber lokasi: simulasi, tetap, atau modul GPS USB (NMEA)."""
import threading
import time
from dataclasses import dataclass
from typing import Optional

from .geo import destination


@dataclass
class Fix:
    lat: float
    lon: float
    speed_kmh: float = 0.0
    heading: Optional[float] = None   # derajat, None kalau belum diketahui
    valid: bool = True


class FixedGPS:
    def __init__(self, cfg):
        self.fix = Fix(*cfg.START_POS)

    def get(self) -> Fix:
        return self.fix


class SimGPS:
    """Mobil virtual yang jalan lurus ke arah SIM_HEADING_DEG."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.lat, self.lon = cfg.START_POS
        self.t = time.time()

    def get(self) -> Fix:
        now = time.time()
        dist = self.cfg.SIM_SPEED_KMH * self.cfg.SIM_SPEEDUP * (now - self.t) / 3600.0
        self.t = now
        if dist > 0:
            self.lat, self.lon = destination(self.lat, self.lon, self.cfg.SIM_HEADING_DEG, dist)
        return Fix(self.lat, self.lon, self.cfg.SIM_SPEED_KMH, self.cfg.SIM_HEADING_DEG)


def _nmea_deg(value: str, hemi: str) -> float:
    dot = value.index(".")
    deg = float(value[:dot - 2])
    minutes = float(value[dot - 2:])
    d = deg + minutes / 60.0
    return -d if hemi in ("S", "W") else d


def parse_rmc(line: str) -> Optional[Fix]:
    """Parse kalimat NMEA $GPRMC / $GNRMC. None kalau tidak valid."""
    line = line.strip()
    if not line.startswith("$") or "RMC" not in line[:6]:
        return None
    f = line.split("*")[0].split(",")
    if len(f) < 9 or f[2] != "A" or not f[3] or not f[5]:
        return None
    try:
        lat = _nmea_deg(f[3], f[4])
        lon = _nmea_deg(f[5], f[6])
        speed = float(f[7]) * 1.852 if f[7] else 0.0
        heading = float(f[8]) if f[8] else None
    except ValueError:
        return None
    return Fix(lat, lon, speed, heading)


class SerialGPS:
    """Baca NMEA dari modul GPS USB di thread terpisah (belum diuji dengan perangkat asli)."""

    def __init__(self, cfg):
        import serial  # pip install pyserial
        self.ser = serial.Serial(cfg.SERIAL_PORT, cfg.SERIAL_BAUD, timeout=1)
        self.fix = Fix(0.0, 0.0, valid=False)
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                line = self.ser.readline().decode("ascii", errors="ignore")
            except Exception:
                time.sleep(1)
                continue
            fix = parse_rmc(line)
            if fix:
                self.fix = fix

    def get(self) -> Fix:
        return self.fix


def make_gps(cfg):
    if cfg.GPS_MODE == "serial":
        return SerialGPS(cfg)
    if cfg.GPS_MODE == "fixed":
        return FixedGPS(cfg)
    return SimGPS(cfg)
