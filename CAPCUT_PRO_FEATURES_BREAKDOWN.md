# Bedah Arsitektur, Fitur, dan Fungsi Berbayar (Pro/VIP) CapCut Desktop
*Hasil Reverse Engineering Menggunakan MCP REA, Analisis Binary PE, Resource & Database CapCut v9.6.0.4097*

---

## 1. Ringkasan Eksekutif & Arsitektur CapCut Desktop

CapCut Desktop dibangun di atas arsitektur hibrida multi-tier:
- **GUI Desktop**: **Qt 6 (QML + QtQuick + Qt Widgets)** sebagai framework antarmuka utama.
- **Embedded Web & Checkout**: **CEF (Chromium Embedded Framework)** dan **ByteDance Lynx (`lynx.dll`)** untuk modal VIP, toko efek, banner subscription, dan otentikasi.
- **Media Engine Core**: **ByteDance Video Engine (VE / `VECreator.dll` 271MB & `cccreator.dll` 158MB)** yang ditautkan ke **FFmpeg 6/7** (`avcodec-61.dll`, `avformat-61.dll`, `swscale-8.dll`).
- **AI / NPU Inference**: Intel OpenVINO, ByteDance ByteNN (`.bytenn`), ONNX, dan NVIDIA CUDA/nvJPEG.
- **Audio Processing**: ByteDance SAMI (`audiosami`) dengan arsitektur U-Net 44kHz dan RNNoise.
- **Data & Entitlement Storage**: SQLite 3 (`rp.db`, `mediasearch.db`, `tracking.db`) dan Tencent MMKV (`settings_json` 8MB).

---

## 2. Katalog Lengkap Fitur & Fungsi Berbayar (Pro / VIP)

Berdasarkan analisis file binary, schema database `rp.db`, dan enum `VipFunctionType` di template Lynx (`image_lynx_videocutpc_modal` & `subscription_export`), berikut adalah fitur-fitur yang dikunci di balik lisensi Pro/VIP:

### A. AI Video & Visual Enhancement (VIP)
1. **`vip_feature_image_quality_enhance` / `ultra_hd` (AI Video Upscaling)**
   - *Fungsi*: Meningkatkan resolusi video secara cerdas (Super Resolution 2K/4K) dengan rekonstruksi detail wajah dan tekstur.
   - *Teknologi CapCut*: Model neural network `jypc_yunfuhua_gpucpu.model` melalui Intel OpenVINO / ByteNN.
   - *Replikasi Open Source*: Gunakan model Real-ESRGAN / Real-CUGAN via ONNX Runtime atau PyTorch.

2. **`vip_feature_video_denoise` (AI Temporal Video Denoise)**
   - *Fungsi*: Membersihkan noise ISO dan grain pada rekaman low-light tanpa mengorbankan ketajaman tepi (edge preservation).
   - *Teknologi CapCut*: Multi-frame motion vector temporal filter di `VECreator.dll`.
   - *Replikasi Open Source*: OpenCV `cv2.fastNlMeansDenoisingColoredMulti` atau filter FFmpeg `hqdn3d` / `bm3d`.

3. **Smart Cutout / AI Matting Pro (`mattingBlendV2`)**
   - *Fungsi*: Hapus background video manusia/objek secara instan tanpa green screen (rotoscoping otomatis).
   - *Teknologi CapCut*: Model segmentasi biner `models\eur_new_v1.0_size0.model` dipadukan dengan shader alpha blend `mattingBlendV2`.
   - *Replikasi Open Source*: Python `rembg` (U2Net/BiRefNet) atau MediaPipe Selfie Segmentation.

4. **Auto Reframe & Intelligent Crop (`lvop_intelligent_crop`)**
   - *Fungsi*: Mengubah aspek rasio video (16:9 ke 9:16 untuk TikTok/Shorts/Reels) secara otomatis dengan melacak posisi subjek utama di tengah frame.
   - *Teknologi CapCut*: Deteksi bounding box wajah/tubuh via AI tracker `objectRect`.
   - *Replikasi Open Source*: OpenCV Haar Cascade / YOLOv8-pose untuk menghitung dynamic crop window.

5. **Optical Flow Slow Motion & Auto Velocity**
   - *Fungsi*: Menghasilkan slow motion ultra-halus (0.1x) tanpa patah-patah dengan menginterpolasi frame baru di antara dua frame asli.
   - *Teknologi CapCut*: Motion Estimation & Frame Synthesis via Optical Flow GPU.
   - *Replikasi Open Source*: RIFE (Real-Time Intermediate Flow Estimation) atau FFmpeg `minterpolate=mi_mode=mci:mc_mode=aobmc`.

6. **Motion Blur & Camera Shake Pro**
   - *Fungsi*: Menambahkan blur gerak natural berbasis vektor kecepatan objek atau simulasi guncangan kamera sinematik.
   - *Teknologi CapCut*: Shader post-processing OpenGL/Vulkan di `Resources/MixMode`.
   - *Replikasi Open Source*: Shader GLSL atau FFmpeg filter `mestimate` + `avgblur`.

---

### B. AI Audio & Voice Tools (VIP)
1. **`vip_feature_vocal_separation` (Vocal Isolation & Removal)**
   - *Fungsi*: Memisahkan vokal dari musik pengiring (karaoke mode atau ambil vokal bersih untuk podcast).
   - *Teknologi CapCut*: Model U-Net 44kHz SAMI (`audiosami\unet_denoise_44k_music_model_v1.0.model`).
   - *Replikasi Open Source*: Demucs (Meta AI) atau Spleeter (Deezer) via PyTorch/ONNX.

2. **`vip_feature_vocal_beautify` & `vip_feature_vocal_optimization` (Voice Enhance)**
   - *Fungsi*: Penyesuaian EQ adaptif, kompresi dinamis, dan de-reverb agar suara terdengar seperti mikrofon studio rekaman.
   - *Teknologi CapCut*: DSP chain Poco/ByteDance di `audioeffect.dll` + RNNoise (`rnnoise`).
   - *Replikasi Open Source*: RNNoise, PyDub dynamic compressor, dan scipy signal high-pass/parametric EQ.

3. **AI Voice Clone & Multilingual TTS Pro**
   - *Fungsi*: Mengkloning suara pengguna atau menghasilkan narasi AI bahasa asing dengan emosi spesifik.
   - *Teknologi CapCut*: Server-side cloud inference ByteDance TTS.
   - *Replikasi Open Source*: Edge-TTS (gratis via Microsoft Azure engine) atau Coqui TTS offline.

---

### C. Color Grading & Efek Visual Pro
1. **3-Way Color Wheels (`LogWheel`, `PrimaryWheel`)**
   - *Fungsi*: Color grading profesional industri film (Lift, Gamma, Gain, Offset) untuk shadow, midtone, dan highlight.
   - *Teknologi CapCut*: Matrix color transform di `Resources/DefaultAdjustBundle`.
   - *Replikasi Open Source*: Implementasi formula Lift/Gamma/Gain di NumPy / OpenCV LUT generator.

2. **3D LUT Cinema Pack (`.cube`)**
   - *Fungsi*: Preset warna Hollywood (Teal & Orange, Kodak Portra, Alexa LogC to Rec709, Vintage Film).
   - *Teknologi CapCut*: 33x33x33 / 65x65x65 Tetrahedral interpolation LUT files di `Resources/lut`.
   - *Replikasi Open Source*: FFmpeg filter `lut3d=file.cube` atau implementasi trilinear interpolation di Python/Numba.

3. **HSL Curves & Selective Color Curves (`Curves`)**
   - *Fungsi*: Mengatur saturasi, hue, dan luminance hanya pada spektrum warna tertentu (contoh: mengubah warna baju merah tanpa mengubah warna kulit).
   - *Teknologi CapCut*: Spline interpolation pada ruang warna HSL/YUV.
   - *Replikasi Open Source*: `scipy.interpolate.CubicSpline` mapping pada channel HSV/HLS di OpenCV.

---

### D. Export, Transcoding & Output Pro
1. **`membership_and_export_resize`**
   - *Bebas Watermark*: Menghilangkan logo CapCut di akhir video (`remove_watermark`).
   - *Resolusi & Frame Rate*: Membuka opsi ekspor 4K (3840x2160), 60 FPS, dan 120 FPS.
   - *Bitrate Pro*: CBR/VBR High Bitrate (hingga 50-100 Mbps).
2. **`pro_enable_mxf_export` & `pro_enable_front_moov` (ProRes / Studio Codec)**
   - *Fungsi*: Ekspor format mastering profesional Apple ProRes 422/4444 dan MXF container dengan FastStart flag (`front_moov`) untuk streaming web instan.
   - *Teknologi CapCut*: FFmpeg encoder libx264, libx265, prores_ks, av1.
   - *Replikasi Open Source*: FFmpeg CLI `-c:v prores_ks -profile:v 3` atau `-c:v libx264 -preset slow -crf 16 -movflags +faststart`.

---

## 3. Matriks Replikasi Fitur di VideoCut

Berikut adalah pemetaan implementasi fitur-fitur berbayar CapCut ke dalam codebase VideoCut:

| Fitur CapCut Pro | Status di CapCut | Implementasi di VideoCut (Gratis / Bebas) | Teknologi Digunakan |
| :--- | :--- | :--- | :--- |
| **Ekspor 4K 60FPS** | Berbayar | **Tersedia (Bebas)** | FFmpeg / OpenCV VideoWriter |
| **Bebas Watermark** | Berbayar | **Tersedia (Bebas)** | Tanpa watermark sama sekali |
| **Hapus Background AI** | Berbayar | **Tersedia** di `src/core/bg_remover.py` | `rembg` (U2Net AI) |
| **Auto Caption / Subtitle** | Berbayar | **Tersedia** di `src/core/auto_caption.py` | `openai-whisper` (Offline AI) |
| **Audio Denoise / Clean Voice** | Berbayar | **Tersedia** di `src/core/audio_fx.py` | `scipy.signal` bandpass + noise gate |
| **Beat Sync (Deteksi Ketukan)** | Berbayar | **Tersedia** di `src/core/beat_sync.py` | `librosa` onset & tempo tracking |
| **Keyframe Animation Pro** | Berbayar | **Tersedia** di `src/core/keyframe_engine.py` | Bezier curve easing interpolation |
| **Color LUT Grading** | Berbayar | **Dapat ditambahkan** | FFmpeg `lut3d` / OpenCV trilinear LUT |
| **Vocal Isolation (Demucs)** | Berbayar | **Roadmap v2.1** | Meta Demucs ONNX |
| **Speed Ramping / Curves** | Berbayar | **Tersedia** | Time remapping timeline interpolation |

---

## 4. Kesimpulan Hasil Analisis
CapCut memonetisasi fiturnya melalui pembatasan (paywall) di tingkat UI Lynx modal (`image_lynx_videocutpc_modal`) dan MMKV settings (`UserBubbleBuyVipForMaterial`, `cc_member_enable`), sedangkan engine komputasinya (`VECreator.dll`, `audiosami`, OpenVINO, FFmpeg) sebenarnya telah terinstal penuh di PC lokal. 

Dengan VideoCut, semua batasan lisensi komersial ini ditiadakan. Arsitektur VideoCut memanfaatkan library open-source Python (`PyQt6`, `OpenCV`, `NumPy`, `FFmpeg`, `Whisper`, `Rembg`) untuk memberikan fungsionalitas pengeditan video kelas profesional secara 100% gratis dan offline.
