"""Alarm suara (pygame). File wav dibuat otomatis kalau belum ada."""
import math
import os
import struct
import wave

import pygame


def _make_beep(path: str, freq=1000, beep=0.25, gap=0.15, repeats=3, rate=44100):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    frames = bytearray()
    for _ in range(repeats):
        for i in range(int(rate * beep)):
            v = int(32767 * 0.7 * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", v)
        frames += b"\x00\x00" * int(rate * gap)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


class Alarm:
    def __init__(self, path: str, volume: float = 1.0):
        pygame.mixer.init()
        if not os.path.exists(path):
            _make_beep(path)
        self.sound = pygame.mixer.Sound(path)
        self.sound.set_volume(volume)
        self.playing = False
        self.muted = False

    def start(self):
        if not self.playing and not self.muted:
            self.sound.play(loops=-1)
            self.playing = True

    def stop(self):
        if self.playing:
            self.sound.stop()
            self.playing = False

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.stop()
