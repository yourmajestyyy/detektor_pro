"""Asisten suara: tawarkan rest area saat ngantuk, dengarkan jawaban, pandu sampai tujuan."""
import queue
import threading
import time

from .geo import haversine_km, speak_distance, speak_name
from .intents import is_cancel, is_restarea_query, parse_yes_no
from .restareas import nearest_area


class VoiceAssistant:
    APPROACH_KM = (5.0, 2.0, 1.0, 0.5)   # kapan pengingat jarak diucapkan
    ARRIVE_KM = 0.12

    def __init__(self, cfg, gps, areas, speaker, listener=None):
        self.cfg, self.gps, self.areas = cfg, gps, areas
        self.speaker, self.listener = speaker, listener
        self.busy = False
        self.status = ""
        self.target = None
        self._lock = threading.Lock()
        self._keys = queue.Queue()
        self._drowsy_since = None
        self._next_ok = 0.0
        self._announced = set()
        self._min_km = 1e9
        self._last_tick = 0.0

    # ---------- API untuk main loop ----------
    def preload(self):
        """Muat model whisper di latar belakang supaya jawaban pertama tidak lambat."""
        if not self.listener:
            return

        def work():
            try:
                self.listener.load()
                print("[MIC] model suara siap")
            except Exception as e:
                print(f"[MIC] model gagal dimuat ({e}). Pakai tombol y/n sebagai gantinya.")
                self.listener.ok = False
        threading.Thread(target=work, daemon=True).start()

    def on_drowsy(self, now: float):
        if self.busy:
            return
        if self._drowsy_since is None:
            self._drowsy_since = now
        if now - self._drowsy_since >= self.cfg.ALARM_BEFORE_VOICE_SEC and now >= self._next_ok:
            self._start(self._dialog_drowsy)

    def on_ok(self):
        self._drowsy_since = None

    def press_key(self, answer_yes: bool):
        if self.busy:
            self._keys.put("ya" if answer_yes else "tidak")

    def ask_by_voice(self):
        """Tombol 'v': pengemudi bertanya sendiri, mis. 'rest area terdekat berapa km lagi?'"""
        self._start(self._dialog_query)

    def tick(self, now: float):
        """Pantau jarak ke rest area tujuan dan ucapkan pengingat."""
        if not self.target or self.busy or now - self._last_tick < 1.0:
            return
        self._last_tick = now
        fix = self.gps.get()
        if not fix.valid:
            return
        km = haversine_km(fix.lat, fix.lon, self.target.lat, self.target.lon)
        name = speak_name(self.target.name)
        if km <= self.ARRIVE_KM:
            self.target = None
            self._start(lambda: self._say(f"Kamu sudah sampai di {name}. Silakan istirahat dulu."))
            return
        self._min_km = min(self._min_km, km)
        if km > self._min_km + 0.5:
            self.target = None
            self._start(lambda: self._say(f"Sepertinya kamu sudah melewati {name}. "
                                          f"Kalau masih mengantuk, tekan v dan tanya lagi."))
            return
        for th in self.APPROACH_KM:
            if km <= th and th not in self._announced:
                self._announced |= {t for t in self.APPROACH_KM if t >= th}
                self._start(lambda: self._say(f"{name}, {speak_distance(km)} lagi."))
                break

    # ---------- internal ----------
    def _start(self, fn):
        with self._lock:
            if self.busy:
                return None
            self.busy = True

        def run():
            try:
                fn()
            except Exception as e:
                print(f"[ASISTEN] error: {type(e).__name__}: {e}")
            finally:
                self._drain()          # buang tombol sisa supaya tidak terbawa ke dialog berikutnya
                self.status = ""
                self.busy = False
        t = threading.Thread(target=run, daemon=True)
        t.start()
        return t

    def _say(self, text: str):
        self.status = "Berbicara..."
        self.speaker.say(text)
        time.sleep(0.3)   # beri jeda supaya mic tidak menangkap ekor suara speaker

    def _drain(self):
        while not self._keys.empty():
            try:
                self._keys.get_nowait()
            except queue.Empty:
                break

    def _listen_text(self) -> str:
        self.status = "Mendengarkan... (atau tekan y / n)"
        text = ""
        try:
            if self.listener is not None and self.listener.ok:
                audio = self.listener.record(self.cfg.LISTEN_SEC, stop=lambda: not self._keys.empty())
                if audio is not None:
                    text = self.listener.transcribe(audio) or ""
            else:   # mic tidak tersedia -> tunggu tombol
                try:
                    text = self._keys.get(timeout=self.cfg.LISTEN_SEC)
                except queue.Empty:
                    pass
        except Exception as e:
            print(f"[MIC] gagal ({type(e).__name__}: {e}). Beralih ke tombol y / n.")
            if self.listener is not None:
                self.listener.ok = False
        if not self._keys.empty():       # tombol selalu menang
            text = self._keys.get_nowait()
        self.status = ""
        print(f"[MIC] terdengar: {text!r}")
        return text

    def _listen_yes_no(self):
        return parse_yes_no(self._listen_text())

    def _eta_text(self, km, fix) -> str:
        speed = fix.speed_kmh if fix.speed_kmh >= 20 else 60.0
        minutes = int(round(km / speed * 60))
        return f", sekitar {minutes} menit" if minutes >= 1 else ""

    def _offer(self, prefix: str = ""):
        fix = self.gps.get()
        found = nearest_area(self.areas, fix)
        if not found:
            self._say(prefix + "Data tempat istirahat tidak tersedia. "
                               "Sebaiknya berhenti di tempat yang aman.")
            return None
        area, km = found
        self._say(f"{prefix}Tempat istirahat terdekat, {speak_name(area.name)}, "
                  f"{speak_distance(km)} lagi. Mau mampir?")
        ans = self._listen_yes_no()
        if ans is None:
            self._say("Maaf, tidak terdengar. Mau mampir? Ya atau tidak.")
            ans = self._listen_yes_no()

        now = time.time()
        fix = self.gps.get()
        km = haversine_km(fix.lat, fix.lon, area.lat, area.lon)
        if ans is True:
            self.target, self._min_km = area, km
            self._announced = {t for t in self.APPROACH_KM if t >= km}
            self._next_ok = now + self.cfg.REASK_COOLDOWN_SEC
            self._say(f"Baik. Menuju {speak_name(area.name)}, {speak_distance(km)} lagi"
                      f"{self._eta_text(km, fix)}. Tetap fokus ya.")
        elif ans is False:
            self._next_ok = now + self.cfg.REASK_COOLDOWN_SEC
            self._say("Baik. Tetap waspada. Kalau masih mengantuk, aku tanya lagi nanti.")
        else:
            self._next_ok = now + self.cfg.UNCLEAR_COOLDOWN_SEC
            self._say("Baik, aku anggap belum. Tetap waspada.")
        return ans

    def _dialog_drowsy(self):
        if self.target:   # sudah dalam perjalanan ke rest area -> cukup diingatkan
            fix = self.gps.get()
            km = haversine_km(fix.lat, fix.lon, self.target.lat, self.target.lon)
            self._next_ok = time.time() + self.cfg.REASK_COOLDOWN_SEC / 3
            self._say(f"Kamu terlihat mengantuk. {speak_name(self.target.name)} "
                      f"{speak_distance(km)} lagi. Tetap fokus.")
            return
        self._offer("Kamu terlihat mengantuk. ")

    def _dialog_query(self):
        self._say("Silakan.")
        text = self._listen_text()
        if not text:
            self._say("Maaf, tidak terdengar.")
        elif self.target and is_cancel(text):
            self.target = None
            self._say("Baik, dibatalkan.")
        elif is_restarea_query(text):
            self._offer("")
        else:
            self._say("Maaf, aku belum paham. Coba bilang: rest area terdekat berapa kilometer lagi.")
