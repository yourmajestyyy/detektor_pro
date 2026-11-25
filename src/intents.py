"""Pemahaman jawaban sederhana (bahasa Indonesia) berbasis kata kunci."""
import re
from typing import Optional

YES = {"ya", "iya", "yap", "yup", "yoi", "mau", "boleh", "oke", "ok", "okay", "siap", "baik",
       "ayo", "gas", "setuju", "mampir", "betul", "benar", "hooh", "yes"}
NO = {"tidak", "nggak", "enggak", "engga", "ngga", "gak", "ga", "tak", "tdk", "jangan",
      "nanti", "belum", "no", "nope"}

_REST_KEYS = ("rest area", "restarea", "rest eria", "res area", "resarea", "istirahat",
              "spbu", "pom bensin", "berapa km", "berapa kilo", "jarak", "terdekat")
_CANCEL_KEYS = ("batal", "tidak jadi", "nggak jadi", "gak jadi", "cancel")


def _words(text: str):
    return re.findall(r"[a-z]+", (text or "").lower())


def parse_yes_no(text: str) -> Optional[bool]:
    """True = ya, False = tidak, None = tidak jelas. Kata negasi menang ('tidak mau' -> False)."""
    w = set(_words(text))
    if w & NO:
        return False
    if w & YES:
        return True
    return None


def is_restarea_query(text: str) -> bool:
    t = (text or "").lower()
    t2 = t.replace(" ", "")
    return any(k in t or k.replace(" ", "") in t2 for k in _REST_KEYS)


def is_cancel(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in _CANCEL_KEYS)
