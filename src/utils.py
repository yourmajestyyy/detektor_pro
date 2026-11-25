"""Gambar HUD di atas frame."""
import cv2

COLORS = {"OK": (80, 200, 80), "WARNING": (0, 200, 255), "DROWSY": (0, 0, 255)}
LABELS = {"OK": "AMAN", "WARNING": "WASPADA", "DROWSY": "NGANTUK!"}


def _text(img, text, org, scale=0.6, color=(255, 255, 255), thick=1):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def draw_hud(frame, state, threshold, fps, calibrator, now, muted, info=None):
    h, w = frame.shape[:2]
    color = COLORS[state.level]

    # panel kiri atas (semi transparan)
    roi = frame[0:190, 0:320]
    frame[0:190, 0:320] = (roi * 0.4).astype(roi.dtype)
    _text(frame, f"FPS      : {fps:5.1f}", (10, 25))
    _text(frame, f"EAR      : {state.ear:.3f}  (thr {threshold:.3f})", (10, 50))
    _text(frame, f"MAR      : {state.mar:.3f}", (10, 75))
    _text(frame, f"Merem    : {state.closed_sec:.1f} dtk", (10, 100))
    _text(frame, f"PERCLOS  : {state.perclos * 100:4.1f} %", (10, 125))
    _text(frame, f"Menguap  : {state.yawn_count}x", (10, 150))
    _text(frame, "[c] kalibrasi [m] mute [v] tanya [y/n] jawab [q] keluar", (10, 178), 0.4)

    # info asisten suara (kiri bawah)
    for i, line in enumerate(reversed(info or [])):
        _text(frame, line, (10, h - 20 - i * 24), 0.55, (255, 255, 255))

    # status
    _text(frame, LABELS[state.level], (w // 2 - 120, 50), 1.3, color, 3)
    if state.reason:
        _text(frame, state.reason, (w // 2 - 120, 85), 0.7, color, 2)
    if muted:
        _text(frame, "MUTE", (w - 90, 30), 0.8, (200, 200, 200), 2)

    # border merah saat ngantuk
    if state.level == "DROWSY":
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 12)

    # progress kalibrasi
    if calibrator.active:
        p = calibrator.progress(now)
        cv2.rectangle(frame, (w // 2 - 200, h - 80), (w // 2 + 200, h - 50), (50, 50, 50), -1)
        cv2.rectangle(frame, (w // 2 - 200, h - 80), (w // 2 - 200 + int(400 * p), h - 50), (0, 200, 255), -1)
        _text(frame, "KALIBRASI: buka mata, lihat ke kamera", (w // 2 - 190, h - 95), 0.7)
    return frame
