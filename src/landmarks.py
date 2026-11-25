"""Indeks landmark MediaPipe Face Mesh + rumus EAR & MAR."""
import numpy as np

# urutan: p1 (sudut luar), p2, p3 (kelopak atas), p4 (sudut dalam), p5, p6 (kelopak bawah)
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

MOUTH_VERTICAL = [(81, 178), (13, 14), (311, 402)]
MOUTH_HORIZONTAL = (61, 291)


def to_pixels(face_landmarks, w: int, h: int) -> np.ndarray:
    """Landmark ternormalisasi -> koordinat pixel (penting supaya rasio tidak miring)."""
    return np.array([(p.x * w, p.y * h) for p in face_landmarks.landmark], dtype=np.float32)


def _dist(a, b) -> float:
    return float(np.linalg.norm(a - b))


def eye_aspect_ratio(pts: np.ndarray, idx) -> float:
    p1, p2, p3, p4, p5, p6 = (pts[i] for i in idx)
    return (_dist(p2, p6) + _dist(p3, p5)) / (2.0 * _dist(p1, p4) + 1e-6)


def mouth_aspect_ratio(pts: np.ndarray) -> float:
    vertical = sum(_dist(pts[a], pts[b]) for a, b in MOUTH_VERTICAL)
    horizontal = _dist(pts[MOUTH_HORIZONTAL[0]], pts[MOUTH_HORIZONTAL[1]])
    return vertical / (3.0 * horizontal + 1e-6)
