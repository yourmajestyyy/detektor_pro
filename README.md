# Drowsiness Detector

Deteksi kantuk real-time dari webcam: mata merem (EAR), PERCLOS, menguap (MAR), wajah hilang.

## Setup (Windows)

```bash
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Pakai Python 3.10 / 3.11 (MediaPipe 0.10.14).

## Cara pakai

1. Saat program mulai, ada kalibrasi 5 detik: buka mata, lihat kamera, kedip normal.
2. Tutup mata >= 1,5 detik -> alarm bunyi.
3. Tombol: `c` kalibrasi ulang, `m` mute, `q`/`Esc` keluar.
4. Event ngantuk tercatat di `logs/events.csv`.

## Tuning (config.py)

- Sering salah deteksi -> naikkan/turunkan `CALIB_RATIO` (0.70-0.80) atau `ALARM_CLOSED_SEC`.
- Pakai kacamata / cahaya redup -> kalibrasi ulang dengan `c`.

## Soal GPU (RTX 4050)

MediaPipe Face Mesh sudah real-time di CPU (jalan di Python), jadi GPU tidak wajib.
GPU baru terpakai kalau nanti diganti ke model deep learning (YOLO / CNN klasifikasi mata) dengan PyTorch + CUDA.

---

## Asisten suara + rest area (baru)

Saat ngantuk: alarm bunyi 3 detik -> alarm berhenti -> program bicara:
_"Kamu terlihat mengantuk. Tempat istirahat terdekat, Rest Area kilometer 49, 12 kilometer lagi. Mau mampir?"_
-> mic mendengarkan -> "ya/mau" = dipandu dengan pengingat jarak (5, 2, 1, 0,5 km, lalu "sudah sampai");
"tidak" = tanya lagi 3 menit kemudian.

Kamu juga bisa bertanya sendiri: tekan `v`, lalu ucapkan _"rest area terdekat berapa km lagi?"_.
Ucapkan "batal" saat tombol `v` aktif untuk membatalkan tujuan.

### Tombol tambahan

`v` tanya lewat suara | `y` / `n` jawab lewat keyboard (cadangan kalau mic bermasalah)

### Pemasangan tambahan

```bash
pip install -r requirements.txt
```

- Pertama kali jalan, faster-whisper mengunduh model (`small` ~ 460 MB). Butuh internet sekali saja, setelah itu offline.
- Suara keluar: `TTS_ENGINE="auto"` memakai edge-tts (natural, butuh internet) dan otomatis jatuh ke suara Windows (offline)
  kalau internet mati. Untuk suara offline berbahasa Indonesia: Settings > Time & language > Speech > tambah voice Indonesia.
  Kalau tidak ada, Windows akan membaca dengan suara Inggris.

### Mode GPS (`GPS_MODE` di config.py)

| Mode            | Kegunaan                                                                                         |
| --------------- | ------------------------------------------------------------------------------------------------ |
| `sim` (default) | Demo di laptop: mobil virtual jalan lurus, 3 rest area DEMO (fiktif) dibuat otomatis di depannya |
| `fixed`         | Posisi diam di `START_POS`                                                                       |
| `serial`        | Modul GPS USB (NMEA). `pip install pyserial`, atur `SERIAL_PORT`                                 |

Untuk data rest area/SPBU nyata (butuh internet, dari OpenStreetMap):

```bash
python tools/fetch_rest_areas.py            # seluruh Lampung -> data/rest_areas.csv
```

Lalu set `GPS_MODE = "fixed"` atau `"serial"`. Format CSV: `name,lat,lon,kind` (kind: `rest_area` / `spbu`).

### Catatan

- Jarak dihitung garis lurus, bukan jarak jalan, jadi hanya perkiraan. Rest area yang dipilih adalah yang di depan arah jalan.
- Di mobil, noise mesin/angin menurunkan akurasi mic. Kalau tidak terdengar, program mengulang pertanyaan sekali.
- Tes logika tanpa kamera/mic: `python tests/test_logic.py`
- Mau GPU untuk whisper: `WHISPER_DEVICE="cuda"`, `WHISPER_COMPUTE="float16"` (perlu CUDA + cuDNN).
