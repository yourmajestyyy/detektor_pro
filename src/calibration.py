"""Kalibrasi threshold EAR per orang."""
import numpy as np


class Calibrator:
    def __init__(self, cfg):
        self.cfg = cfg
        self.active = False
        self.samples = []
        self.start_time = 0.0
        self.threshold = None

    def start(self, now: float):
        self.active = True
        self.samples = []
        self.start_time = now

    def progress(self, now: float) -> float:
        return min(1.0, (now - self.start_time) / self.cfg.CALIB_SEC)

    def feed(self, ear, now: float):
        """Kembalikan threshold baru kalau kalibrasi selesai, selain itu None."""
        if not self.active:
            return None
        if ear is not None:
            self.samples.append(ear)
        if now - self.start_time >= self.cfg.CALIB_SEC and len(self.samples) >= 30:
            open_ear = float(np.median(self.samples))
            thr = open_ear * self.cfg.CALIB_RATIO
            thr = max(self.cfg.EAR_MIN, min(self.cfg.EAR_MAX, thr))
            self.threshold = thr
            self.active = False
            return thr
        return None
