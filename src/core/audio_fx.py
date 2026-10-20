"""
Audio FX Engine — Pitch shift, reverb, robot, echo, distortion
numpy-based DSP with optional scipy acceleration
"""
from __future__ import annotations
import numpy as np
from typing import Optional

SCIPY_AVAILABLE = False
try:
    from scipy import signal as sp_signal
    from scipy.io import wavfile
    SCIPY_AVAILABLE = True
except ImportError:
    pass


def semitones_to_note_label(semitones: int) -> str:
    """Return human-readable label for a semitone offset."""
    if semitones == 0:
        return "Normal (0)"
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    direction = "+" if semitones > 0 else ""
    return f"{direction}{semitones} st"


# Preset chains for voice changer quick-access
VOICE_PRESETS = {
    "chipmunk": [{"type": "pitch", "params": {"semitones": 8.0}}],
    "helium":   [{"type": "pitch", "params": {"semitones": 12.0}}],
    "deep":     [{"type": "pitch", "params": {"semitones": -6.0}},
                 {"type": "reverb", "params": {"room_size": 0.3, "wet": 0.2}}],
    "monster":  [{"type": "pitch", "params": {"semitones": -10.0}},
                 {"type": "robot", "params": {}},
                 {"type": "reverb", "params": {"room_size": 0.6, "wet": 0.3}}],
    "alien":    [{"type": "pitch", "params": {"semitones": 5.0}},
                 {"type": "robot", "params": {}}],
    "echo_voice": [{"type": "echo", "params": {"delay_ms": 400.0, "decay": 0.4, "repeats": 4}}],
}


class AudioFXEngine:
    """Alias kept for backward compat — wraps AudioFX methods."""
    pass


class AudioFX:
    """Audio effects processor — operates on float32 mono/stereo numpy arrays."""

    @staticmethod
    def pitch_shift(samples: np.ndarray, sr: int,
                    semitones: float = 0.0) -> np.ndarray:
        """
        Pitch-shift by resampling + time-stretch (phase-vocoder-lite).
        semitones: positive = higher pitch, negative = lower.
        """
        if abs(semitones) < 0.01:
            return samples
        factor = 2.0 ** (semitones / 12.0)
        # Resample to change pitch (naive but fast)
        n_out = int(len(samples) / factor)
        x = np.linspace(0, len(samples) - 1, n_out)
        idx = x.astype(np.int64)
        frac = x - idx
        idx = np.clip(idx, 0, len(samples) - 2)
        return (samples[idx] * (1 - frac) + samples[idx + 1] * frac).astype(samples.dtype)

    @staticmethod
    def robot_voice(samples: np.ndarray, sr: int,
                    freq_hz: float = 100.0) -> np.ndarray:
        """Vocoder-style robot effect: multiply by carrier sine wave."""
        t = np.arange(len(samples)) / sr
        carrier = np.sin(2 * np.pi * freq_hz * t).astype(np.float32)
        out = samples.astype(np.float32) * carrier
        # Low-pass to smooth
        out = AudioFX._lowpass(out, sr, cutoff=3000.0)
        return _normalize(out).astype(samples.dtype)

    @staticmethod
    def echo(samples: np.ndarray, sr: int,
             delay_ms: float = 300.0, decay: float = 0.5,
             n_echoes: int = 4) -> np.ndarray:
        """Discrete echo: delay_ms between each repeat, decaying amplitude."""
        delay_samples = int(sr * delay_ms / 1000.0)
        out = samples.astype(np.float32).copy()
        total_len = len(samples) + delay_samples * n_echoes
        padded = np.zeros(total_len, dtype=np.float32)
        padded[:len(samples)] = samples.astype(np.float32)
        for i in range(1, n_echoes + 1):
            amp = decay ** i
            start = delay_samples * i
            padded[start:start + len(samples)] += samples.astype(np.float32) * amp
        return padded[:len(samples)]

    @staticmethod
    def reverb(samples: np.ndarray, sr: int,
               room_size: float = 0.5, damping: float = 0.5,
               wet: float = 0.4) -> np.ndarray:
        """Schroeder reverb: parallel comb + allpass filters."""
        f = samples.astype(np.float32)
        # Comb filter delays (Schroeder sizes scaled by room_size)
        comb_delays = [int(sr * d * (0.5 + room_size)) for d in
                       [0.0297, 0.0371, 0.0411, 0.0437]]
        comb_out = np.zeros_like(f)
        for d in comb_delays:
            comb_out += _comb_filter(f, d, damping * 0.8)
        comb_out /= len(comb_delays)
        # Allpass
        ap = _allpass_filter(comb_out, int(sr * 0.005), 0.7)
        ap = _allpass_filter(ap, int(sr * 0.0017), 0.7)
        return (f * (1.0 - wet) + ap * wet).astype(samples.dtype)

    @staticmethod
    def distortion(samples: np.ndarray, drive: float = 0.5) -> np.ndarray:
        """Soft-clip distortion via tanh waveshaper."""
        f = samples.astype(np.float32)
        gain = 1.0 + drive * 40.0
        return np.tanh(f * gain).astype(samples.dtype)

    @staticmethod
    def chorus(samples: np.ndarray, sr: int,
               rate_hz: float = 1.5, depth_ms: float = 3.0,
               wet: float = 0.5) -> np.ndarray:
        """Chorus: modulated delay line."""
        f = samples.astype(np.float32)
        n = len(f)
        depth_s = depth_ms / 1000.0
        max_delay = int(sr * depth_s * 2) + 1
        t = np.arange(n) / sr
        mod = depth_s * (0.5 + 0.5 * np.sin(2 * np.pi * rate_hz * t))
        mod_samples = (mod * sr).astype(np.int32)
        out = np.zeros(n, np.float32)
        for i in range(n):
            j = max(0, i - mod_samples[i])
            out[i] = f[j]
        return (f * (1 - wet) + out * wet).astype(samples.dtype)

    @staticmethod
    def _lowpass(samples: np.ndarray, sr: int, cutoff: float = 4000.0) -> np.ndarray:
        if SCIPY_AVAILABLE:
            b, a = sp_signal.butter(2, cutoff / (sr / 2), btype='low')
            return sp_signal.lfilter(b, a, samples).astype(samples.dtype)
        # Simple IIR 1-pole fallback
        rc = 1.0 / (2 * np.pi * cutoff)
        dt = 1.0 / sr
        alpha = dt / (rc + dt)
        out = np.zeros_like(samples, dtype=np.float32)
        out[0] = samples[0]
        for i in range(1, len(samples)):
            out[i] = out[i - 1] + alpha * (float(samples[i]) - out[i - 1])
        return out.astype(samples.dtype)

    @staticmethod
    def apply_chain(samples: np.ndarray, sr: int,
                    effects: list) -> np.ndarray:
        """
        Apply a list of (effect_name, params_dict) in order.
        effects: [("pitch", {"semitones": 2}), ("reverb", {"wet": 0.3}), ...]
        """
        s = samples.copy()
        for name, params in effects:
            if name == "pitch":
                s = AudioFX.pitch_shift(s, sr, **params)
            elif name == "robot":
                s = AudioFX.robot_voice(s, sr, **params)
            elif name == "echo":
                s = AudioFX.echo(s, sr, **params)
            elif name == "reverb":
                s = AudioFX.reverb(s, sr, **params)
            elif name == "distortion":
                s = AudioFX.distortion(s, **params)
            elif name == "chorus":
                s = AudioFX.chorus(s, sr, **params)
        return s


# ── DSP helpers ───────────────────────────────────────────────────────────────

def _comb_filter(x: np.ndarray, delay: int, feedback: float) -> np.ndarray:
    out = np.zeros_like(x)
    for i in range(len(x)):
        j = i - delay
        out[i] = x[i] + (out[j] * feedback if j >= 0 else 0.0)
    return out


def _allpass_filter(x: np.ndarray, delay: int, gain: float) -> np.ndarray:
    out = np.zeros_like(x)
    for i in range(len(x)):
        j = i - delay
        delayed = out[j] if j >= 0 else 0.0
        out[i] = -gain * x[i] + delayed + gain * (out[j] if j >= 0 else 0.0)
        # Simpler stable allpass:
        out[i] = x[i] * (1 - gain ** 2) + (x[j] if j >= 0 else 0.0) * gain
    return out


def _normalize(x: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(x))
    if peak > 1e-9:
        return x / peak
    return x
