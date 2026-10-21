"""
Video Player Core - handles video playback using OpenCV + PyQt6
"""

import cv2
import numpy as np
import os
from collections import OrderedDict
from PyQt6.QtCore import QTimer, pyqtSignal, QObject, Qt, QThread
from PyQt6.QtGui import QImage, QPixmap


class VideoReader:
    """Reads frames from a video file."""

    def __init__(self, path: str):
        self.path = path
        self.cap = None
        self.total_frames = 0
        self.fps = 30.0
        self.width = 0
        self.height = 0
        self.duration_ms = 0
        self._lru = OrderedDict()
        self._pos = -1   # frame index the capture will read next
        self._open()

    def _open(self):
        self.cap = cv2.VideoCapture(self.path)
        if self.cap.isOpened():
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.duration_ms = int((self.total_frames / self.fps) * 1000)

    def frame_index(self, time_ms: float) -> int:
        return max(0, min(int((time_ms / 1000.0) * self.fps + 1e-6), self.total_frames - 1))

    def read_index(self, n: int) -> np.ndarray:
        """RGB frame n. Small LRU; reads sequentially (no seek) when n follows the last read."""
        if not self.cap or not self.cap.isOpened():
            return None
        n = max(0, min(n, self.total_frames - 1))
        hit = self._lru.get(n)
        if hit is not None:
            self._lru.move_to_end(n)
            return hit
        if n != self._pos:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, n)
        ret, frame = self.cap.read()
        if not ret:
            self._pos = -1
            return None
        self._pos = n + 1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._lru[n] = rgb
        if len(self._lru) > 8:
            self._lru.popitem(last=False)
        return rgb

    def read_frame(self, time_ms: float) -> np.ndarray:
        f = self.read_index(self.frame_index(time_ms))
        return None if f is None else f.copy()

    def read_thumbnail(self, size=(160, 90)) -> np.ndarray:
        frame = self.read_frame(self.duration_ms // 2)
        if frame is not None:
            return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
        return None

    def close(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def is_valid(self):
        return self.cap is not None and self.cap.isOpened()


class ImageReader:
    """Reads an image file."""

    def __init__(self, path: str):
        self.path = path
        self._img = None
        self.width = 0
        self.height = 0
        self.duration_ms = 5000  # default 5 sec
        self._load()

    def _load(self):
        img = cv2.imread(self.path, cv2.IMREAD_UNCHANGED)  # keeps PNG alpha
        if img is not None:
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            if img.dtype != np.uint8:
                img = (img.astype(np.float32) / (65535.0 if img.dtype == np.uint16 else 1.0)
                       * 255).clip(0, 255).astype(np.uint8)
            self._img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA if img.shape[2] == 4 else cv2.COLOR_BGR2RGB)
            self.height, self.width = self._img.shape[:2]

    def read_frame(self, time_ms: int = 0) -> np.ndarray:
        return self._img.copy() if self._img is not None else None

    def is_valid(self):
        return self._img is not None


class FrameProcessor:
    """Applies color corrections and filters to a frame."""

    @staticmethod
    def apply_color_correction(frame: np.ndarray, clip) -> np.ndarray:
        if frame is None:
            return frame

        result = frame.astype(np.float32) / 255.0

        # Brightness
        if clip.brightness != 0:
            result = result + clip.brightness * 0.5

        # Contrast
        if clip.contrast != 0:
            factor = (259 * (clip.contrast * 255 + 255)) / (255 * (259 - clip.contrast * 255))
            result = factor * (result - 0.5) + 0.5

        # Saturation
        if clip.saturation != 0:
            gray = np.dot(result[..., :3], [0.299, 0.587, 0.114])
            gray = gray[..., np.newaxis]
            result = result + clip.saturation * (result - gray)

        # Temperature (warm/cool)
        if clip.temperature != 0:
            result[:, :, 0] += clip.temperature * 0.1  # red
            result[:, :, 2] -= clip.temperature * 0.1  # blue

        # Tint
        if clip.tint != 0:
            result[:, :, 1] += clip.tint * 0.1  # green

        # Highlight / Shadow
        if clip.highlight != 0:
            mask = result > 0.5
            result[mask] = result[mask] + clip.highlight * (1 - result[mask]) * 0.5

        if clip.shadow != 0:
            mask = result < 0.5
            result[mask] = result[mask] + clip.shadow * result[mask] * 0.5

        result = np.clip(result, 0, 1)

        # Sharpness
        if clip.sharpness > 0:
            img8 = (result * 255).astype(np.uint8)
            blur = cv2.GaussianBlur(img8, (0, 0), 3)
            result = cv2.addWeighted(img8, 1 + clip.sharpness * 2, blur, -clip.sharpness * 2, 0)
            result = result.astype(np.float32) / 255.0

        # Vignette
        if clip.vignette > 0:
            h, w = result.shape[:2]
            Y, X = np.ogrid[:h, :w]
            cx, cy = w / 2, h / 2
            dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
            vign = 1 - np.clip(dist * clip.vignette, 0, 1)
            result = result * vign[..., np.newaxis]

        # Noise reduction (beauty)
        if getattr(clip, 'noise_reduction', 0) > 0:
            nr = getattr(clip, 'noise_reduction', 0)
            img8 = (result * 255).astype(np.uint8)
            ksize = int(nr * 10) * 2 + 1
            result = cv2.GaussianBlur(img8, (ksize, ksize), 0).astype(np.float32) / 255.0

        # Skin smooth (beauty)
        if getattr(clip, 'skin_smooth', 0) > 0:
            smooth = getattr(clip, 'skin_smooth', 0)
            img8 = (result * 255).astype(np.uint8)
            d = int(smooth * 20) + 5
            sigma = smooth * 50 + 20
            result = cv2.bilateralFilter(img8, d, sigma, sigma).astype(np.float32) / 255.0

        # Whitening: lift brightness, weighted towards midtones/shadows so highlights don't clip
        wh = getattr(clip, 'whitening', 0)
        if wh > 0:
            result = np.clip(result + wh * 0.25 * (1.0 - result * 0.5), 0, 1)

        # Skin tone: -1 cool/pale .. +1 warm/rosy
        st = getattr(clip, 'skin_tone', 0)
        if st != 0:
            result = result.copy()
            result[..., 0] += st * 0.06
            result[..., 1] += st * 0.015
            result[..., 2] -= st * 0.05
            result = np.clip(result, 0, 1)

        # Dehaze: stretch contrast per-frame using the dark channel as haze estimate
        dh = getattr(clip, 'dehaze', 0)
        if dh > 0:
            dark = cv2.erode(result.min(axis=2), np.ones((15, 15), np.uint8))
            airlight = max(float(np.percentile(dark, 99)), 0.5)
            t = 1.0 - dh * 0.9 * np.clip(dark / airlight, 0, 1)
            t = np.clip(t, 0.2, 1.0)[..., np.newaxis]
            result = np.clip((result - airlight) / t + airlight, 0, 1)

        # Clarity / Dehaze
        if getattr(clip, 'clarity', 0) > 0:
            clarity = getattr(clip, 'clarity', 0)
            img8 = (result * 255).astype(np.uint8)
            blur = cv2.GaussianBlur(img8, (0, 0), 10).astype(np.float32)
            result = np.clip(img8.astype(np.float32) + clarity * (img8.astype(np.float32) - blur) * 0.5, 0, 255) / 255.0

        # Grain
        if getattr(clip, 'grain', 0) > 0:
            grain_amt = getattr(clip, 'grain', 0)
            noise = np.random.normal(0, grain_amt * 30, result.shape).astype(np.float32)
            result = np.clip(result + noise / 255.0, 0, 1)

        # Opacity
        if clip.opacity < 1.0:
            result = result * clip.opacity

        return (result * 255).clip(0, 255).astype(np.uint8)

    @staticmethod
    def apply_filter(frame: np.ndarray, filter_id: str, intensity: float = 1.0) -> np.ndarray:
        if not filter_id or frame is None:
            return frame

        filters = {
            # Original 18
            'vintage': FrameProcessor._filter_vintage,
            'vivid': FrameProcessor._filter_vivid,
            'cool': FrameProcessor._filter_cool,
            'warm': FrameProcessor._filter_warm,
            'bw': FrameProcessor._filter_bw,
            'sepia': FrameProcessor._filter_sepia,
            'fade': FrameProcessor._filter_fade,
            'portrait': FrameProcessor._filter_portrait,
            'food': FrameProcessor._filter_food,
            'sky': FrameProcessor._filter_sky,
            'natural': FrameProcessor._filter_natural,
            'dawn': FrameProcessor._filter_dawn,
            'dusk': FrameProcessor._filter_dusk,
            'neon': FrameProcessor._filter_neon,
            'cinema': FrameProcessor._filter_cinema,
            'lomo': FrameProcessor._filter_lomo,
            'polaroid': FrameProcessor._filter_polaroid,
            'cross': FrameProcessor._filter_cross,
            # NEW FILTERS
            'film': FrameProcessor._filter_film,
            'matte': FrameProcessor._filter_matte,
            'urban': FrameProcessor._filter_urban,
            'tropical': FrameProcessor._filter_tropical,
            'dreamy': FrameProcessor._filter_dreamy,
            'ink': FrameProcessor._filter_ink,
            'golden': FrameProcessor._filter_golden,
            'moody': FrameProcessor._filter_moody,
            'pastel': FrameProcessor._filter_pastel,
            'vibrant': FrameProcessor._filter_vibrant,
            'autumn': FrameProcessor._filter_autumn,
            'ocean': FrameProcessor._filter_ocean,
            'futuristic': FrameProcessor._filter_futuristic,
            'retro80': FrameProcessor._filter_retro80,
            'coffee': FrameProcessor._filter_coffee,
            'mint': FrameProcessor._filter_mint,
            'rose': FrameProcessor._filter_rose,
            'noir': FrameProcessor._filter_noir,
        }

        fn = filters.get(filter_id)
        if fn:
            filtered = fn(frame)
            # Blend with intensity
            if intensity < 1.0:
                filtered = cv2.addWeighted(frame, 1 - intensity, filtered, intensity, 0)
            return filtered
        return frame

    # ---- Original 18 filters ----

    @staticmethod
    def _filter_vintage(f):
        result = f.astype(np.float32)
        result[:, :, 0] *= 1.1   # R
        result[:, :, 2] *= 0.85  # B
        result = result + 15
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_vivid(f):
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.4, 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.1, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

    @staticmethod
    def _filter_cool(f):
        result = f.astype(np.float32)
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.2, 0, 255)
        result[:, :, 0] = np.clip(result[:, :, 0] * 0.9, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_warm(f):
        result = f.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.2, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.85, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_bw(f):
        gray = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

    @staticmethod
    def _filter_sepia(f):
        gray = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32)
        result = np.zeros_like(f, dtype=np.float32)
        result[:, :, 0] = np.clip(gray * 1.08, 0, 255)
        result[:, :, 1] = np.clip(gray * 0.84, 0, 255)
        result[:, :, 2] = np.clip(gray * 0.65, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_fade(f):
        result = f.astype(np.float32)
        result = result * 0.85 + 25
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_portrait(f):
        result = f.astype(np.float32)
        blur = cv2.GaussianBlur(f, (0, 0), 5).astype(np.float32)
        result = result * 0.7 + blur * 0.3
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.05, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_food(f):
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.3, 0, 255)
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.1, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_sky(f):
        result = f.astype(np.float32)
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.25, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * 1.05, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_natural(f):
        result = f.astype(np.float32)
        result = result * 1.05 - 5
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_dawn(f):
        result = f.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.3, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * 1.1, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.7, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_dusk(f):
        result = f.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.15, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.8, 0, 255)
        result = result * 0.9 + 10
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_neon(f):
        result = f.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.2, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.4, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * 0.8, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_cinema(f):
        result = f.astype(np.float32)
        dark_mask = result < 80
        result[dark_mask] = result[dark_mask] * 0.9
        result[:, :, 2][result[:, :, 2] < 80] += 5
        result[:, :, 1] = np.clip(result[:, :, 1] * 0.93, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_lomo(f):
        result = f.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.05, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.9, 0, 255)
        h, w = result.shape[:2]
        Y, X = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
        vign = 1 - np.clip(dist * 0.7, 0, 0.8)
        result = result * vign[..., np.newaxis]
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_polaroid(f):
        result = f.astype(np.float32)
        result = result * 0.9 + 20
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.05, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.95, 0, 255)
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_cross(f):
        result = f.astype(np.float32) / 255.0
        result[:, :, 0] = result[:, :, 0] ** 0.8
        result[:, :, 1] = result[:, :, 1] ** 1.2
        result[:, :, 2] = result[:, :, 2] ** 0.9
        return (np.clip(result, 0, 1) * 255).astype(np.uint8)

    # ---- NEW 18 filters ----

    @staticmethod
    def _filter_film(f):
        """Film grain + halation"""
        result = f.astype(np.float32)
        # Halation: red glow in highlights
        highs = np.clip(result[:, :, 0] - 180, 0, 75).astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] + highs * 0.3, 0, 255)
        # Slight desaturate
        gray = result.mean(axis=2, keepdims=True)
        result = result * 0.85 + gray * 0.15
        result = result * 0.95 + 8
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_matte(f):
        """Matte/flat look — lifted blacks"""
        result = f.astype(np.float32)
        result = result * 0.8 + 30
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.02, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.96, 0, 255)
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_urban(f):
        """High contrast, desaturated street look"""
        result = f.astype(np.float32)
        # Boost contrast
        result = (result - 128) * 1.3 + 128
        # Desaturate slightly
        gray = result.mean(axis=2, keepdims=True)
        result = result * 0.75 + gray * 0.25
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.9, 0, 255)
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_tropical(f):
        """Bright, saturated, cyan-teal"""
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.5, 0, 255)
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
        result[:, :, 1] = np.clip(result[:, :, 1] * 1.05, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.1, 0, 255)
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_dreamy(f):
        """Soft glow, pastel, overexposed"""
        result = f.astype(np.float32)
        blur = cv2.GaussianBlur(f, (0, 0), 8).astype(np.float32)
        result = result * 0.6 + blur * 0.4
        result = result * 1.1 + 15
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.05, 0, 255)
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_ink(f):
        """High contrast B&W with deep blacks"""
        gray = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32)
        gray = (gray - 128) * 1.8 + 128
        gray = np.clip(gray, 0, 255).astype(np.uint8)
        # Apply adaptive threshold feel (not binarize, just sharpen midtones)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

    @staticmethod
    def _filter_golden(f):
        """Golden hour sunlight"""
        result = f.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.25, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * 1.1, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.65, 0, 255)
        result = result * 1.05 + 5
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_moody(f):
        """Dark, desaturated, cinematic shadows"""
        result = f.astype(np.float32)
        gray = result.mean(axis=2, keepdims=True)
        result = result * 0.6 + gray * 0.4
        result = result * 0.85
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.1, 0, 255)
        # Vignette
        h, w = result.shape[:2]
        Y, X = np.ogrid[:h, :w]
        dist = np.sqrt(((X - w/2) / (w/2)) ** 2 + ((Y - h/2) / (h/2)) ** 2)
        vign = 1 - np.clip(dist * 0.6, 0, 0.7)
        result = result * vign[..., np.newaxis]
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_pastel(f):
        """Soft pastel palette"""
        result = f.astype(np.float32)
        # Desaturate
        gray = result.mean(axis=2, keepdims=True)
        result = result * 0.6 + gray * 0.4
        # Lift all channels
        result = result * 0.75 + 50
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.05, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.08, 0, 255)
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_vibrant(f):
        """Maximum saturation + sharpness"""
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.8, 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.1, 0, 255)
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        # Sharpen
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        result = cv2.filter2D(result, -1, kernel)
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_autumn(f):
        """Orange-brown fall tones"""
        result = f.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.2, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * 0.95, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.6, 0, 255)
        result = result * 0.95 + 10
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_ocean(f):
        """Deep blue-green water tones"""
        result = f.astype(np.float32)
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.35, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * 1.1, 0, 255)
        result[:, :, 0] = np.clip(result[:, :, 0] * 0.8, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_futuristic(f):
        """Cyan-magenta tech look"""
        result = f.astype(np.float32)
        # Edge detect and overlay
        gray = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150).astype(np.float32)
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.4 + edges * 0.2, 0, 255)
        result[:, :, 0] = np.clip(result[:, :, 0] * 0.85, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * 1.15, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _filter_retro80(f):
        """80s synthwave — magenta/cyan duotone"""
        result = f.astype(np.float32)
        gray = result.mean(axis=2)
        # Map to magenta (highlights) / cyan (shadows)
        lo = np.clip(1 - gray / 255, 0, 1)[..., np.newaxis]
        hi = np.clip(gray / 255, 0, 1)[..., np.newaxis]
        tinted = np.zeros_like(result)
        tinted[:, :, 0] = np.clip(result[:, :, 0] * 0.5 + 255 * hi[:, :, 0] * 0.5, 0, 255)  # R
        tinted[:, :, 1] = np.clip(result[:, :, 1] * 0.5 + 255 * lo[:, :, 0] * 0.3, 0, 255)  # G
        tinted[:, :, 2] = np.clip(result[:, :, 2] * 0.5 + 255 * (lo[:, :, 0] * 0.5 + hi[:, :, 0] * 0.3), 0, 255)  # B
        return tinted.astype(np.uint8)

    @staticmethod
    def _filter_coffee(f):
        """Warm brown coffee tones"""
        result = f.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.15 + 10, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * 0.9 + 5, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.7, 0, 255)
        result = result * 0.9 + 15
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_mint(f):
        """Cool mint-green fresh look"""
        result = f.astype(np.float32)
        result[:, :, 1] = np.clip(result[:, :, 1] * 1.12, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.08, 0, 255)
        result[:, :, 0] = np.clip(result[:, :, 0] * 0.92, 0, 255)
        result = result * 0.95 + 10
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_rose(f):
        """Rosy pink tones"""
        result = f.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.15, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.05, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * 0.9, 0, 255)
        result = result * 0.9 + 20
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _filter_noir(f):
        """High contrast black and white noir"""
        gray = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32)
        # Apply S-curve
        gray = gray / 255.0
        gray = gray ** 0.7 * 1.1
        gray = np.clip(gray * 255, 0, 255).astype(np.uint8)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
        gray = clahe.apply(gray)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

    # ---- Frame utilities ----

    @staticmethod
    def apply_chroma_key(frame: np.ndarray, key_color_hsv: tuple,
                         tolerance: float = 30.0) -> np.ndarray:
        """Green screen / chroma key — returns BGRA with alpha channel."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        hue, sat, val = key_color_hsv
        lower = np.array([max(0, hue - tolerance), 50, 50])
        upper = np.array([min(180, hue + tolerance), 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
        # Feather edges
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        alpha = 255 - mask
        rgba = cv2.cvtColor(frame, cv2.COLOR_RGB2RGBA)
        rgba[:, :, 3] = alpha
        return rgba

    @staticmethod
    def apply_mask(frame: np.ndarray, mask_type: str,
                   feather: float = 0.1, inverted: bool = False) -> np.ndarray:
        """Apply shape mask to frame (outside the shape becomes black)."""
        h, w = frame.shape[:2]
        m = FrameProcessor.mask_alpha(h, w, mask_type, feather, inverted)
        return (frame.astype(np.float32) * m[..., np.newaxis]).astype(np.uint8)

    @staticmethod
    def mask_alpha(h: int, w: int, mask_type: str, feather: float = 0.1,
                   inverted: bool = False) -> np.ndarray:
        """Shape mask as float32 HxW alpha in 0..1."""
        mask = np.zeros((h, w), dtype=np.uint8)

        if mask_type == 'circle':
            cx, cy = w // 2, h // 2
            r = min(cx, cy) - int(min(cx, cy) * feather)
            cv2.circle(mask, (cx, cy), r, 255, -1)
        elif mask_type in ('rect', 'rectangle'):
            margin = int(min(h, w) * feather)
            cv2.rectangle(mask, (margin, margin), (w - margin, h - margin), 255, -1)
        elif mask_type == 'star':
            pts = []
            import math
            for i in range(10):
                angle = math.pi / 5 * i - math.pi / 2
                r = (min(w, h) // 2 - 10) if i % 2 == 0 else (min(w, h) // 4)
                pts.append([int(w/2 + r * math.cos(angle)), int(h/2 + r * math.sin(angle))])
            pts_arr = np.array(pts, dtype=np.int32)
            cv2.fillPoly(mask, [pts_arr], 255)
        elif mask_type == 'heart':
            # Approximate heart with ellipses
            cv2.ellipse(mask, (w//2 - w//8, h//3), (w//4, h//4), 0, 0, 360, 255, -1)
            cv2.ellipse(mask, (w//2 + w//8, h//3), (w//4, h//4), 0, 0, 360, 255, -1)
            pts = np.array([[w//4, h//3], [w//2, h*3//4], [w*3//4, h//3]], dtype=np.int32)
            cv2.fillPoly(mask, [pts], 255)

        if feather > 0:
            ksize = int(min(h, w) * feather) * 2 + 1
            mask = cv2.GaussianBlur(mask, (ksize, ksize), 0)

        m = mask.astype(np.float32) / 255.0
        return 1.0 - m if inverted else m

    @staticmethod
    def apply_lut(frame: np.ndarray, lut_name: str) -> np.ndarray:
        """Apply color grading LUT."""
        luts = {
            'bleach_bypass': FrameProcessor._lut_bleach_bypass,
            'day_for_night': FrameProcessor._lut_day_for_night,
            'teal_orange': FrameProcessor._lut_teal_orange,
            'blockbuster': FrameProcessor._lut_blockbuster,
        }
        fn = luts.get(lut_name)
        if fn:
            return fn(frame)
        return frame

    @staticmethod
    def _lut_bleach_bypass(f):
        result = f.astype(np.float32)
        gray = result.mean(axis=2, keepdims=True)
        result = result * 0.5 + gray * 0.5
        result = (result - 128) * 1.5 + 128
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _lut_day_for_night(f):
        result = f.astype(np.float32) * 0.4
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.3, 0, 255)
        result[:, :, 0] = np.clip(result[:, :, 0] * 0.7, 0, 255)
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _lut_teal_orange(f):
        result = f.astype(np.float32)
        # Shadows → teal
        dark = np.clip(1 - result / 128, 0, 1)
        result[:, :, 2] += dark[:, :, 0] * 30
        result[:, :, 1] += dark[:, :, 0] * 10
        # Highlights → orange
        light = np.clip(result / 128 - 1, 0, 1)
        result[:, :, 0] += light[:, :, 0] * 25
        result[:, :, 1] += light[:, :, 0] * 10
        result[:, :, 2] -= light[:, :, 0] * 15
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _lut_blockbuster(f):
        result = f.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.1, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.85, 0, 255)
        gray = result.mean(axis=2, keepdims=True)
        result = result * 0.8 + gray * 0.2
        result = (result - 128) * 1.15 + 128
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def apply_flip(frame: np.ndarray, flip_h: bool, flip_v: bool) -> np.ndarray:
        if flip_h and flip_v:
            return cv2.flip(frame, -1)
        elif flip_h:
            return cv2.flip(frame, 1)
        elif flip_v:
            return cv2.flip(frame, 0)
        return frame

    @staticmethod
    def apply_crop(frame: np.ndarray, left: float, right: float,
                   top: float, bottom: float) -> np.ndarray:
        if left == 0 and right == 0 and top == 0 and bottom == 0:
            return frame
        h, w = frame.shape[:2]
        x1 = int(left * w)
        x2 = int(w - right * w)
        y1 = int(top * h)
        y2 = int(h - bottom * h)
        return frame[y1:y2, x1:x2]

    # ─── Motion & Cinematic Effects ───────────────────────────────────────────

    @staticmethod
    def apply_motion_blur(frame: np.ndarray, angle: float = 0.0,
                          strength: int = 15) -> np.ndarray:
        """Directional motion blur. angle in degrees, strength 1-50."""
        if frame is None or strength < 2:
            return frame
        strength = max(1, min(int(strength), 50))
        # Build horizontal kernel then rotate
        kernel = np.zeros((strength, strength), dtype=np.float32)
        kernel[strength // 2, :] = 1.0 / strength

        # Rotate kernel by angle using warpAffine
        cx, cy = strength / 2.0, strength / 2.0
        M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
        kernel = cv2.warpAffine(kernel, M, (strength, strength))
        total = kernel.sum()
        if total > 0:
            kernel /= total

        return cv2.filter2D(frame, -1, kernel)

    @staticmethod
    def apply_zoom_blur(frame: np.ndarray, strength: float = 0.5,
                        center_x: float = 0.5, center_y: float = 0.5) -> np.ndarray:
        """Radial zoom blur emanating from a center point."""
        if frame is None or strength <= 0:
            return frame
        h, w = frame.shape[:2]
        cx, cy = center_x * w, center_y * h
        iterations = 8
        scale_step = strength * 0.04
        result = frame.astype(np.float32)
        for i in range(1, iterations + 1):
            s = 1.0 + scale_step * i
            # Scale about center
            M = np.array([[s, 0, cx * (1 - s)],
                           [0, s, cy * (1 - s)]], dtype=np.float32)
            scaled = cv2.warpAffine(frame, M, (w, h),
                                    flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REPLICATE)
            weight = (iterations - i + 1) / ((iterations * (iterations + 1)) / 2)
            result += scaled.astype(np.float32) * weight
        # Normalize: sum of weights + 1 for original
        total_weight = 1.0 + sum((iterations - i + 1) / ((iterations * (iterations + 1)) / 2)
                                  for i in range(1, iterations + 1))
        result = (result / total_weight).clip(0, 255).astype(np.uint8)
        return result

    @staticmethod
    def apply_ken_burns(frame: np.ndarray, progress: float = 0.0,
                        start_scale: float = 1.0, end_scale: float = 1.3,
                        start_x: float = 0.5, start_y: float = 0.5,
                        end_x: float = 0.5, end_y: float = 0.5) -> np.ndarray:
        """Slow zoom + pan (Ken Burns). progress 0.0→1.0 over clip duration."""
        if frame is None:
            return frame
        h, w = frame.shape[:2]
        # EaseInOut cubic
        t = max(0.0, min(1.0, progress))
        ease = t * t * (3 - 2 * t)

        scale = start_scale + (end_scale - start_scale) * ease
        cx = (start_x + (end_x - start_x) * ease) * w
        cy = (start_y + (end_y - start_y) * ease) * h

        # Crop region
        crop_w = int(w / scale)
        crop_h = int(h / scale)
        x1 = int(cx - crop_w / 2)
        y1 = int(cy - crop_h / 2)
        x1 = max(0, min(x1, w - crop_w))
        y1 = max(0, min(y1, h - crop_h))
        x2, y2 = x1 + crop_w, y1 + crop_h

        cropped = frame[y1:y2, x1:x2]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def apply_tilt_shift(frame: np.ndarray, focus_y: float = 0.5,
                         blur_amount: int = 15, fade_range: float = 0.3) -> np.ndarray:
        """Miniature / tilt-shift: sharp band in middle, blurred top and bottom."""
        if frame is None:
            return frame
        h, w = frame.shape[:2]
        ksize = max(1, blur_amount | 1)  # must be odd
        blurred = cv2.GaussianBlur(frame, (ksize, ksize), 0)

        # Gradient mask: 1 at focus band, 0 far away
        ys = np.linspace(0, 1, h, dtype=np.float32)
        dist = np.abs(ys - focus_y)
        mask = 1.0 - np.clip(dist / max(fade_range, 0.01), 0.0, 1.0)
        mask = mask[:, np.newaxis, np.newaxis]

        # Slightly boost saturation for miniature look
        f32 = frame.astype(np.float32)
        gray = np.dot(f32[..., :3], [0.299, 0.587, 0.114])[..., np.newaxis]
        saturated = np.clip(f32 + 0.3 * (f32 - gray), 0, 255).astype(np.uint8)

        result = (saturated.astype(np.float32) * mask +
                  blurred.astype(np.float32) * (1.0 - mask))
        return result.clip(0, 255).astype(np.uint8)

    @staticmethod
    def apply_radial_blur(frame: np.ndarray, strength: float = 0.5) -> np.ndarray:
        """Spin/rotational blur: multiple rotated copies accumulated."""
        if frame is None or strength <= 0:
            return frame
        h, w = frame.shape[:2]
        cx, cy = w / 2.0, h / 2.0
        steps = 8
        max_angle = strength * 6.0  # degrees total spread
        result = frame.astype(np.float32)
        for i in range(1, steps + 1):
            angle = max_angle * i / steps
            for sign in (1, -1):
                M = cv2.getRotationMatrix2D((cx, cy), sign * angle, 1.0)
                rotated = cv2.warpAffine(frame, M, (w, h),
                                         flags=cv2.INTER_LINEAR,
                                         borderMode=cv2.BORDER_REPLICATE)
                result += rotated.astype(np.float32) * (0.3 / steps)
        result /= (1.0 + 0.3)
        return result.clip(0, 255).astype(np.uint8)

    @staticmethod
    def apply_glitch_rgb(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
        """Chromatic aberration + scanline displacement glitch."""
        if frame is None or intensity <= 0:
            return frame
        result = frame.copy()
        shift = max(1, int(intensity * 20))

        # Channel shift: R left, B right
        result[:, :, 0] = np.roll(frame[:, :, 0], -shift, axis=1)  # R
        result[:, :, 2] = np.roll(frame[:, :, 2], shift, axis=1)   # B

        # Random scanline displacement (~10% of rows)
        h, w = result.shape[:2]
        n_glitch = max(1, int(h * 0.1 * intensity))
        rows = np.random.choice(h, n_glitch, replace=False)
        for row in rows:
            disp = np.random.randint(-int(w * 0.05 * intensity),
                                      int(w * 0.05 * intensity) + 1)
            result[row] = np.roll(result[row], disp, axis=0)

        return result

    @staticmethod
    def apply_vhs_wobble(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
        """VHS tape wobble: horizontal scanline jitter + color bleed."""
        if frame is None or intensity <= 0:
            return frame
        h, w = frame.shape[:2]
        result = frame.copy().astype(np.float32)

        # Horizontal jitter per scanline
        for y in range(h):
            if np.random.random() < intensity * 0.3:
                jitter = int(np.random.normal(0, intensity * 4))
                result[y] = np.roll(result[y], jitter, axis=0)

        # Color bleed: smear chroma horizontally
        bleed_k = max(1, int(intensity * 8)) | 1
        b_ch = cv2.blur(frame[:, :, 2], (1, bleed_k))
        result[:, :, 2] = result[:, :, 2] * (1 - intensity * 0.4) + b_ch * intensity * 0.4

        # Slight noise
        noise = np.random.normal(0, intensity * 8, result.shape).astype(np.float32)
        result = np.clip(result + noise, 0, 255)

        return result.astype(np.uint8)

    @staticmethod
    def apply_chromatic_aberration(frame: np.ndarray, amount: float = 0.5) -> np.ndarray:
        """Lens-style chromatic aberration: scale R and B channels slightly."""
        if frame is None or amount <= 0:
            return frame
        h, w = frame.shape[:2]
        scale_r = 1.0 + amount * 0.02
        scale_b = 1.0 - amount * 0.02

        def scale_channel(ch, s):
            M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s)
            return cv2.warpAffine(ch, M, (w, h),
                                   flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REPLICATE)

        result = frame.copy()
        result[:, :, 0] = scale_channel(frame[:, :, 0], scale_r)
        result[:, :, 2] = scale_channel(frame[:, :, 2], scale_b)
        return result


    # ── Motion Blur methods ────────────────────────────────────────────

    @staticmethod
    def motion_blur_horizontal(frame: np.ndarray, strength: int = 15) -> np.ndarray:
        from src.core.kenburns import MotionBlurEngine
        return MotionBlurEngine.horizontal(frame, strength)

    @staticmethod
    def motion_blur_vertical(frame: np.ndarray, strength: int = 15) -> np.ndarray:
        from src.core.kenburns import MotionBlurEngine
        return MotionBlurEngine.vertical(frame, strength)

    @staticmethod
    def motion_blur_zoom(frame: np.ndarray, strength: float = 0.05) -> np.ndarray:
        from src.core.kenburns import MotionBlurEngine
        return MotionBlurEngine.zoom(frame, strength)

    @staticmethod
    def ken_burns(frame: np.ndarray, t: float = 0.0,
                  zoom_in: bool = True, intensity: float = 0.15) -> np.ndarray:
        """Ken Burns effect at normalized time t (0..1)."""
        from src.core.kenburns import KenBurnsEngine
        margin = intensity
        if zoom_in:
            start = (0.0, 0.0, 1.0, 1.0)
            end   = (margin / 2, margin / 2, 1.0 - margin, 1.0 - margin)
        else:
            start = (margin / 2, margin / 2, 1.0 - margin, 1.0 - margin)
            end   = (0.0, 0.0, 1.0, 1.0)
        return KenBurnsEngine.apply(frame, t, start, end)

    @staticmethod
    def three_d_zoom(frame: np.ndarray, t: float = 0.0, strength: float = 0.1) -> np.ndarray:
        from src.core.kenburns import ThreeDZoomEngine
        zoom = 1.0 + strength * t
        rot_y = strength * 8 * t
        return ThreeDZoomEngine.apply(frame, zoom_factor=zoom, rotation_y=rot_y)


def frame_to_pixmap(frame: np.ndarray, target_w: int, target_h: int) -> QPixmap:
    """Convert numpy RGB frame to QPixmap, fitted to target size."""
    if frame is None:
        return QPixmap(target_w, target_h)

    h, w = frame.shape[:2]
    aspect = w / h
    target_aspect = target_w / target_h

    if aspect > target_aspect:
        new_w = target_w
        new_h = int(target_w / aspect)
    else:
        new_h = target_h
        new_w = int(target_h * aspect)

    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    h, w, c = resized.shape
    bytes_per_line = c * w
    qimg = QImage(resized.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)
