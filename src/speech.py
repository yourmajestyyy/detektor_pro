"""Suara keluar (TTS) dan suara masuk (mic -> teks). Library berat di-import saat dipakai saja."""
import asyncio
import os
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np


class Speaker:
    """edge-tts (natural, online) dengan cadangan suara Windows (SAPI, offline)."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._edge_retry_at = 0.0

    def say(self, text: str):
        print(f"[SUARA] {text}")
        mode = self.cfg.TTS_ENGINE
        if mode in ("auto", "edge") and time.time() >= self._edge_retry_at:
            try:
                self._say_edge(text)
                return
            except Exception as e:
                print(f"[SUARA] edge-tts gagal ({type(e).__name__}: {e})")
                if mode == "edge":
                    return
                self._edge_retry_at = time.time() + 120  # coba lagi 2 menit lagi
        try:
            self._say_sapi(text)
        except Exception as e:
            print(f"[SUARA] TTS offline gagal ({type(e).__name__}: {e})")

    def _say_edge(self, text: str):
        import edge_tts
        import pygame

        if not pygame.mixer.get_init():
            pygame.mixer.init()
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            asyncio.run(edge_tts.Communicate(text, self.cfg.EDGE_VOICE).save(path))
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.unload()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def _say_sapi(self, text: str):
        if sys.platform.startswith("win"):
            script = (
                "Add-Type -AssemblyName System.Speech;"
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                "$v=$s.GetInstalledVoices()|Where-Object{$_.VoiceInfo.Culture.Name -like 'id*'}"
                "|Select-Object -First 1;"
                "if($v){$s.SelectVoice($v.VoiceInfo.Name)};"
                "$s.Speak($env:TTS_TEXT)"
            )
            env = dict(os.environ, TTS_TEXT=text)
            subprocess.run(["powershell", "-NoProfile", "-Command", script], env=env, check=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            for cmd in (["espeak-ng", "-v", "id"], ["espeak", "-v", "id"]):
                try:
                    subprocess.run(cmd + [text], check=True)
                    return
                except FileNotFoundError:
                    continue
            raise RuntimeError("tidak ada TTS offline di sistem ini")


class Listener:
    """Rekam dari mic sampai orang selesai bicara, lalu transkripsi pakai faster-whisper."""

    SR = 16000
    BLOCK = 1600  # 0,1 detik

    def __init__(self, cfg):
        self.cfg = cfg
        self.model = None
        self.ok = True
        self._lock = threading.Lock()

    def load(self):
        with self._lock:
            if self.model is None:
                from faster_whisper import WhisperModel
                self.model = WhisperModel(self.cfg.WHISPER_MODEL, device=self.cfg.WHISPER_DEVICE,
                                          compute_type=self.cfg.WHISPER_COMPUTE)

    def record(self, max_sec: float, stop=None):
        """Kembalikan array float32 16 kHz, atau None kalau tidak ada yang bicara."""
        import sounddevice as sd

        chunks, noise, speech, quiet = [], 0.0, False, 0
        total = int(max_sec / 0.1)
        with sd.InputStream(samplerate=self.SR, channels=1, dtype="float32",
                            blocksize=self.BLOCK, device=self.cfg.MIC_DEVICE) as st:
            for i in range(total):
                if stop and stop():
                    break
                data, _ = st.read(self.BLOCK)
                data = data[:, 0]
                rms = float(np.sqrt(np.mean(data ** 2)))
                chunks.append(data)
                if i < 3:                      # 0,3 dtk awal = estimasi noise
                    noise = max(noise, rms)
                    continue
                if rms > max(self.cfg.MIC_MIN_RMS, noise * 2.5):
                    speech, quiet = True, 0
                elif speech:
                    quiet += 1
                    if quiet >= 8:             # diam 0,8 dtk setelah bicara -> selesai
                        break
        return np.concatenate(chunks) if speech and chunks else None

    def transcribe(self, audio) -> str:
        self.load()
        segs, _ = self.model.transcribe(
            audio, language="id", beam_size=1, vad_filter=True, condition_on_previous_text=False,
            initial_prompt="Ya. Tidak. Mau. Rest area terdekat berapa kilometer lagi? SPBU.")
        return " ".join(s.text for s in segs).strip()
