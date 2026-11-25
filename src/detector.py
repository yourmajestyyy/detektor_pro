"""Logika deteksi kantuk: EAR, durasi merem, PERCLOS, menguap, wajah hilang."""
from collections import deque
from dataclasses import dataclass

from .landmarks import LEFT_EYE, RIGHT_EYE, eye_aspect_ratio, mouth_aspect_ratio


@dataclass
class State:
    face: bool = False
    ear: float = 0.0
    mar: float = 0.0
    eyes_closed: bool = False
    closed_sec: float = 0.0
    perclos: float = 0.0
    yawning: bool = False
    yawn_count: int = 0
    no_face_sec: float = 0.0
    level: str = "OK"       # OK / WARNING / DROWSY
    reason: str = ""


class DrowsinessDetector:
    def __init__(self, cfg):
        self.cfg = cfg
        self.threshold = cfg.EAR_THRESHOLD
        self.history = deque()          # (waktu, closed: bool)
        self.closed_since = None
        self.yawn_since = None
        self.yawn_counted = False
        self.yawn_count = 0
        self.no_face_since = None

    def set_threshold(self, value: float):
        self.threshold = value

    def reset(self):
        self.history.clear()
        self.closed_since = None
        self.yawn_since = None
        self.yawn_counted = False
        self.no_face_since = None

    def update(self, pts, now: float) -> State:
        c = self.cfg
        s = State(yawn_count=self.yawn_count)

        # ---- wajah tidak ada ----
        if pts is None:
            if self.no_face_since is None:
                self.no_face_since = now
            s.no_face_sec = now - self.no_face_since
            self.closed_since = None
            self.yawn_since = None
            if s.no_face_sec >= c.NO_FACE_ALARM_SEC:
                s.level, s.reason = "DROWSY", "Wajah tidak terdeteksi"
            return s
        self.no_face_since = None
        s.face = True

        # ---- mata ----
        s.ear = (eye_aspect_ratio(pts, LEFT_EYE) + eye_aspect_ratio(pts, RIGHT_EYE)) / 2.0
        s.eyes_closed = s.ear < self.threshold
        if s.eyes_closed:
            if self.closed_since is None:
                self.closed_since = now
            s.closed_sec = now - self.closed_since
        else:
            self.closed_since = None

        # ---- PERCLOS ----
        self.history.append((now, s.eyes_closed))
        while self.history and now - self.history[0][0] > c.PERCLOS_WINDOW_SEC:
            self.history.popleft()
        span = now - self.history[0][0]
        if span >= c.PERCLOS_MIN_DATA_SEC:
            s.perclos = sum(1 for _, x in self.history if x) / len(self.history)

        # ---- menguap ----
        s.mar = mouth_aspect_ratio(pts)
        if s.mar > c.MAR_THRESHOLD:
            if self.yawn_since is None:
                self.yawn_since = now
            if now - self.yawn_since >= c.YAWN_SEC:
                s.yawning = True
                if not self.yawn_counted:
                    self.yawn_count += 1
                    self.yawn_counted = True
        else:
            self.yawn_since = None
            self.yawn_counted = False
        s.yawn_count = self.yawn_count

        # ---- tentukan level ----
        if s.closed_sec >= c.ALARM_CLOSED_SEC:
            s.level, s.reason = "DROWSY", f"Mata merem {s.closed_sec:.1f} dtk"
        elif s.perclos >= c.PERCLOS_ALARM:
            s.level, s.reason = "DROWSY", f"PERCLOS {s.perclos * 100:.0f}%"
        elif s.closed_sec >= c.WARN_CLOSED_SEC:
            s.level, s.reason = "WARNING", "Mata mulai menutup"
        elif s.perclos >= c.PERCLOS_WARN:
            s.level, s.reason = "WARNING", f"PERCLOS {s.perclos * 100:.0f}%"
        elif s.yawning:
            s.level, s.reason = "WARNING", "Menguap"
        return s
