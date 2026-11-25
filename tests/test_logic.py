"""Tes logika tanpa kamera/mic/speaker:  python tests/test_logic.py"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.assistant import VoiceAssistant
from src.geo import haversine_km, speak_distance, speak_name
from src.gps import Fix, FixedGPS, parse_rmc
from src.intents import is_cancel, is_restarea_query, parse_yes_no
from src.restareas import RestArea, nearest_area


class FakeSpeaker:
    def __init__(self): self.said = []
    def say(self, t): self.said.append(t)


class FakeListener:
    ok = True
    def __init__(self, texts): self.texts = list(texts)
    def record(self, max_sec, stop=None): return object()
    def transcribe(self, audio): return self.texts.pop(0) if self.texts else ""


def make(texts, areas=None, heading=0.0):
    cfg = Config(ALARM_BEFORE_VOICE_SEC=0.0, LISTEN_SEC=0.2)
    gps = FixedGPS(cfg)
    gps.fix = Fix(-5.43, 105.26, 80.0, heading)
    areas = areas or [RestArea("Rest Area KM 49", -5.39, 105.26),   # ~4,4 km di utara
                      RestArea("Rest Area Belakang", -5.47, 105.26)]
    sp = FakeSpeaker()
    return VoiceAssistant(cfg, gps, areas, sp, FakeListener(texts)), sp


def run(a):
    t = a._start(a._dialog_drowsy); t.join(5)


def test_basic():
    assert abs(haversine_km(0, 0, 0, 1) - 111.19) < 0.1
    assert speak_distance(0.83) == "850 meter"
    assert speak_distance(2.5) == "2,5 kilometer"
    assert speak_distance(12.4) == "12 kilometer"
    assert speak_name("Rest Area KM 49") == "Rest Area kilometer 49"
    assert parse_yes_no("iya mau") is True
    assert parse_yes_no("nggak mau") is False
    assert parse_yes_no("hmm") is None
    assert is_restarea_query("rest area terdekat berapa km lagi")
    assert is_restarea_query("res area dimana")
    assert is_cancel("batal ya")
    f = parse_rmc("$GPRMC,123519,A,0525.7700,S,10515.6600,E,043.2,084.4,230394,003.1,W*6A")
    assert abs(f.lat + 5.4295) < 1e-3 and abs(f.lon - 105.261) < 1e-3
    assert abs(f.speed_kmh - 80.0) < 0.1 and f.heading == 84.4
    assert parse_rmc("$GPRMC,123519,V,,,,,,,230394,,*00") is None


def test_ahead_only():
    a, _ = make([])
    area, km = nearest_area(a.areas, a.gps.get())
    assert area.name == "Rest Area KM 49", area
    a.gps.fix.heading = 180.0                       # menghadap selatan -> yang di selatan
    assert nearest_area(a.areas, a.gps.get())[0].name == "Rest Area Belakang"


def test_yes():
    a, sp = make(["iya mau"])
    run(a)
    assert a.target.name == "Rest Area KM 49"
    assert "Mau mampir" in sp.said[0] and "kilometer 49" in sp.said[0]
    assert "Baik. Menuju" in sp.said[1] and "menit" in sp.said[1]
    assert not a.busy


def test_no_and_cooldown():
    a, sp = make(["tidak"])
    run(a)
    assert a.target is None and "Tetap waspada" in sp.said[1]
    n = len(sp.said)
    a.on_drowsy(time.time())                         # masih cooldown -> tidak bertanya lagi
    time.sleep(0.2)
    assert len(sp.said) == n and not a.busy


def test_unclear_then_yes():
    a, sp = make(["", "ya"])
    run(a)
    assert any("tidak terdengar" in s for s in sp.said) and a.target


def test_unclear_twice():
    a, sp = make(["", ""])
    run(a)
    assert a.target is None and "anggap belum" in sp.said[-1]


def test_key_fallback():
    a, sp = make([])
    a.listener = None                                # mic tidak ada -> tombol
    t = a._start(a._dialog_drowsy)
    time.sleep(0.1); a.press_key(True); t.join(5)
    assert a.target is not None


def test_query_and_progress():
    a, sp = make(["rest area terdekat berapa km lagi", "mau"])
    t = a._start(a._dialog_query); t.join(5)
    assert a.target and "Tempat istirahat terdekat" in sp.said[1]
    a.gps.fix = Fix(-5.3950, 105.26, 80.0, 0.0)      # ~0,55 km dari tujuan -> pengingat 1 km
    a._last_tick = 0
    a.tick(time.time()); time.sleep(0.2)
    assert any("lagi." in s and "Rest Area kilometer 49" in s for s in sp.said[-1:])
    a.gps.fix = Fix(-5.3901, 105.26, 80.0, 0.0)
    time.sleep(0.1); a._last_tick = 0; a.tick(time.time()); time.sleep(0.2)
    assert a.target is None and "sudah sampai" in sp.said[-1]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("OK ", name)
