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

## VideoCut Mobile (Android APK)

VideoCut kini tersedia untuk perangkat smartphone Android dengan antarmuka sentuh vertikal (CapCut Mobile style layout):

- **Kanvas Responsif**: Rasio 9:16 (TikTok/Shorts/Reels), 16:9 (YouTube), 1:1, dan 4:5.
- **Touch Timeline**: Multi-track video, audio, teks dengan pinch-to-zoom dan split cepat.
- **Color Grading & Filters**: Pengaturan Brightness, Contrast, Saturation, dan Vignette secara real-time.
- **Export Engine**: Pilihan resolusi 720p, 1080p, dan 4K hingga 60 FPS tanpa watermark.
- **Kompatibilitas**: Android 7.0+ (Min SDK 24, Target SDK 34), Universal ARM64 / x86_64.

### Instalasi APK ke HP Android:
1. Salin file `VideoCut.apk` ke HP melalui kabel USB, Bluetooth, atau Google Drive.
2. Di HP Android, buka file manager dan ketuk `VideoCut.apk`.
3. Izinkan *"Install unknown apps"* (jika diminta) dan pilih **Install**.
4. Aplikasi siap digunakan secara offline.

### Membangun Ulang APK dari Source:
```bash
cd videocut_mobile
flutter build apk --release
```
File output akan berada di: `videocut_mobile/build/app/outputs/flutter-apk/app-release.apk`.

---

## Struktur Proyek

```
VideoCut/
├── assets/                  # Icon dan aset antarmuka desktop
├── installer/               # Script NSIS installer Windows (setup.nsi)
├── src/                     # Source code desktop (PyQt6 / Python)
├── videocut_mobile/         # Subproject mobile Android (Flutter / Dart)
│   ├── android/             # Android native Gradle configuration & Manifest
│   ├── lib/
│   │   ├── editor_state.dart# Core state management (tracks, clips, filters)
│   │   ├── main.dart        # Entry point aplikasi Android
│   │   └── ui/
│   │       ├── editor_screen.dart # Layar utama editor CapCut Mobile
│   │       └── widgets/     # Preview canvas, touch timeline, bottom toolbar, export modal
│   └── pubspec.yaml         # Dependensi Flutter
├── VideoCut.apk             # Installer Android APK siap pakai
├── VideoCut_Setup.exe       # Installer Windows PC siap pakai
├── build_installer.bat      # Script otomasi build PyInstaller + NSIS
├── main.py                  # Entry point aplikasi desktop
├── requirements.txt         # Daftar paket Python desktop
└── videocut.spec            # Konfigurasi bundling PyInstaller
```

---

## Lisensi & Kontribusi

Proyek ini bersifat open-source untuk tujuan edukasi dan pengembangan multimedia bebas. Pull request dan issue dipersilakan.
