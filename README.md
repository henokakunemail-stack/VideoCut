# VideoCut

Aplikasi desktop video editor gratis dan open-source (alternatif CapCut) berbasis Python, PyQt6, OpenCV, dan AI offline.

---

## Fitur Utama

- **Multi-Track Timeline**: Pengeditan multi-layer video, audio, teks, dan efek dengan zoom dan snapping.
- **Keyframe Animation Engine**: Interpolasi posisi, skala, rotasi, dan opasitas berbasis kurva Bezier.
- **AI Background Removal**: Hapus background video otomatis tanpa green screen (`rembg` / U2Net).
- **Auto Caption / Subtitle**: Transkripsi audio ke subtitle otomatis offline menggunakan `openai-whisper`.
- **Audio FX & Denoise**: Filter audio, equalizer, de-reverb, dan noise gate berbasis `scipy.signal`.
- **Beat Sync Detection**: Analisis tempo dan pendeteksian ketukan musik otomatis dengan `librosa`.
- **Visual Filters & Effects**: Color grading, penyesuaian kecerahan/kontras/saturasi, blur, dan efek transisi.
- **Ekspor Fleksibel**: Ekspor video hingga resolusi 4K 60FPS tanpa watermark (FFmpeg / OpenCV).

---

## Persyaratan Sistem

- **OS**: Windows 10 / 11 64-bit
- **Python**: 3.10+ (disarankan 3.12)
- **RAM**: Minimal 4 GB (disarankan 8 GB+)
- **Storage**: 1 GB ruang kosong

---

## Instalasi & Menjalankan dari Source

### 1. Clone Repository
```bash
git clone https://github.com/henokakunemail-stack/VideoCut.git
cd VideoCut
```

### 2. Install Dependensi
```bash
# Dependensi core
pip install -r requirements.txt
```

Atau jalankan script otomatis:
```cmd
install_and_run.bat
```

### 3. Jalankan Aplikasi
```bash
python main.py
```
atau klik ganda file `run.bat`.

---

## Membangun Installer Windows (.exe)

Aplikasi menyertakan script build otomatis menggunakan PyInstaller dan NSIS:

### Prasyarat Build:
1. `pyinstaller` (`pip install pyinstaller`)
2. NSIS v3.x terinstal di `C:\Program Files (x86)\NSIS\`

### Langkah Build:
Jalankan file batch:
```cmd
build_installer.bat
```
Hasil build:
- **Portable**: `dist\VideoCut\VideoCut.exe`
- **Setup Wizard**: `installer\VideoCut_Setup.exe`

---

## Struktur Proyek

```
VideoCut/
├── assets/                  # Icon dan aset antarmuka
├── installer/               # Script NSIS installer (setup.nsi)
├── src/
│   ├── core/                # Engine inti video, audio, AI, dan keyframe
│   │   ├── ai_background.py # Penggantian background video AI
│   │   ├── audio_fx.py      # Pengolahan audio & noise reduction
│   │   ├── auto_caption.py  # Generator subtitle otomatis (Whisper)
│   │   ├── beat_sync.py     # Deteksi beat musik (Librosa)
│   │   ├── bg_remover.py    # Segmentasi dan penghapusan background
│   │   ├── kenburns.py      # Efek pan & zoom animasi
│   │   ├── keyframe_engine.py # Interpolasi keyframe animasi
│   │   ├── project.py       # Manajemen data dan serialisasi proyek
│   │   └── video_player.py  # Playback frame controller
│   └── ui/                  # Komponen tampilan PyQt6
│       ├── main_window.py   # Jendela utama editor
│       ├── timeline_panel.py# Panel multi-track timeline
│       ├── preview_panel.py # Monitor pemutar video
│       ├── media_panel.py   # Panel aset media
│       ├── properties_panel.py # Pengaturan klip dan transformasi
│       ├── effects_panel.py # Pilihan filter dan efek video
│       └── export_dialog.py # Dialog konfigurasi render video
├── build_installer.bat      # Script otomasi build PyInstaller + NSIS
├── main.py                  # Entry point aplikasi
├── requirements.txt         # Daftar paket Python
└── videocut.spec            # Konfigurasi bundling PyInstaller
```

---

## Lisensi & Kontribusi

Proyek ini bersifat open-source untuk tujuan edukasi dan pengembangan multimedia bebas. Pull request dan issue dipersilakan.
