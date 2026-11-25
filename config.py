"""Semua pengaturan ada di sini. Ubah sesuai kebutuhan."""
import sys
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Config:
    # --- Kamera ---
    CAMERA_INDEX: int = 0
    FRAME_WIDTH: int = 1280
    FRAME_HEIGHT: int = 720
    MIRROR: bool = True

    # --- Kalibrasi (mata terbuka, lihat ke kamera) ---
    CALIB_SEC: float = 5.0
    CALIB_RATIO: float = 0.75      # threshold = median EAR terbuka * ratio
    EAR_THRESHOLD: float = 0.21    # dipakai kalau kalibrasi dilewati
    EAR_MIN: float = 0.15          # batas aman hasil kalibrasi
    EAR_MAX: float = 0.30

    # --- Deteksi mata ---
    WARN_CLOSED_SEC: float = 0.8   # mata merem >= ini -> WARNING
    ALARM_CLOSED_SEC: float = 1.5  # mata merem >= ini -> DROWSY (alarm)

    # --- PERCLOS (persen waktu mata tertutup dalam jendela waktu) ---
    PERCLOS_WINDOW_SEC: float = 60.0
    PERCLOS_MIN_DATA_SEC: float = 10.0
    PERCLOS_WARN: float = 0.15
    PERCLOS_ALARM: float = 0.30

    # --- Menguap (MAR) ---
    MAR_THRESHOLD: float = 0.60
    YAWN_SEC: float = 1.0

    # --- Wajah hilang (misal kepala menunduk) ---
    NO_FACE_ALARM_SEC: float = 3.0

    # --- Alarm ---
    ALARM_FILE: str = "assets/alarm.wav"
    ALARM_VOLUME: float = 1.0

    # --- Log ---
    LOG_FILE: str = "logs/events.csv"

    # ==================== ASISTEN SUARA ====================
    VOICE_ENABLED: bool = True
    ALARM_BEFORE_VOICE_SEC: float = 3.0   # alarm bunyi dulu segini, lalu diganti suara
    REASK_COOLDOWN_SEC: float = 180.0     # jeda sebelum tanya lagi kalau jawab "tidak"
    UNCLEAR_COOLDOWN_SEC: float = 60.0    # jeda kalau jawaban tidak terdengar

    # --- Suara keluar (TTS) ---
    # "auto" = coba edge-tts (natural, butuh internet), kalau gagal pakai suara Windows (offline)
    # "edge" = hanya edge-tts, "sapi" = hanya suara Windows/offline
    TTS_ENGINE: str = "auto"
    EDGE_VOICE: str = "id-ID-ArdiNeural"  # atau "id-ID-GadisNeural"

    # --- Suara masuk (mic, faster-whisper, offline) ---
    STT_ENABLED: bool = True
    WHISPER_MODEL: str = "small"          # "base" lebih cepat, "small" lebih akurat
    WHISPER_DEVICE: str = "cpu"           # "cuda" kalau CUDA + cuDNN sudah terpasang
    WHISPER_COMPUTE: str = "int8"         # untuk cuda pakai "float16"
    MIC_DEVICE: Optional[int] = None      # None = mic default Windows
    LISTEN_SEC: float = 6.0               # batas waktu mendengarkan jawaban
    MIC_MIN_RMS: float = 0.015            # naikkan kalau noise dianggap suara

    # ==================== GPS & REST AREA ====================
    # "sim"    = posisi disimulasikan jalan terus (untuk demo/tes di laptop)
    # "fixed"  = posisi diam di START_POS
    # "serial" = modul GPS USB (NMEA) lewat SERIAL_PORT
    GPS_MODE: str = "sim"
    START_POS: Tuple[float, float] = (-5.4295, 105.2610)   # lat, lon (Bandar Lampung)
    SIM_HEADING_DEG: float = 0.0          # arah jalan simulasi (0 = utara)
    SIM_SPEED_KMH: float = 80.0
    SIM_SPEEDUP: float = 8.0              # waktu simulasi dipercepat supaya demo singkat
    SERIAL_PORT: str = "COM5"
    SERIAL_BAUD: int = 9600

    REST_CSV: str = "data/rest_areas.csv"            # data asli (isi pakai tools/fetch_rest_areas.py)
    DEMO_CSV: str = "data/rest_areas_demo.csv"       # dibuat otomatis untuk mode sim

    @property
    def use_dshow(self) -> bool:
        return sys.platform.startswith("win")
