"""Pendeteksi kantuk real-time (OpenCV + MediaPipe)."""
import csv
import os
import time

import cv2
import mediapipe as mp

from config import Config
from src.alarm import Alarm
from src.calibration import Calibrator
from src.detector import DrowsinessDetector
from src.landmarks import LEFT_EYE, RIGHT_EYE, eye_aspect_ratio, to_pixels
from src.utils import draw_hud


def open_camera(cfg: Config):
    backend = cv2.CAP_DSHOW if cfg.use_dshow else cv2.CAP_ANY
    cap = cv2.VideoCapture(cfg.CAMERA_INDEX, backend)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)
    if not cap.isOpened():
        raise RuntimeError("Kamera tidak bisa dibuka. Cek CAMERA_INDEX di config.py")
    return cap


def build_assistant(cfg: Config):
    """Rangkai GPS + data rest area + suara. None kalau fitur suara dimatikan."""
    if not cfg.VOICE_ENABLED:
        return None
    from src.assistant import VoiceAssistant
    from src.gps import make_gps
    from src.restareas import load_rest_areas, make_demo_csv
    from src.speech import Listener, Speaker

    gps = make_gps(cfg)
    if cfg.GPS_MODE == "sim":
        make_demo_csv(cfg.DEMO_CSV, *cfg.START_POS, cfg.SIM_HEADING_DEG)   # selalu cocok dengan posisi awal
        areas = load_rest_areas(cfg.DEMO_CSV)
    else:
        areas = load_rest_areas(cfg.REST_CSV)
    if not areas:
        print(f"[PERINGATAN] Data rest area kosong. Jalankan: python tools/fetch_rest_areas.py")
    print(f"[ASISTEN] GPS={cfg.GPS_MODE}, {len(areas)} tempat istirahat dimuat")

    listener = Listener(cfg) if cfg.STT_ENABLED else None
    assistant = VoiceAssistant(cfg, gps, areas, Speaker(cfg), listener)
    assistant.preload()
    return assistant


def log_event(cfg: Config, reason: str, state):
    os.makedirs(os.path.dirname(cfg.LOG_FILE), exist_ok=True)
    new = not os.path.exists(cfg.LOG_FILE)
    with open(cfg.LOG_FILE, "a", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        if new:
            wr.writerow(["waktu", "alasan", "ear", "perclos", "menguap"])
        wr.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), reason,
                     f"{state.ear:.3f}", f"{state.perclos:.3f}", state.yawn_count])


def main():
    cfg = Config()
    cap = open_camera(cfg)
    face_mesh = mp.solutions.face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    detector = DrowsinessDetector(cfg)
    calib = Calibrator(cfg)
    alarm = Alarm(cfg.ALARM_FILE, cfg.ALARM_VOLUME)
    assistant = build_assistant(cfg)

    calib.start(time.time())
    prev_level, prev_t, fps = "OK", time.time(), 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if cfg.MIRROR:
            frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        now = time.time()

        res = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        pts = to_pixels(res.multi_face_landmarks[0], w, h) if res.multi_face_landmarks else None

        if calib.active:
            # selama kalibrasi: hanya kumpulkan EAR, tanpa alarm
            ear = None
            if pts is not None:
                ear = (eye_aspect_ratio(pts, LEFT_EYE) + eye_aspect_ratio(pts, RIGHT_EYE)) / 2
            new_thr = calib.feed(ear, now)
            if new_thr:
                detector.set_threshold(new_thr)
                detector.reset()
            state = detector.update(None, now)
            state.level, state.reason, state.no_face_sec = "OK", "", 0.0
            if ear is not None:
                state.ear = ear
        else:
            state = detector.update(pts, now)

        # alarm + log
        if state.level == "DROWSY":
            if prev_level != "DROWSY":
                log_event(cfg, state.reason, state)
            if assistant:
                assistant.on_drowsy(now)
            # selama asisten bicara/mendengarkan, alarm dimatikan supaya mic tidak terganggu
            if assistant and assistant.busy:
                alarm.stop()
            else:
                alarm.start()
        else:
            alarm.stop()
            if assistant:
                assistant.on_ok()
        if assistant:
            assistant.tick(now)
        prev_level = state.level

        # FPS (smoothing)
        dt = now - prev_t
        prev_t = now
        if dt > 0:
            fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps else 1.0 / dt

        info = []
        if assistant:
            fix = assistant.gps.get()
            info.append(f"GPS {cfg.GPS_MODE}: {fix.lat:.4f}, {fix.lon:.4f}")
            if assistant.target:
                info.append(f"Tujuan: {assistant.target.name}")
            if assistant.status:
                info.append(f"Suara: {assistant.status}")
        frame = draw_hud(frame, state, detector.threshold, fps, calib, now, alarm.muted, info)
        cv2.imshow("Drowsiness Detector", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key == ord("c"):
            calib.start(time.time())
            alarm.stop()
        elif key == ord("m"):
            alarm.toggle_mute()
        elif assistant and key == ord("y"):
            assistant.press_key(True)
        elif assistant and key == ord("n"):
            assistant.press_key(False)
        elif assistant and key == ord("v"):
            assistant.ask_by_voice()

    alarm.stop()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
